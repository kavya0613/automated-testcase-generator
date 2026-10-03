from tcgen.schemas import QACase, StoryAnalysis


def test_case_coercion():
    c = QACase.model_validate({"scenario": "x", "steps": "open > click > verify", "priority": "high",
                               "polarity": "negative case", "test_data": {"a": 1}, "requirement_ids": "R1, R2"})
    assert c.steps == ["open", "click", "verify"]
    assert c.priority == "High" and c.polarity == "Negative"
    assert c.requirement_ids == ["R1", "R2"] and c.test_data == '{"a": 1}'


def test_analysis_accepts_string_requirements():
    a = StoryAnalysis.model_validate({"requirements": ["email required", {"id": "R9", "text": "pw required"}]})
    assert [r.id for r in a.requirements] == ["R1", "R9"]
