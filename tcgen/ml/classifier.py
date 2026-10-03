"""TensorFlow NLP components.

Two small text classifiers (Keras TextVectorization -> Embedding -> pooled Dense net):
  * category : Authentication / Payment / Registration / Search / ...
  * quality  : Complete / Incomplete / Ambiguous user story

If TensorFlow is not installed (or training fails) a keyword heuristic is used so the
rest of the pipeline keeps working; ClassificationResult.source tells which one ran.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from ..preprocess import parse_story_template, vague_terms
from ..schemas import ClassificationResult
from .dataset import CATEGORIES, generate_dataset


def tf_available() -> bool:
    return importlib.util.find_spec("tensorflow") is not None


class TFTextClassifier:
    def __init__(self, task: str, models_dir: Path, max_tokens: int = 6000,
                 seq_len: int = 48, embed_dim: int = 64):
        self.task, self.models_dir = task, Path(models_dir)
        self.max_tokens, self.seq_len, self.embed_dim = max_tokens, seq_len, embed_dim
        self.model = None
        self.labels: list[str] = []

    @property
    def model_path(self) -> Path:
        return self.models_dir / f"{self.task}.keras"

    @property
    def labels_path(self) -> Path:
        return self.models_dir / f"{self.task}_labels.json"

    def exists(self) -> bool:
        return self.model_path.exists() and self.labels_path.exists()

    # ------------------------------------------------------------------ build / train
    def _build(self, train_texts, num_classes):
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers

        vec = layers.TextVectorization(
            max_tokens=self.max_tokens, output_sequence_length=self.seq_len,
            standardize="lower_and_strip_punctuation")
        vec.adapt(tf.constant(train_texts))
        inputs = keras.Input(shape=(), dtype="string")
        x = vec(inputs)
        x = layers.Embedding(vec.vocabulary_size(), self.embed_dim, mask_zero=True)(x)
        x = layers.GlobalAveragePooling1D()(x)
        x = layers.Dense(64, activation="relu")(x)
        x = layers.Dropout(0.3)(x)
        outputs = layers.Dense(num_classes, activation="softmax")(x)
        model = keras.Model(inputs, outputs, name=f"{self.task}_classifier")
        model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        return model

    def train(self, texts: list[str], labels: list[str], epochs: int = 30, seed: int = 42) -> dict:
        import numpy as np
        import tensorflow as tf
        from sklearn.model_selection import train_test_split

        tf.keras.utils.set_random_seed(seed)
        self.labels = sorted(set(labels))
        y = np.array([self.labels.index(l) for l in labels])
        x_tr, x_te, y_tr, y_te = train_test_split(
            texts, y, test_size=0.2, random_state=seed, stratify=y)
        self.model = self._build(x_tr, len(self.labels))
        early = tf.keras.callbacks.EarlyStopping(patience=4, restore_best_weights=True)
        self.model.fit(tf.constant(x_tr), y_tr, epochs=epochs, batch_size=32,
                       validation_split=0.1, callbacks=[early], verbose=0)
        _, acc = self.model.evaluate(tf.constant(x_te), y_te, verbose=0)
        return {"task": self.task, "accuracy": float(acc), "n_train": len(x_tr), "n_test": len(x_te)}

    # ------------------------------------------------------------------ save / load / predict
    def save(self) -> None:
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.model.save(self.model_path)
        self.labels_path.write_text(json.dumps(self.labels), encoding="utf-8")

    def load(self) -> None:
        from tensorflow import keras
        self.model = keras.models.load_model(self.model_path)
        self.labels = json.loads(self.labels_path.read_text(encoding="utf-8"))

    def predict(self, text: str) -> dict[str, float]:
        import tensorflow as tf
        probs = self.model(tf.constant([text]), training=False).numpy()[0]
        return {label: float(p) for label, p in zip(self.labels, probs)}


# ---------------------------------------------------------------------- heuristic fallback
_KEYWORDS = {
    "Authentication": ["login", "log in", "sign in", "logout", "password", "otp", "authenticate", "credential"],
    "Payment": ["pay", "payment", "card", "refund", "checkout", "upi", "invoice", "billing"],
    "Registration": ["register", "registration", "sign up", "signup", "create an account", "create account", "verify my email"],
    "Search": ["search", "filter", "sort", "keyword", "suggestion", "results"],
    "Shopping Cart": ["cart", "coupon", "quantity", "basket", "discount"],
    "Profile": ["profile", "avatar", "picture", "account settings", "personal details"],
    "Notification": ["notification", "alert", "remind", "push", "unread", "notify"],
    "Data Management": ["record", "csv", "import", "export", "create a new", "edit", "delete", "report", "data"],
}


def heuristic_classify(story: str) -> ClassificationResult:
    low = story.lower()
    scores = {c: sum(1 for k in kws if k in low) for c, kws in _KEYWORDS.items()}
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    category = best if scores[best] > 0 else "General"
    conf = (scores[best] / total) if total else 0.0
    parsed = parse_story_template(story)
    vague = vague_terms(story)
    words = len(re.findall(r"\w+", story))
    if vague and not (parsed["structured"] and parsed["benefit"] and words > 14):
        quality, score = "Ambiguous", 45.0
    elif parsed["structured"] and parsed["benefit"] and words >= 10:
        quality, score = "Complete", 90.0
    else:
        quality, score = "Incomplete", 30.0
    return ClassificationResult(category=category, category_confidence=round(conf, 3),
                                quality=quality, quality_confidence=0.6,
                                quality_score=score, source="heuristic")


# ---------------------------------------------------------------------- facade used by the agent
class StoryMLAnalyzer:
    def __init__(self, models_dir: Path, auto_train: bool = True):
        self.models_dir = Path(models_dir)
        self.category = TFTextClassifier("category", self.models_dir)
        self.quality = TFTextClassifier("quality", self.models_dir)
        self.mode, self.error = "heuristic", None
        if not tf_available():
            self.error = "TensorFlow is not installed - using keyword heuristic."
            return
        try:
            if not (self.category.exists() and self.quality.exists()) and auto_train:
                self.train()
            if self.category.exists() and self.quality.exists():
                self.category.load()
                self.quality.load()
                self.mode = "tensorflow"
        except Exception as exc:  # never break the app because of the ML layer
            self.error = f"TensorFlow models unavailable ({exc}) - using keyword heuristic."
            self.mode = "heuristic"

    def train(self, epochs: int = 30) -> list[dict]:
        rows = generate_dataset()
        texts = [r["text"] for r in rows]
        metrics = []
        for clf, key in ((self.category, "category"), (self.quality, "quality")):
            metrics.append(clf.train(texts, [r[key] for r in rows], epochs=epochs))
            clf.save()
        return metrics

    def classify(self, story: str) -> ClassificationResult:
        if self.mode != "tensorflow":
            return heuristic_classify(story)
        cat = self.category.predict(story)
        qual = self.quality.predict(story)
        category = max(cat, key=cat.get)
        quality = max(qual, key=qual.get)
        return ClassificationResult(
            category=category, category_confidence=round(cat[category], 4),
            quality=quality, quality_confidence=round(qual[quality], 4),
            quality_score=round(qual.get("Complete", 0.0) * 100, 1), source="tensorflow")


KNOWN_CATEGORIES = list(CATEGORIES) + ["General"]
