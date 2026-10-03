"""Streamlit UI:  streamlit run app.py"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from tcgen import db, export
from tcgen.preprocess import load_stories
from tcgen.service import get_components, get_settings_cached, run_generation

st.set_page_config(page_title="AI Test Case Generator", page_icon="🧪", layout="wide")
settings = get_settings_cached()
SAMPLES = json.loads((Path(__file__).parent / "data" / "sample_stories.json").read_text(encoding="utf-8"))


@st.cache_resource(show_spinner="Loading TensorFlow models and LLM (first run trains the classifiers)...")
def load_components():
    return get_components()


comp = load_components()

st.title("🧪 AI Test Case Generator")
st.caption("TensorFlow story analysis · LangChain tools · single Agentic AI loop · Generative AI test authoring")

with st.sidebar:
    st.subheader("System status")
    st.write(f"**LLM:** `{comp.llm_status}`")
    st.write(f"**TensorFlow classifier:** `{comp.ml.mode}`")
    if comp.ml.error:
        st.caption(comp.ml.error)
    st.write(f"**Embeddings:** `{settings.embedding_backend}`")
    st.write(f"**Max refinement rounds:** {settings.max_refinements}")
    st.info("Offline mode uses curated templates. Set LLM_PROVIDER + API key in `.env` for full GenAI output.")


def render(result: dict, key: str):
    m, c = result["metrics"], result["classification"]
    st.subheader("Story analysis")
    a, b, d, e = st.columns(4)
    a.metric("Category", c["category"], f'{c["category_confidence"]:.0%} confidence')
    b.metric("Story quality", c["quality"], f'{c["quality_score"]:.0f}% complete')
    d.metric("Requirements", m["requirements"])
    e.metric("Refinement rounds", m["refinements"])

    st.subheader("Test case summary")
    a, b, d, e, f = st.columns(5)
    a.metric("Total", m["total"])
    b.metric("Positive / Negative", f'{m["positive"]} / {m["negative"]}')
    d.metric("Requirement coverage", f'{m["coverage_percent"]:.0f}%')
    e.metric("Relevance", f'{m["relevance_percent"]:.0f}%')
    f.metric("Duplicates", f'{m["duplicate_percent"]:.0f}%')
    (st.success if m["meets_target"] else st.warning)(
        "Meets the 80%+ coverage and relevance target." if m["meets_target"]
        else "Below the 80% target - see uncovered requirements below.")

    st.dataframe(export.cases_df(result["test_cases"]), use_container_width=True, hide_index=True)

    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇ Excel", export.to_excel_bytes(result), "test_cases.xlsx", key=f"x{key}",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    d2.download_button("⬇ CSV", export.to_csv_bytes(result["test_cases"]), "test_cases.csv", "text/csv", key=f"c{key}")
    d3.download_button("⬇ JSON", export.to_json_str(result), "test_cases.json", "application/json", key=f"j{key}")

    with st.expander("Extracted requirements and coverage"):
        rows = [{"ID": r["id"], "Requirement": r["text"],
                 "Covered": m["coverage_detail"].get(r["id"], {}).get("covered"),
                 "Best test case": m["coverage_detail"].get(r["id"], {}).get("best_case")}
                for r in result["analysis"]["requirements"]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander("Agent trace (plan → act → observe)"):
        for t in result["trace"]:
            st.markdown(f"**{t['step']}. `{t['action']}`** — _{t['thought']}_  \n{t['observation']}  ({t['seconds']}s)")


tab_gen, tab_batch, tab_hist = st.tabs(["Generate", "Batch", "History"])

with tab_gen:
    choice = st.selectbox("Load a sample story", ["(write my own)"] + [f'{s["id"]}. {s["title"]}' for s in SAMPLES])
    default = "" if choice.startswith("(") else next(s["user_story"] for s in SAMPLES if choice.startswith(f'{s["id"]}.'))
    story = st.text_area("User story", value=default, height=120, key=f"story_{choice}",
                         placeholder="As a user, I want to ... so that ...")
    if st.button("Generate test cases", type="primary"):
        try:
            with st.spinner("Agent is analysing, generating, validating and refining..."):
                st.session_state["result"] = run_generation(story)
        except ValueError as exc:
            st.error(str(exc))
    if "result" in st.session_state:
        render(st.session_state["result"], "single")

with tab_batch:
    up = st.file_uploader("Upload stories (.txt: one per line/paragraph, or .json)", type=["txt", "json"])
    stories = load_stories(up.name, up.getvalue()) if up else []
    use_samples = st.checkbox("Use the built-in sample stories", value=not up)
    if use_samples:
        stories = [s["user_story"] for s in SAMPLES]
    st.write(f"{len(stories)} stories ready")
    if stories and st.button("Run batch"):
        results, bar = [], st.progress(0.0)
        for i, s in enumerate(stories, 1):
            results.append(run_generation(s))
            bar.progress(i / len(stories))
        st.session_state["batch"] = results
    if "batch" in st.session_state:
        res = st.session_state["batch"]
        table = pd.DataFrame([{"Story": r["story"][:80], "Category": r["classification"]["category"],
                               "Quality": r["classification"]["quality"], "Cases": r["metrics"]["total"],
                               "Coverage %": r["metrics"]["coverage_percent"],
                               "Relevance %": r["metrics"]["relevance_percent"]} for r in res])
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.metric("Average coverage / relevance",
                  f'{table["Coverage %"].mean():.0f}% / {table["Relevance %"].mean():.0f}%')
        st.download_button("⬇ All test cases (Excel)", export.batch_excel_bytes(res), "batch_test_cases.xlsx")

with tab_hist:
    rows = db.list_stories(settings.db_path)
    if not rows:
        st.info("No runs saved yet.")
    else:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        sid = st.selectbox("Show test cases for story id", [r["story_id"] for r in rows])
        st.dataframe(pd.DataFrame(db.get_cases(settings.db_path, sid)), use_container_width=True, hide_index=True)
