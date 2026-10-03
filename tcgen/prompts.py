"""LangChain prompt templates (see docs/PROMPT_ENGINEERING.md for the design rationale)."""
from langchain_core.prompts import ChatPromptTemplate

ANALYSIS_SYSTEM = """You are a senior QA analyst. Read the user story and extract what a tester needs.
Return ONLY valid JSON (no prose, no markdown fences) with exactly this shape:
{{
  "actor": "who performs the action",
  "goal": "what the actor wants to do",
  "benefit": "why (may be empty)",
  "requirements": [{{"id": "R1", "text": "one atomic, testable requirement"}}],
  "business_rules": ["rules stated or strongly implied"],
  "constraints": ["limits, formats, security or performance constraints"]
}}
Rules:
- Produce 4 to 8 atomic, testable requirements, numbered R1, R2, ...
- Include requirements for input validation, error handling and security when relevant.
- If the story is incomplete or ambiguous, add reasonable requirements and keep them generic.
- Do not invent product-specific details that contradict the story."""

ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", ANALYSIS_SYSTEM),
    ("human", "Domain category (from ML classifier): {category}\n"
              "Story quality (from ML classifier): {quality}\n\nUser story:\n{story}"),
])

GENERATION_SYSTEM = """You are an expert QA engineer who writes detailed, actionable manual test cases.
Using the user story and the analysed requirements, produce between {min_cases} and {max_cases} test cases.
Return ONLY a JSON array (no prose, no markdown fences). Each element must have exactly these keys:
{{
  "scenario": "short title",
  "preconditions": "state required before the test",
  "steps": ["step 1", "step 2", "..."],
  "test_data": "concrete example values",
  "expected_result": "observable, verifiable outcome",
  "priority": "High | Medium | Low",
  "test_type": "Functional | Validation | Boundary | Security | Error Handling | Usability",
  "polarity": "Positive | Negative",
  "requirement_ids": ["R1"]
}}
Coverage rules:
- Every requirement id must be referenced by at least one test case.
- Include positive, negative, boundary, validation, security and error-handling cases where they make sense.
- Steps must be imperative, ordered and specific (2 to 7 steps). Expected results must be measurable.
- Never duplicate a scenario; each case must test something different.
- Domain hints for this category: {hints}
- If the story quality is Incomplete or Ambiguous, state your assumptions in "preconditions"."""

GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", GENERATION_SYSTEM),
    ("human", "Category: {category}\nStory quality: {quality}\n\nUser story:\n{story}\n\n"
              "Analysis (JSON):\n{analysis}"),
])

REFINE_SYSTEM = """You are a QA lead reviewing generated test cases. Fix every listed issue and return the
COMPLETE corrected list as ONLY a JSON array using the same keys as the input (scenario, preconditions,
steps, test_data, expected_result, priority, test_type, polarity, requirement_ids).
- Add test cases for uncovered requirements (and tag them with the requirement id).
- Fill in missing steps / expected results. Remove or rewrite duplicates.
- Keep good test cases unchanged."""

REFINE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", REFINE_SYSTEM),
    ("human", "User story:\n{story}\n\nRequirements (JSON):\n{requirements}\n\n"
              "Current test cases (JSON):\n{test_cases}\n\nIssues found by the validator:\n{issues}"),
])

PLANNER_SYSTEM = """You are the planner of a single test-case-generation agent.
Choose the NEXT action from the allowed list, based on the current state.
Return ONLY JSON: {{"thought": "one sentence reason", "action": "<one allowed action>"}}
Guidance: refine when the validator found real problems (missing steps, uncovered requirements,
duplicates); accept (calculate_metrics) when the remaining issues are minor or refinements are used up."""

PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", PLANNER_SYSTEM),
    ("human", "State summary:\n{state}\n\nAllowed actions: {allowed}"),
])

CATEGORY_HINTS = {
    "Authentication": "valid/invalid credentials, empty fields, email format, lockout after repeated failures, SQL injection, session handling, password masking.",
    "Payment": "valid/expired/invalid cards, insufficient funds, gateway timeout, double submit, amount mismatch, CVV masking, receipt.",
    "Registration": "mandatory fields, duplicate email, password complexity and length boundaries, confirmation mismatch, verification email.",
    "Search": "valid keyword, empty query, no results, special characters, very long input, filters, sorting, case-insensitivity.",
    "Shopping Cart": "add/remove, quantity boundaries (0, max stock), totals, discounts, persistence across sessions.",
    "Profile": "view/update, mandatory fields, invalid phone/email, file type and size limits, persistence.",
    "Notification": "trigger events, enable/disable, content accuracy, channels, read/unread, no duplicates.",
    "Data Management": "create/edit/delete, mandatory fields, confirmation dialogs, max length, invalid types, import/export formats.",
    "General": "main flow, invalid input, mandatory inputs, authorisation, error messages, boundary values.",
}
