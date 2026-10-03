"""Module 7: rule + similarity based validation of generated test cases."""
from __future__ import annotations

from dataclasses import dataclass, field

from .metrics import Scorer
from .schemas import QACase, StoryAnalysis


@dataclass
class Issue:
    kind: str            # missing_field | too_few_cases | no_positive | no_negative | duplicate | uncovered_requirement
    message: str
    case_id: str | None = None

    def to_dict(self) -> dict:
        return {"kind": self.kind, "message": self.message, "case_id": self.case_id}


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)
    duplicates: list[tuple[str, str, float]] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues

    def kinds(self) -> set[str]:
        return {i.kind for i in self.issues}

    def to_text(self) -> str:
        return "\n".join(f"- [{i.kind}] {i.message}" for i in self.issues) or "No issues."

    def to_dict(self) -> dict:
        return {"passed": self.passed, "issues": [i.to_dict() for i in self.issues]}


def validate(cases: list[QACase], analysis: StoryAnalysis, scorer: Scorer, min_cases: int = 6) -> ValidationReport:
    rep = ValidationReport()
    for c in cases:
        if not c.scenario:
            rep.issues.append(Issue("missing_field", "Missing scenario", c.id))
        if len(c.steps) < 1:
            rep.issues.append(Issue("missing_field", "Missing test steps", c.id))
        if not c.expected_result:
            rep.issues.append(Issue("missing_field", "Missing expected result", c.id))
    if len(cases) < min_cases:
        rep.issues.append(Issue("too_few_cases", f"Only {len(cases)} test cases; at least {min_cases} expected"))
    if not any(c.polarity == "Positive" for c in cases):
        rep.issues.append(Issue("no_positive", "No positive test case"))
    if not any(c.polarity == "Negative" for c in cases):
        rep.issues.append(Issue("no_negative", "No negative test case"))
    rep.duplicates = scorer.duplicates(cases)
    for a, b, s in rep.duplicates:
        rep.issues.append(Issue("duplicate", f"{b} duplicates {a} (similarity {s:.2f})", b))
    rep.uncovered = scorer.coverage(cases, analysis)["uncovered"]
    by_id = {r.id: r.text for r in analysis.requirements}
    for rid in rep.uncovered:
        rep.issues.append(Issue("uncovered_requirement", f"{rid} not covered: {by_id.get(rid, '')}"))
    return rep
