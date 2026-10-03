import _path  # noqa: F401
from tcgen.service import get_components, get_settings_cached
from tcgen.metrics import Scorer
from tcgen.offline import offline_analyze, offline_generate

scorer = Scorer(get_components().embedder, get_settings_cached().thresholds)
story = ("As a registered user, I want to log into the application using my "
            "registered email and password so that I can access my account.")
analysis = offline_analyze(story, "Authentication")
sets = [("Matching cases (login)", offline_generate(analysis, "Authentication")),
           ("Unrelated cases (payment)", offline_generate(offline_analyze("x", "Payment"), "Payment"))]
for name, cases in sets:
    for i, c in enumerate(cases, 1):
           c.id = f"TC{i:03d}"
    cov = scorer.coverage(cases, analysis)["percent"]
    rel = scorer.relevance(cases, story, analysis)["percent"]
    print(f"{name:<28} coverage={cov}%  relevance={rel}%")   