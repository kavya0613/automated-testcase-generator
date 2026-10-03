"""Pydantic models shared by the agent, validators, exporters, API and UI."""
from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Requirement(BaseModel):
    id: str
    text: str


class StoryAnalysis(BaseModel):
    actor: str = ""
    goal: str = ""
    benefit: str = ""
    requirements: list[Requirement] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

    @field_validator("requirements", mode="before")
    @classmethod
    def _coerce_requirements(cls, v: Any):
        out = []
        for i, item in enumerate(v or [], start=1):
            if isinstance(item, str):
                out.append({"id": f"R{i}", "text": item})
            elif isinstance(item, dict):
                out.append({"id": str(item.get("id") or f"R{i}"),
                            "text": str(item.get("text") or item.get("requirement") or "")})
            else:
                out.append(item)
        return [o for o in out if not isinstance(o, dict) or o["text"]]

    @field_validator("business_rules", "constraints", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return [str(x) for x in v]


class QACase(BaseModel):
    """One structured test case."""

    id: str = ""
    scenario: str = ""
    preconditions: str = ""
    steps: list[str] = Field(default_factory=list)
    test_data: str = ""
    expected_result: str = ""
    priority: Literal["High", "Medium", "Low"] = "Medium"
    test_type: str = "Functional"
    polarity: Literal["Positive", "Negative"] = "Positive"
    requirement_ids: list[str] = Field(default_factory=list)

    @field_validator("steps", mode="before")
    @classmethod
    def _coerce_steps(cls, v: Any):
        if v is None:
            return []
        if isinstance(v, str):
            parts = re.split(r"\s*(?:→|->|>|\n|;)\s*", v)
            return [p.strip() for p in parts if p.strip()]
        return [re.sub(r"^\s*\d+[.)]\s*", "", str(s)).strip() for s in v if str(s).strip()]

    @field_validator("test_data", "preconditions", "scenario", "expected_result", mode="before")
    @classmethod
    def _coerce_text(cls, v: Any):
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return str(v).strip()

    @field_validator("priority", mode="before")
    @classmethod
    def _coerce_priority(cls, v: Any):
        v = str(v or "Medium").strip().capitalize()
        return v if v in {"High", "Medium", "Low"} else "Medium"

    @field_validator("polarity", mode="before")
    @classmethod
    def _coerce_polarity(cls, v: Any):
        return "Negative" if str(v or "").strip().lower().startswith("neg") else "Positive"

    @field_validator("requirement_ids", mode="before")
    @classmethod
    def _coerce_req_ids(cls, v: Any):
        if v is None:
            return []
        if isinstance(v, str):
            return [x.strip() for x in re.split(r"[,\s]+", v) if x.strip()]
        return [str(x) for x in v]


class ClassificationResult(BaseModel):
    category: str
    category_confidence: float          # 0..1
    quality: Literal["Complete", "Incomplete", "Ambiguous"]
    quality_confidence: float           # 0..1
    quality_score: float                # P(Complete) in percent
    source: str = "heuristic"           # "tensorflow" | "heuristic"
