"""Embeddings + objective scoring: requirement coverage, relevance and duplicate detection.

These scores are computed with vector similarity, NOT by asking the LLM for a number.
"""
from __future__ import annotations

import re

import numpy as np

from .config import Settings


# ------------------------------------------------------------------ text normalisation
def _stem(word: str) -> str:
    for suf in ("ations", "ation", "ings", "ing", "ions", "ion", "ed", "es", "s"):
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[: -len(suf)]
    return word


# tiny concept map so "empty / blank / missing / mandatory" and "wrong / incorrect / invalid" match
_SYNONYMS = {"mandatory": "required", "empty": "required", "blank": "required", "missing": "required",
             "incorrect": "invalid", "wrong": "invalid", "unsupported": "invalid", "oversized": "invalid",
             "expired": "invalid", "unregistered": "invalid", "rejected": "invalid"}


def _tokenize(text: str) -> list[str]:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_SYNONYMS.get(s, s) for s in (_stem(w) for w in words if w not in ENGLISH_STOP_WORDS)]


class Embedder:
    """similarity(a, b) -> |a| x |b| cosine matrix. Backends: tfidf (default), hf, openai."""

    def __init__(self, settings: Settings):
        self.backend = settings.embedding_backend
        self._dense = None
        if self.backend == "hf":
            from langchain_huggingface import HuggingFaceEmbeddings
            self._dense = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        elif self.backend == "openai":
            from langchain_openai import OpenAIEmbeddings
            self._dense = OpenAIEmbeddings(model="text-embedding-3-small")
        elif self.backend != "tfidf":
            raise ValueError(f"Unknown EMBEDDING_BACKEND '{self.backend}'")

    def relatedness(self, refs: list[str], docs: list[str]) -> np.ndarray:
        """|refs| x |docs| matrix: how well each doc addresses each reference text.

        Dense backends: cosine similarity of embeddings.
        TF-IDF backend: containment = share of the reference's (stemmed) terms found in the doc.
        Containment is used because short requirements vs. long test cases give tiny cosine values.
        """
        if self._dense is not None:
            return self.similarity(refs, docs)
        if not refs or not docs:
            return np.zeros((len(refs), len(docs)))
        doc_sets = [set(_tokenize(d)) for d in docs]
        out = np.zeros((len(refs), len(docs)))
        for i, r in enumerate(refs):
            rt = set(_tokenize(r))
            if rt:
                out[i] = [len(rt & ds) / len(rt) for ds in doc_sets]
        return out

    def similarity(self, a: list[str], b: list[str]) -> np.ndarray:
        """Symmetric cosine similarity (used for duplicate detection)."""
        if not a or not b:
            return np.zeros((len(a), len(b)))
        if self._dense is not None:
            ea = np.array(self._dense.embed_documents(a), dtype=float)
            eb = np.array(self._dense.embed_documents(b), dtype=float)
            ea /= np.linalg.norm(ea, axis=1, keepdims=True) + 1e-12
            eb /= np.linalg.norm(eb, axis=1, keepdims=True) + 1e-12
            return ea @ eb.T
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        corpus = list(dict.fromkeys(a + b))
        try:
            vec = TfidfVectorizer(tokenizer=_tokenize, token_pattern=None, lowercase=False,
                                  ngram_range=(1, 2), sublinear_tf=True).fit(corpus)
            return cosine_similarity(vec.transform(a), vec.transform(b))
        except ValueError:  # empty vocabulary
            return np.zeros((len(a), len(b)))


def case_text(tc) -> str:
    # preconditions are excluded: they are often boilerplate and dilute the similarity signal
    return " . ".join([tc.scenario, " ".join(tc.steps), tc.test_data, tc.expected_result])


class Scorer:
    def __init__(self, embedder: Embedder, thresholds: dict):
        self.embedder, self.t = embedder, thresholds

    def duplicates(self, cases) -> list[tuple[str, str, float]]:
        if len(cases) < 2:
            return []
        texts = [case_text(c) for c in cases]
        sim = self.embedder.similarity(texts, texts)
        out = []
        for i in range(len(cases)):
            for j in range(i + 1, len(cases)):
                if sim[i, j] >= self.t["duplicate"]:
                    out.append((cases[i].id, cases[j].id, float(sim[i, j])))
        return out

    def coverage(self, cases, analysis) -> dict:
        reqs = analysis.requirements
        if not reqs:
            return {"percent": 0.0, "covered": [], "uncovered": [], "per_requirement": {}}
        sim = self.embedder.relatedness([r.text for r in reqs], [case_text(c) for c in cases]) \
            if cases else np.zeros((len(reqs), 0))
        per, covered = {}, []
        for i, r in enumerate(reqs):
            best_sim, best_case, tagged_ok = 0.0, None, False
            for j, c in enumerate(cases):
                s = float(sim[i, j])
                if s > best_sim:
                    best_sim, best_case = s, c.id
                if r.id in c.requirement_ids and s >= self.t["coverage"] / 2:
                    tagged_ok = True
            ok = best_sim >= self.t["coverage"] or tagged_ok
            per[r.id] = {"covered": ok, "best_case": best_case, "similarity": round(best_sim, 3)}
            if ok:
                covered.append(r.id)
        uncovered = [r.id for r in reqs if r.id not in covered]
        return {"percent": round(100 * len(covered) / len(reqs), 1), "covered": covered,
                "uncovered": uncovered, "per_requirement": per}

    def relevance(self, cases, story: str, analysis) -> dict:
        if not cases:
            return {"percent": 0.0, "avg_similarity_percent": 0.0, "per_case": {}}
        refs = [story] + [r.text for r in analysis.requirements]
        sim = self.embedder.relatedness(refs, [case_text(c) for c in cases])  # refs x cases
        best = sim.max(axis=0)
        relevant = best >= self.t["relevance"]
        return {"percent": round(float(relevant.mean() * 100), 1),
                "avg_similarity_percent": round(float(best.mean() * 100), 1),
                "per_case": {c.id: round(float(b), 3) for c, b in zip(cases, best)}}

    def summary(self, cases, story, analysis, refinements: int, target: float) -> dict:
        cov = self.coverage(cases, analysis)
        rel = self.relevance(cases, story, analysis)
        dups = self.duplicates(cases)
        by_type: dict[str, int] = {}
        for c in cases:
            by_type[c.test_type] = by_type.get(c.test_type, 0) + 1
        return {
            "total": len(cases),
            "positive": sum(c.polarity == "Positive" for c in cases),
            "negative": sum(c.polarity == "Negative" for c in cases),
            "by_type": by_type,
            "requirements": len(analysis.requirements),
            "coverage_percent": cov["percent"],
            "uncovered": cov["uncovered"],
            "coverage_detail": cov["per_requirement"],
            "relevance_percent": rel["percent"],
            "avg_similarity_percent": rel["avg_similarity_percent"],
            "duplicate_percent": round(100 * len({b for _, b, _ in dups}) / max(len(cases), 1), 1),
            "refinements": refinements,
            "meets_target": cov["percent"] >= target and rel["percent"] >= target,
        }
