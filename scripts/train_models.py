"""Train and save the TensorFlow category + quality classifiers into ./models"""
import _path  # noqa: F401
import argparse

from tcgen.config import get_settings
from tcgen.ml.classifier import StoryMLAnalyzer, tf_available

p = argparse.ArgumentParser()
p.add_argument("--epochs", type=int, default=30)
args = p.parse_args()

if not tf_available():
    raise SystemExit("TensorFlow is not installed: pip install tensorflow")
analyzer = StoryMLAnalyzer(get_settings().models_dir, auto_train=False)
for m in analyzer.train(epochs=args.epochs):
    print(f"{m['task']:<9} held-out accuracy = {m['accuracy']:.3f}  (train={m['n_train']}, test={m['n_test']})")
print("Models saved to", get_settings().models_dir)
