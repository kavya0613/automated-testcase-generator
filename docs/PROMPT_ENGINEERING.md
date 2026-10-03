# Prompt Engineering Documentation

All prompts live in `tcgen/prompts.py` as LangChain `ChatPromptTemplate`s and run as LCEL chains:
`prompt | llm | StrOutputParser()` followed by a tolerant JSON extractor (`tcgen/utils.py`) and Pydantic validation
(`tcgen/schemas.py`).

## 1. Principles used

| Technique | Where | Why |
|---|---|---|
| Role prompting ("senior QA analyst", "expert QA engineer", "QA lead") | all system prompts | steers vocabulary and level of rigor |
| Strict output schema in the prompt | analysis, generation, refine | machine-readable JSON, no prose |
| Pydantic validation + coercion after generation | `QACase`, `StoryAnalysis` | tolerates small deviations (steps as a string, lowercase priority) |
| Coverage rules inside the prompt | generation | every requirement id must be referenced; positive/negative/boundary/security cases required |
| Context injection from TensorFlow | all human prompts | the classifier's category and quality are passed in; category-specific hints (`CATEGORY_HINTS`) are added to generation |
| Assumptions for weak stories | generation | if quality is Incomplete/Ambiguous the model must state assumptions in `preconditions` |
| Feedback-driven refinement | refine | the validator's issues are pasted into the prompt, the model returns the full corrected list |
| Low temperature (0.2) | `LLM_TEMPERATURE` | consistent structure and fewer invented details |
| Constrained planner | planner prompt | the model can only pick from the actions the code marks as legal |

## 2. The prompt chain

1. **Analysis prompt**: story + category + quality → actor, goal, benefit, 4-8 atomic requirements (`R1..Rn`), business rules, constraints.
2. **Generation prompt**: story + analysis JSON + category hints → 8-16 test cases with the fields
   `scenario, preconditions, steps[], test_data, expected_result, priority, test_type, polarity, requirement_ids[]`.
3. **Refine prompt** (only when validation fails): story + requirements + current cases + issue list → corrected full list.
4. **Planner prompt** (only when there is a real choice): state summary + allowed actions → `{"thought", "action"}`.

## 3. Failure handling
* Markdown fences or extra prose around the JSON are stripped (`extract_json`).
* Test cases that fail Pydantic validation are dropped; fewer than 3 usable cases triggers the offline fallback.
* Duplicates are removed deterministically by code, not by the LLM.
* Every fallback is recorded in the agent trace shown in the UI.

## 4. Tips for tuning
* Add 1-2 few-shot examples of your own organisation's test case style to `GENERATION_SYSTEM`.
* Add domain rules (e.g. "passwords: 8-64 chars") to the story or to `CATEGORY_HINTS`.
* If outputs are too long, lower `max_cases`; if coverage is low, raise `min_cases` and `MAX_REFINEMENTS`.
* Keep the JSON schema block unchanged unless you also update `QACase`.

## 5. Example
Input: *"As a registered user, I want to log into the application using my registered email and password so that I can access my account."*

Expected cases include: valid login, invalid password, unregistered email, empty email, empty password, invalid email format,
account lockout after repeated failures, SQL-injection attempt, password masking.
