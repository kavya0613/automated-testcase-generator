"""FastAPI service:  uvicorn api:app --reload   (docs at /docs)"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tcgen import db
from tcgen.service import get_components, get_settings_cached, run_generation

app = FastAPI(title="AI Test Case Generator", version="1.0.0")


class StoryIn(BaseModel):
    user_story: str


@app.get("/health")
def health():
    comp = get_components()
    return {"status": "ok", "llm": comp.llm_status, "classifier": comp.ml.mode}


@app.post("/generate")
def generate(body: StoryIn):
    try:
        return run_generation(body.user_story)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/stories")
def stories(limit: int = 50):
    return db.list_stories(get_settings_cached().db_path, limit)


@app.get("/stories/{story_id}/test-cases")
def story_cases(story_id: int):
    return db.get_cases(get_settings_cached().db_path, story_id)
