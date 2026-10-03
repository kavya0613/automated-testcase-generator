import json
from pathlib import Path

import pytest

from tcgen.agent import CaseGenerationAgent, Components
from tcgen.config import Settings
from tcgen.metrics import Embedder
from tcgen.ml.classifier import StoryMLAnalyzer

SAMPLES = json.loads((Path(__file__).parent.parent / "data" / "sample_stories.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def agent_factory(tmp_path_factory):
    settings = Settings(llm_provider="none", models_dir=tmp_path_factory.mktemp("models"))
    comps = Components(llm=None, llm_status="offline", ml=StoryMLAnalyzer(settings.models_dir, auto_train=False),
                       embedder=Embedder(settings))
    return lambda: CaseGenerationAgent(settings, comps)


@pytest.mark.parametrize("sample", SAMPLES[:9], ids=lambda s: s["title"])
def test_meets_80_percent_targets(agent_factory, sample):
    r = agent_factory().run(sample["user_story"])
    assert r["metrics"]["total"] >= 6
    assert r["metrics"]["coverage_percent"] >= 80
    assert r["metrics"]["relevance_percent"] >= 80
    assert r["metrics"]["positive"] >= 1 and r["metrics"]["negative"] >= 1
    assert all(c["steps"] and c["expected_result"] for c in r["test_cases"])


def test_agent_trace_order(agent_factory):
    r = agent_factory().run(SAMPLES[0]["user_story"])
    actions = [t["action"] for t in r["trace"]]
    assert actions[:4] == ["classify_story", "analyze_story", "generate_test_cases", "validate_test_cases"]
    assert actions[-1] == "finish"


def test_too_short_story_rejected(agent_factory):
    with pytest.raises(ValueError):
        agent_factory().run("hi")


def test_refine_loop_fixes_uncovered(agent_factory):
    agent = agent_factory()
    agent.state = None
    r = agent.run(SAMPLES[1]["user_story"])
    assert r["metrics"]["uncovered"] == []
