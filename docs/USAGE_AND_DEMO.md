# Usage Guide and Demo Script

## Using the UI
1. `streamlit run app.py`
2. **Generate** tab: pick a sample or type your own story → *Generate test cases*.
3. Read the **Story analysis** (TensorFlow category/quality), **Test case summary** (counts, coverage, relevance, duplicates),
   the test case table, the requirement-coverage expander and the **Agent trace**.
4. Download **Excel / CSV / JSON**.
5. **Batch** tab: upload `.txt` (one story per line or paragraph) or `.json` (`[{"user_story": "..."}]`) and run many at once.
6. **History** tab: previously generated stories and cases from SQLite.

Input JSON format: `{"user_story": "As a user, I want ... so that ..."}` or a list of such objects.

## API
`POST /generate` with `{"user_story": "..."}` → full result (classification, analysis, test cases, metrics, trace).
`GET /stories`, `GET /stories/{id}/test-cases`, `GET /health`.

## Demo video script (3-5 minutes)
1. **Problem** (20 s): manual test writing is slow and inconsistent.
2. **Architecture slide** (40 s): TensorFlow → single LangChain agent → GenAI → validation → scoring → export.
3. **Live demo 1: Login story** (60 s): show category + quality, test cases, coverage/relevance, trace.
4. **Live demo 2: Vague story** `The system should handle login properly and be fast, etc.` (40 s): show *Ambiguous* quality and the assumptions.
5. **Live demo 3: Payment or Cart** (40 s): show negative/boundary/security cases.
6. **Batch tab** (40 s): run the 10 samples, show average coverage/relevance vs the 80% target.
7. **Agentic behaviour** (30 s): open the trace, point out a validate → refine → validate loop.
8. **Exports and docs** (20 s): download Excel, show the prompt-engineering doc.

## Questions you may be asked
* *Why TensorFlow?* Cheap, fast, deterministic story classification/quality gate, so the LLM gets better context and the system does not depend on the LLM for everything.
* *Why LangChain?* Prompt templates, provider-independent LLM calls, tools and embeddings in one framework.
* *Why an agent?* The number of steps depends on the validation result: it decides whether to refine or finish.
* *How do you measure quality?* Requirement coverage, relevance and duplicate rate from similarity scores, plus rule-based validation.
* *Limitations?* See "Honest notes about the metrics" in the README.
