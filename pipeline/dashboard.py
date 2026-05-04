import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="LLM Benchmark Dashboard",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 LLM Coding Benchmark Dashboard")
st.caption("StackEval-style evaluation · Python · Debugging, Implementation, Conceptual · Judge: GPT-4o")

#load data 

@st.cache_data
def load_data():
    """
    Merges prompt.csv (model answers) with eval.csv (judge scores) into one dataframe.
    difficulty is already in prompt.csv from answer.py, so no need to re-merge questions.csv.
    """
    answers = pd.read_csv("prompt.csv")
    scores  = pd.read_csv("eval.csv")

    # Merge on all shared keys to avoid duplicate columns
    merge_keys = ["question_id", "model", "category", "difficulty"]
    combined = pd.merge(answers, scores, on=merge_keys, how="left")

    # accepted = score >= 2 (Acceptable or Optimal)
    combined["accepted"] = combined["llm_score"].apply(
        lambda s: 1 if str(s) in ("2", "3") else 0
    )

    return combined


# Load data — show error if files are missing
try:
    df = load_data()
except FileNotFoundError as e:
    st.error(f"Missing file: {e}\n\nMake sure you have run answer.py and evaluate.py first.")
    st.stop()

tab1, tab2 = st.tabs([ "🔍 Answer Browser", "📊 Leaderboard"])

#Tab 1: Answer browser
with tab1:
    st.subheader("Browse Model Answers per Question")

    # Sidebar filters
    st.sidebar.subheader("Answer Browser Filters")

    sb_cat = st.sidebar.selectbox(
        "Category",
        ["All"] + sorted(df["category"].dropna().unique().tolist()),
        key="sb_cat"
    )
    sb_diff = st.sidebar.selectbox(
        "Difficulty",
        ["All"] + sorted(df["difficulty"].dropna().unique().tolist()),
        key="sb_diff"
    )

    # Filter to get matching questions 
    browser_df = df.copy()
    if sb_cat != "All":
        browser_df = browser_df[browser_df["category"] == sb_cat]
    if sb_diff != "All":
        browser_df = browser_df[browser_df["difficulty"] == sb_diff]

    question_ids = sorted(browser_df["question_id"].unique().tolist())

    if not question_ids:
        st.warning("No questions match the selected filters.")
        st.stop()

    st.write(f"**{len(question_ids)} questions** match current filters")

    selected_q = st.selectbox(
        "Select question",
        question_ids,
        key="sb_q"
    )

    q_rows = browser_df[browser_df["question_id"] == selected_q]

    if q_rows.empty:
        st.info("No data for this question.")
        st.stop()

    # ── Question metadata 
    first_row = q_rows.iloc[0]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Question ID", selected_q)
    col_b.metric("Category", first_row.get("category", "—").capitalize())
    col_c.metric("Difficulty", str(first_row.get("difficulty", "—")).capitalize())

    st.divider()

    # ── Question text 
    st.markdown("#### 📝 Question")
    st.write(first_row.get("question_text", "—"))

    # ── Reference answer 
    with st.expander("✅ Stack Overflow Accepted Answer (reference)", expanded=False):
        st.write(first_row.get("accepted_answer", "—"))

    st.divider()

    # ── Model answers 
    st.markdown("#### 🤖 Model Answers")

    models_in_q = sorted(q_rows["model"].unique().tolist())

    for model in models_in_q:
        model_row = q_rows[q_rows["model"] == model].iloc[0]
        score = model_row.get("llm_score", "?")
        accepted = str(score) in ("2", "3")

        score_label = {
            "0": "0 — Fully unacceptable",
            "1": "1 — Useful but unacceptable",
            "2": "2 — Acceptable ✅",
            "3": "3 — Optimal ✅",
        }.get(str(score), f"Score: {score}")

        # Color the card header based on accepted/not
        header_color = "🟢" if accepted else "🔴"

        with st.expander(f"{header_color} **{model}** — {score_label}", expanded=True):
            st.markdown("**Model answer:**")
            st.write(model_row.get("model_answer", "—"))

            st.markdown("**Judge reasoning:**")
            st.caption(model_row.get("llm_reason", "No reasoning recorded."))


# Tab 2: Leaderboard
with tab2:
    st.subheader("Model Performance Leaderboard")

    # ── Filters 
    col1, col2 = st.columns(2)

    with col1:
        cat_options = ["All"] + sorted(df["category"].dropna().unique().tolist())
        selected_cat = st.selectbox("Category", cat_options, key="lb_cat")

    with col2:
        diff_options = ["All"] + sorted(df["difficulty"].dropna().unique().tolist())
        selected_diff = st.selectbox("Difficulty", diff_options, key="lb_diff")

    # ── Apply filters 
    filtered = df.copy()
    if selected_cat != "All":
        filtered = filtered[filtered["category"] == selected_cat]
    if selected_diff != "All":
        filtered = filtered[filtered["difficulty"] == selected_diff]

    st.write(f"Showing results for **{filtered['question_id'].nunique()} questions**")

    # ── Top metrics 
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total questions", filtered["question_id"].nunique())
    m2.metric("Total responses", len(filtered))
    m3.metric("Models tested", filtered["model"].nunique())
    m4.metric("Judge model", "GPT-4o")

    st.divider()

    # ── Leaderboard table 
    st.markdown("#### Acceptance Rate by Model (score ≥ 2)")

    leaderboard = (
        filtered.groupby("model")
        .agg(
            acceptance_rate=("accepted", "mean"),
            avg_score=("llm_score", lambda x: pd.to_numeric(x, errors="coerce").mean()),
            accepted=("accepted", "sum"),
            total=("accepted", "count"),
        )
        .reset_index()
        .sort_values("acceptance_rate", ascending=False)
    )

    leaderboard["acceptance_rate"] = (leaderboard["acceptance_rate"] * 100).round(1)
    leaderboard["avg_score"] = leaderboard["avg_score"].round(2)
    leaderboard["result"] = leaderboard["accepted"].astype(str) + " / " + leaderboard["total"].astype(str)

    leaderboard_display = leaderboard[["model", "acceptance_rate", "avg_score", "result"]].rename(columns={
        "model": "Model",
        "acceptance_rate": "Acceptance Rate (%)",
        "avg_score": "Average Score",
        "result": "Accepted / Total"
    })

    st.dataframe(leaderboard_display, use_container_width=True, hide_index=True)

    st.divider()

    # ── Per-category breakdown 
    st.markdown("#### Acceptance Rate by Model × Category")

    cat_breakdown = (
        filtered.groupby(["model", "category"])
        .agg(acceptance_rate=("accepted", "mean"))
        .reset_index()
    )
    cat_breakdown["acceptance_rate"] = (cat_breakdown["acceptance_rate"] * 100).round(1)

    pivot = cat_breakdown.pivot(index="model", columns="category", values="acceptance_rate").reset_index()
    pivot.columns.name = None

    st.dataframe(pivot, use_container_width=True, hide_index=True)

    st.divider()

    # ── Score distribution 
    st.markdown("#### Score Distribution by Model")

    score_dist = (
        filtered.groupby(["model", "llm_score"])
        .size()
        .reset_index(name="count")
    )
    score_dist["llm_score"] = score_dist["llm_score"].astype(str)
    score_dist_pivot = score_dist.pivot(index="model", columns="llm_score", values="count").fillna(0).astype(int).reset_index()
    score_dist_pivot.columns.name = None

    st.dataframe(score_dist_pivot, use_container_width=True, hide_index=True)
