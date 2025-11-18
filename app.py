# app.py
# Streamlit interface for the Original Enterprise AI – Group X Prototype

import streamlit as st
from decision_engine import run_simulation, explain_decision
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# Streamlit Page Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Original Enterprise AI Prototype", layout="wide")

st.title("🧠 Original Enterprise AI – Group X Prototype")
st.markdown("""
This demo shows how *Original Enterprise AI* processes a CEO's question through  
**Group Manager → Enterprise Manager → LOCAL Nodes** and returns an explainable recommendation.
""")

# -----------------------------------------------------------------------------
# 1️⃣ CEO Question Input
# -----------------------------------------------------------------------------
st.subheader("Ask a strategic question:")

# Pre-filled example (editable by user)
question = st.text_input(
    "Strategic Query:",
    value="How can we increase steel production with minimal investment?",
    help="You can edit this question or run the simulation directly."
)

if st.button("Run Simulation"):
    with st.spinner("Running enterprise simulation..."):
        # Run the decision simulation
        result = run_simulation()

        # -----------------------------------------------------------------------------
        # 2️⃣ AI Recommendation Summary
        # -----------------------------------------------------------------------------
        st.header("AI Recommendation Summary")

        st.markdown(f"**Recommended Plant:** {result['Recommended Plant']}")
        st.markdown(f"**Expected Output Increase:** {result['Expected Output Increase']}")
        st.markdown(f"**Capital Investment:** {result['Capital Investment']}")
        st.markdown(f"**ROI Period:** {result['ROI Period']}")
        st.markdown(f"**Energy Required:** {result['Energy Required']}")

        st.info(result["Summary"])

        # -----------------------------------------------------------------------------
        # 3️⃣ Explainable AI Insight
        # -----------------------------------------------------------------------------
        st.subheader("💬 Explainable AI Insight")

        explanation = explain_decision(result["Summary"])
        if "⚠️" in explanation:
            st.warning(explanation)
        else:
            st.success(explanation)

        # -----------------------------------------------------------------------------
        # 4️⃣ Data and Decision Flow (Enhanced Sankey Diagram with Tooltips)
        # -----------------------------------------------------------------------------
        st.subheader("📊 Data and Decision Flow")

        recommended = result['Recommended Plant']
        nodes = [
            "CEO Query",
            "Group Manager",
            "Enterprise Manager (Steel)",
            "LOCAL Nodes",
            f"Recommendation → {recommended}"
        ]

        # Hover tooltips for storytelling
        hover_texts = [
            "CEO sets a strategic objective or challenge.",
            "Group Manager interprets goals and prioritizes investment areas.",
            "Enterprise Manager analyzes operational and financial feasibility.",
            "LOCAL Nodes simulate data-driven production outcomes.",
            f"Final recommendation identifies optimal plant: {recommended}."
        ]

        links = dict(
            source=[0, 1, 2, 3],
            target=[1, 2, 3, 4],
            value=[1, 1, 1, 1],
            color=["#82c4ff", "#a0d8ef", "#ffc77a", "#b2f7b2"]
        )

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=35,
                thickness=28,
                line=dict(color="white", width=0.5),
                label=nodes,
                color=["#007acc", "#5ba4cf", "#ff8c42", "#ffb677", "#33cc66"],
                hovertemplate='%{customdata}<extra></extra>',
                customdata=hover_texts
            ),
            link=links
        )])

        fig.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(size=14, color="black"),
            title_font=dict(size=18, color="black", family="sans-serif"),
            title="Enterprise Decision Flow – From Query to Action"
        )

        st.plotly_chart(fig, use_container_width=True)
