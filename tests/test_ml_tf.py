import pytest

pytest.importorskip("tensorflow")

from tcgen.ml.classifier import StoryMLAnalyzer  # noqa: E402


def test_tensorflow_classifiers_learn(tmp_path):
    a = StoryMLAnalyzer(tmp_path, auto_train=False)
    metrics = a.train(epochs=15)
    assert all(m["accuracy"] > 0.85 for m in metrics)
    a2 = StoryMLAnalyzer(tmp_path)  # loads saved models
    assert a2.mode == "tensorflow"
    r = a2.classify("As a customer, I want to pay for my order using a credit card so that I can finish checkout.")
    assert r.category == "Payment" and r.quality == "Complete"
    assert a2.classify("User should login.").quality != "Complete"
