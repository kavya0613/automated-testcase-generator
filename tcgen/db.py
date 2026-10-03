"""SQLite persistence (UserStory + TestCase tables)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS UserStory (
    story_id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_text TEXT NOT NULL,
    category TEXT, quality_score REAL, coverage REAL, relevance REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS TestCase (
    test_case_id TEXT, story_id INTEGER, scenario TEXT, precondition TEXT, test_steps TEXT,
    test_data TEXT, expected_result TEXT, priority TEXT, test_type TEXT, polarity TEXT, status TEXT DEFAULT 'Draft',
    FOREIGN KEY (story_id) REFERENCES UserStory(story_id)
);
"""


def _conn(path: Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def save_run(path: Path, result: dict) -> int:
    con = _conn(path)
    with con:
        cur = con.execute(
            "INSERT INTO UserStory (story_text, category, quality_score, coverage, relevance) VALUES (?,?,?,?,?)",
            (result["story"], result["classification"]["category"], result["classification"]["quality_score"],
             result["metrics"]["coverage_percent"], result["metrics"]["relevance_percent"]))
        sid = cur.lastrowid
        con.executemany(
            "INSERT INTO TestCase (test_case_id, story_id, scenario, precondition, test_steps, test_data,"
            " expected_result, priority, test_type, polarity) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(c["id"], sid, c["scenario"], c["preconditions"], json.dumps(c["steps"]), c["test_data"],
              c["expected_result"], c["priority"], c["test_type"], c["polarity"]) for c in result["test_cases"]])
    con.close()
    return sid


def list_stories(path: Path, limit: int = 50) -> list[dict]:
    con = _conn(path)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT story_id, story_text, category, quality_score, coverage, relevance, created_at "
        "FROM UserStory ORDER BY story_id DESC LIMIT ?", (limit,))]
    con.close()
    return rows


def get_cases(path: Path, story_id: int) -> list[dict]:
    con = _conn(path)
    con.row_factory = sqlite3.Row
    rows = []
    for r in con.execute("SELECT * FROM TestCase WHERE story_id=?", (story_id,)):
        d = dict(r)
        d["test_steps"] = json.loads(d["test_steps"] or "[]")
        rows.append(d)
    con.close()
    return rows
