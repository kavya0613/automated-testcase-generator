"""The single Test Case Generation Agent.

One agent, a set of LangChain tools, and a plan -> act -> observe loop:

    classify_story -> analyze_story -> generate_test_cases -> validate_test_cases
        -> (refine_test_cases -> validate_test_cases)* -> calculate_metrics -> finish

The set of *legal* next actions is derived from the agent state (guardrails). When more than one
action is legal (e.g. refine vs. accept) the LLM planner chooses; with no LLM a rule picks.
Generative AI does language work (analysis, generation, refinement); TensorFlow does story
classification/quality; embeddings do objective scoring.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import StructuredTool

from .config import Settings, get_settings
from .llm import get_llm
from .metrics import Embedder, Scorer
from .ml.classifier import StoryMLAnalyzer
from .offline import cases_for_requirement, offline_analyze, offline_generate, repair_cases
from .preprocess import clean_text, validate_story
from .prompts import (ANALYSIS_PROMPT, CATEGORY_HINTS, GENERATION_PROMPT, PLANNER_PROMPT, REFINE_PROMPT)
from .schemas import ClassificationResult, QACase, StoryAnalysis
from .utils import extract_json
from .validation import ValidationReport, validate

MAX_STEPS = 14


@dataclass
class Components:
    """Heavy, shareable objects (build once, reuse for every run)."""
    llm: Any
    llm_status: str
    ml: StoryMLAnalyzer
    embedder: Embedder

    @classmethod
    def build(cls, settings: Settings) -> "Components":
        llm, status = get_llm(settings)
        return cls(llm, status, StoryMLAnalyzer(settings.models_dir), Embedder(settings))


@dataclass
class AgentState:
    story: str
    classification: ClassificationResult | None = None
    analysis: StoryAnalysis | None = None
    test_cases: list[QACase] = field(default_factory=list)
    report: ValidationReport | None = None
    metrics: dict | None = None
    refinements: int = 0
    trace: list[dict] = field(default_factory=list)


class CaseGenerationAgent:
    __test__ = False  # not a pytest class

    def __init__(self, settings: Settings | None = None, components: Components | None = None):
        self.settings = settings or get_settings()
        self.c = components or Components.build(self.settings)
        self.scorer = Scorer(self.c.embedder, self.settings.thresholds)
        self.state: AgentState | None = None
        self.tools = {t.name: t for t in self._build_tools()}

    # ------------------------------------------------------------------ public API
    def run(self, story: str) -> dict:
        story = validate_story(clean_text(story))
        self.state = AgentState(story=story)
        for step in range(1, MAX_STEPS + 1):
            allowed = self._allowed()
            action, thought = self._decide(allowed)
            t0 = time.time()
            if action == "finish":
                self._log(step, action, thought, "Result assembled.", t0)
                break
            observation = self.tools[action].invoke({})
            self._log(step, action, thought, observation, t0)
        return self._result()

    # ------------------------------------------------------------------ planning
    def _allowed(self) -> list[str]:
        s = self.state
        if s.classification is None:
            return ["classify_story"]
        if s.analysis is None:
            return ["analyze_story"]
        if not s.test_cases:
            return ["generate_test_cases"]
        if s.report is None:
            return ["validate_test_cases"]
        if s.metrics is None:
            if s.report.issues and s.refinements < self.settings.max_refinements:
                return ["refine_test_cases", "calculate_metrics"]
            return ["calculate_metrics"]
        return ["finish"]

    def _decide(self, allowed: list[str]) -> tuple[str, str]:
        if len(allowed) == 1:
            return allowed[0], "Only one valid next step."
        if self.c.llm is not None and self.settings.use_llm_planner:
            try:
                chain = PLANNER_PROMPT | self.c.llm | StrOutputParser()
                data = extract_json(chain.invoke({"state": self._state_summary(), "allowed": ", ".join(allowed)}))
                if data.get("action") in allowed:
                    return data["action"], str(data.get("thought", "")) or "LLM planner decision."
            except Exception:
                pass
        return allowed[0], "Rule-based planner: fix validator issues before accepting."

    def _state_summary(self) -> str:
        s = self.state
        return json.dumps({
            "category": s.classification.category, "story_quality": s.classification.quality,
            "num_test_cases": len(s.test_cases), "refinements_used": s.refinements,
            "max_refinements": self.settings.max_refinements,
            "validator_issues": [i.to_dict() for i in s.report.issues][:12]}, indent=2)

    def _log(self, step, action, thought, observation, t0):
        self.state.trace.append({"step": step, "action": action, "thought": thought,
                                 "observation": observation, "seconds": round(time.time() - t0, 2)})

    # ------------------------------------------------------------------ tools
    def _build_tools(self) -> list[StructuredTool]:
        specs = [
            (self._t_classify, "classify_story", "Classify the story domain and quality with the TensorFlow models."),
            (self._t_analyze, "analyze_story", "Extract actor, goal and atomic testable requirements."),
            (self._t_generate, "generate_test_cases", "Generate structured test cases with the LLM."),
            (self._t_validate, "validate_test_cases", "Check completeness, duplicates and requirement coverage."),
            (self._t_refine, "refine_test_cases", "Fix validator issues: dedupe, fill gaps, add missing cases."),
            (self._t_metrics, "calculate_metrics", "Compute coverage, relevance and duplicate scores."),
        ]
        return [StructuredTool.from_function(func=f, name=n, description=d) for f, n, d in specs]

    def _llm_json(self, prompt, **variables):
        return extract_json((prompt | self.c.llm | StrOutputParser()).invoke(variables))

    def _t_classify(self) -> str:
        s = self.state
        s.classification = self.c.ml.classify(s.story)
        c = s.classification
        return (f"category={c.category} ({c.category_confidence:.0%}); quality={c.quality} "
                f"(P(complete)={c.quality_score:.0f}%) via {c.source}")

    def _t_analyze(self) -> str:
        s, cat = self.state, self.state.classification
        note = ""
        if self.c.llm is not None:
            try:
                data = self._llm_json(ANALYSIS_PROMPT, category=cat.category, quality=cat.quality, story=s.story)
                s.analysis = StoryAnalysis.model_validate(data)
                if not s.analysis.requirements:
                    raise ValueError("no requirements returned")
            except Exception as exc:
                note, s.analysis = f" (LLM analysis failed: {exc}; used offline analysis)", None
        if s.analysis is None:
            s.analysis = offline_analyze(s.story, cat.category)
        return f"actor='{s.analysis.actor}'; {len(s.analysis.requirements)} requirements extracted{note}"

    def _t_generate(self) -> str:
        s, cat = self.state, self.state.classification
        cases, note = [], ""
        if self.c.llm is not None:
            try:
                data = self._llm_json(
                    GENERATION_PROMPT, category=cat.category, quality=cat.quality, story=s.story,
                    analysis=s.analysis.model_dump_json(indent=1), min_cases=8, max_cases=16,
                    hints=CATEGORY_HINTS.get(cat.category, CATEGORY_HINTS["General"]))
                cases = self._parse_cases(data)
                if len(cases) < 3:
                    raise ValueError("fewer than 3 usable test cases")
            except Exception as exc:
                note, cases = f" (LLM generation failed: {exc}; used offline templates)", []
        if not cases:
            cases = offline_generate(s.analysis, cat.category)
        s.test_cases = self._renumber(cases)
        return f"{len(s.test_cases)} test cases generated{note}"

    def _t_validate(self) -> str:
        s = self.state
        s.report = validate(s.test_cases, s.analysis, self.scorer, self.settings.min_cases)
        return f"{len(s.report.issues)} issue(s): {sorted(s.report.kinds()) or 'none'}"

    def _t_refine(self) -> str:
        s, rep, cat = self.state, self.state.report, self.state.classification.category
        notes = []
        drop = {b for _, b, _ in rep.duplicates}
        if drop:
            s.test_cases = [c for c in s.test_cases if c.id not in drop]
            notes.append(f"removed {len(drop)} duplicate(s)")
        fixable = [i for i in rep.issues if i.kind != "duplicate"]
        if fixable:
            refined = None
            if self.c.llm is not None:
                try:
                    data = self._llm_json(
                        REFINE_PROMPT, story=s.story, requirements=json.dumps([r.model_dump() for r in s.analysis.requirements]),
                        test_cases=json.dumps([c.model_dump() for c in s.test_cases]), issues=rep.to_text())
                    refined = self._parse_cases(data)
                    if len(refined) < max(3, len(s.test_cases) // 2):
                        raise ValueError("refinement returned too few cases")
                    notes.append("LLM rewrote test cases to fix issues")
                except Exception as exc:
                    refined = None
                    notes.append(f"LLM refinement failed ({exc})")
            if refined is not None:
                s.test_cases = refined
            else:
                s.test_cases = repair_cases(
                    s.test_cases, s.analysis, cat, rep.uncovered,
                    need_positive="no_positive" in rep.kinds(), need_negative="no_negative" in rep.kinds(),
                    min_cases=self.settings.min_cases if "too_few_cases" in rep.kinds() else 0)
                notes.append("applied template repairs")
        s.test_cases = self._renumber(s.test_cases)
        s.refinements += 1
        s.report = None  # forces re-validation
        return "; ".join(notes) or "nothing to change"

    def _t_metrics(self) -> str:
        s = self.state
        s.metrics = self.scorer.summary(s.test_cases, s.story, s.analysis, s.refinements, self.settings.target_percent)
        m = s.metrics
        return (f"coverage={m['coverage_percent']}%, relevance={m['relevance_percent']}%, "
                f"duplicates={m['duplicate_percent']}%, meets_80%_target={m['meets_target']}")

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _parse_cases(data) -> list[QACase]:
        if isinstance(data, dict):
            data = data.get("test_cases") or data.get("testCases") or next(
                (v for v in data.values() if isinstance(v, list)), [])
        cases = []
        for item in data:
            try:
                cases.append(QACase.model_validate(item))
            except Exception:
                continue
        return cases

    @staticmethod
    def _renumber(cases: list[QACase]) -> list[QACase]:
        for i, c in enumerate(cases, start=1):
            c.id = f"TC{i:03d}"
        return cases

    def _result(self) -> dict:
        s = self.state
        return {
            "story": s.story,
            "classification": s.classification.model_dump(),
            "analysis": s.analysis.model_dump(),
            "test_cases": [c.model_dump() for c in s.test_cases],
            "metrics": s.metrics,
            "validation": s.report.to_dict() if s.report else {"passed": True, "issues": []},
            "trace": s.trace,
            "llm_status": self.c.llm_status,
            "ml_mode": self.c.ml.mode,
            "ml_note": self.c.ml.error,
        }
