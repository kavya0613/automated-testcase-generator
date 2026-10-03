# AI Test Case Generator from User Stories

A **single-agent** system that turns a natural-language user story into structured, validated and scored
test cases (steps, test data, expected results, preconditions, priority, type, positive/negative).

| Technology | Real role in this project |
|---|---|
| **TensorFlow** | Two Keras text classifiers trained on synthetic stories: *domain category* (Authentication, Payment, ...) and *story quality* (Complete / Incomplete / Ambiguous). They steer the agent and its prompts. |
| **LangChain** | Prompt templates (LCEL `prompt \| llm \| parser`), the LLM provider abstraction, `StructuredTool`s that the agent calls, embeddings wrappers. |
| **Generative AI** | The LLM analyses the story into requirements, writes the test cases and rewrites them when validation fails. |
| **Agentic AI** | One `CaseGenerationAgent` runs a plan → act → observe loop over its tools, with state-based guardrails and a refine-until-valid loop. |

## Architecture

```
User story ─► preprocess ─► TensorFlow (category + quality) ─► ┌──────────── Agent ────────────┐
                                                               │ classify → analyze → generate │
                                                               │      → validate ─┐            │
                                                               │        ▲  refine ◄┘ (issues)  │
                                                               │      → calculate_metrics      │
                                                               └───────────────┬───────────────┘
                              LLM (LangChain)  ◄── analyze / generate / refine ┘
                                                               ▼
              coverage % · relevance % · duplicate % (embeddings)  ─►  JSON / CSV / Excel / SQLite
```

Details:
* **Validation** (`tcgen/validation.py`): missing steps/expected results, too few cases, no positive/negative case,
  duplicates, uncovered requirements.
* **Coverage** = covered requirements / extracted requirements. **Relevance** = % of test cases that clearly relate to the
  story or one of its requirements. **Duplicates** = pairs above a cosine threshold. All are computed with vector/term
  similarity, not by asking the LLM for a score.
* **Planner**: when only one next step is legal the agent just takes it; when there is a real choice (refine vs. accept)
  the LLM decides, otherwise a rule does.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # Python 3.10-3.12 recommended for TensorFlow
cp .env.example .env                                   # then edit it (optional, see below)
streamlit run app.py
```

On the first launch the TensorFlow classifiers are trained automatically (a few seconds) and saved in `models/`.
Train manually with `python scripts/train_models.py` (prints held-out accuracy).

### Choose the generative model
Edit `.env`:

| Goal | Settings |
|---|---|
| Free/cheap cloud | `LLM_PROVIDER=google`, `GOOGLE_API_KEY=...`, `pip install langchain-google-genai` |
| OpenAI | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=...`, `pip install langchain-openai` |
| Claude | `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=...`, `pip install langchain-anthropic` |
| Local, no key | install Ollama, `ollama pull llama3.1`, `LLM_PROVIDER=ollama`, `pip install langchain-ollama` |
| Nothing | `LLM_PROVIDER=none` → **offline template mode** (the app still runs end to end) |

Optional: `EMBEDDING_BACKEND=hf` (+ `pip install langchain-huggingface sentence-transformers`) switches coverage,
relevance and duplicate scoring to dense sentence embeddings, which is the recommended setting for the real demo.

## Other entry points

```bash
python main.py --story "As a user, I want to ... so that ..."     # CLI → output/*.json|csv|xlsx
python main.py --file data/sample_stories.json
uvicorn api:app --reload                                          # REST API, docs at /docs
python scripts/evaluate.py                                        # coverage/relevance on 10 sample stories
pytest                                                            # unit + end-to-end tests
```

## Project layout

```
app.py                Streamlit UI (Generate / Batch / History tabs, Excel/CSV/JSON download)
api.py  main.py       FastAPI service and CLI
tcgen/agent.py        the single agent: tools, planner, refine loop
tcgen/prompts.py      LangChain prompt templates
tcgen/ml/             TensorFlow classifiers + synthetic dataset
tcgen/metrics.py      embeddings, coverage, relevance, duplicates
tcgen/validation.py   validator
tcgen/offline*.py     template fallback (no-LLM mode)
tcgen/export.py db.py JSON/CSV/Excel export, SQLite storage
data/                 sample stories (10 diverse), synthetic training data is generated on demand
docs/                 PROMPT_ENGINEERING.md, USAGE_AND_DEMO.md
tests/                pytest suite
```

## Honest notes about the metrics

* **Offline template mode**: coverage/relevance are high *by construction* because the templates know which requirement each
  case verifies. Use it for development and as a fallback; use an LLM (plus dense embeddings) to demonstrate real results.
* Thresholds live in `tcgen/config.py` (`THRESHOLDS`). Tune them on your own stories instead of just lowering them to hit 80%.
* The TensorFlow models are trained on **synthetic** template-generated stories, so they are strong on that style and
  weaker on very different phrasing. Add real stories to `tcgen/ml/dataset.py` (or your own CSV) to improve them.
* `scripts/train_models.py` reports accuracy on a held-out split of the same synthetic distribution; treat it as a smoke test.

## Data and safety
No sensitive data is used. Training data is synthetic; test data in generated cases is fictional (e.g. `user@example.com`).
