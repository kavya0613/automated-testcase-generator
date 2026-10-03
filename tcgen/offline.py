"""Offline (no-LLM) analysis / generation / repair, built on offline_packs.

This keeps the whole pipeline demo-able without any API key. With an LLM configured
these functions are only used as a safety net when the model output is unusable.
"""
from __future__ import annotations

from .offline_packs import PACKS
from .preprocess import clean_text, parse_story_template
from .schemas import QACase, Requirement, StoryAnalysis


def _pack(category: str) -> list:
    return PACKS.get(category, PACKS["General"])


def offline_analyze(story: str, category: str) -> StoryAnalysis:
    parsed = parse_story_template(story)
    goal = parsed["goal"] or clean_text(story)[:160]
    reqs = [Requirement(id="R1", text=goal)]
    for i, (req_text, _) in enumerate(_pack(category), start=2):
        reqs.append(Requirement(id=f"R{i}", text=req_text))
    return StoryAnalysis(
        actor=parsed["actor"] or "user", goal=goal, benefit=parsed["benefit"], requirements=reqs,
        business_rules=["Behaviour follows the acceptance criteria stated in the user story."],
        constraints=["Input must be validated before processing."])


def _to_case(t: tuple, req_ids: list[str]) -> QACase:
    scenario, steps, data, expected, prio, ttype, pol = t
    return QACase(scenario=scenario, preconditions="Application is available and the tester has network access.",
                  steps=steps, test_data=data, expected_result=expected, priority=prio,
                  test_type=ttype, polarity=pol, requirement_ids=req_ids)


def goal_case(analysis: StoryAnalysis) -> QACase:
    goal = analysis.goal or "complete the main user action"
    return QACase(
        scenario=f"Happy path: {goal}", preconditions="User has the required access and valid data.",
        steps=["Open the application", f"Perform the action: {goal}", "Submit or confirm the action"],
        test_data="Valid test data", expected_result=f"The action completes successfully: {goal}",
        priority="High", test_type="Functional", polarity="Positive",
        requirement_ids=[analysis.requirements[0].id] if analysis.requirements else [])


def cases_for_requirement(req: Requirement, category: str) -> list[QACase]:
    """Cases for one requirement: use the pack entry when the text matches, else a generic pair."""
    for req_text, cases in _pack(category):
        if req_text.lower() == req.text.lower():
            return [_to_case(c, [req.id]) for c in cases]
    return [
        QACase(scenario=f"Verify: {req.text}", preconditions="Application is available.",
               steps=["Open the application", f"Exercise the behaviour: {req.text}", "Observe the result"],
               test_data="Valid test data", expected_result=f"The requirement is satisfied: {req.text}",
               priority="High", test_type="Functional", polarity="Positive", requirement_ids=[req.id]),
        QACase(scenario=f"Verify invalid input against: {req.text}", preconditions="Application is available.",
               steps=["Open the application", f"Violate the rule: {req.text}", "Observe the result"],
               test_data="Invalid test data", expected_result=f"A clear error is shown; the rule is enforced: {req.text}",
               priority="Medium", test_type="Validation", polarity="Negative", requirement_ids=[req.id]),
    ]


def offline_generate(analysis: StoryAnalysis, category: str) -> list[QACase]:
    cases = [goal_case(analysis)]
    pack_texts = {t.lower(): cs for t, cs in _pack(category)}
    used = set()
    for req in analysis.requirements:
        if req.text.lower() in pack_texts:
            cases.extend(cases_for_requirement(req, category))
            used.add(req.text.lower())
    if len(cases) < 4:  # requirements came from elsewhere (e.g. an LLM) -> fall back to the whole pack
        for req_text, cs in _pack(category):
            if req_text.lower() not in used:
                cases.extend(_to_case(c, []) for c in cs)
    return cases


def repair_cases(cases: list[QACase], analysis: StoryAnalysis, category: str,
                 uncovered: list[str], need_positive: bool, need_negative: bool,
                 min_cases: int = 0) -> list[QACase]:
    for c in cases:  # fill missing fields
        if not c.steps:
            c.steps = ["Open the application", f"Perform: {c.scenario or 'the scenario'}", "Observe the result"]
        if not c.expected_result:
            c.expected_result = "The system behaves as described by the requirement."
        if not c.scenario:
            c.scenario = c.steps[0]
    by_id = {r.id: r for r in analysis.requirements}
    for rid in uncovered:
        if rid in by_id:
            cases.extend(cases_for_requirement(by_id[rid], category))
    if need_positive and not any(c.polarity == "Positive" for c in cases):
        cases.append(goal_case(analysis))
    if need_negative and not any(c.polarity == "Negative" for c in cases):
        cases.extend(c for c in cases_for_requirement(
            Requirement(id="R0", text="Invalid input is rejected with a clear error message"), "General")
            if c.polarity == "Negative")
    if len(cases) < min_cases:  # top up from the category pack, then from the general pack
        have = {c.scenario.lower() for c in cases}
        for pack in (_pack(category), PACKS["General"]):
            for _, cs in pack:
                for c in cs:
                    if len(cases) >= min_cases:
                        return cases
                    if c[0].lower() not in have:
                        cases.append(_to_case(c, []))
                        have.add(c[0].lower())
    return cases
