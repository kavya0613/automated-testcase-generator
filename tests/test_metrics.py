from tcgen.config import Settings
from tcgen.metrics import Embedder, Scorer
from tcgen.schemas import QACase, Requirement, StoryAnalysis


def _scorer():
    s = Settings()
    return Scorer(Embedder(s), s.thresholds)


def test_duplicate_detection():
    a = QACase(id="TC001", scenario="Login with valid email and password", steps=["Enter valid email", "Enter valid password", "Click Login"], expected_result="Dashboard shown")
    b = QACase(id="TC002", scenario="Login with valid email and password", steps=["Enter valid email", "Enter valid password", "Click Login"], expected_result="Dashboard is shown")
    c = QACase(id="TC003", scenario="Export report to PDF", steps=["Open reports", "Click export"], expected_result="PDF downloaded")
    dups = _scorer().duplicates([a, b, c])
    assert [(x, y) for x, y, _ in dups] == [("TC001", "TC002")]


def test_coverage_flags_uncovered_requirement():
    case = QACase(id="TC001", scenario="Login with empty email", steps=["Leave email empty", "Click Login"], expected_result="Email required message", requirement_ids=["R1"])
    analysis = StoryAnalysis(requirements=[Requirement(id="R1", text="Email is mandatory"),
                                           Requirement(id="R2", text="Generate quarterly invoice archive")])
    cov = _scorer().coverage([case], analysis)
    assert "R1" in cov["covered"] and "R2" in cov["uncovered"] and cov["percent"] == 50.0
