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
        # 4️⃣ Data and Decision Flow (Clear, Descriptive Version)
        # -----------------------------------------------------------------------------
        st.subheader("📊 Data and Decision Flow")

        recommended = result['Recommended Plant']

        # Create figure
        fig = go.Figure()

        # Define block properties
        blocks = [
            {"x0": 0.05, "x1": 0.23, "color": "#007acc", "title": "CEO Query",
             "desc": "Defines strategic objective (e.g., increase steel production)."},
            {"x0": 0.25, "x1": 0.43, "color": "#00b4d8", "title": "Group Manager",
             "desc": "Interprets goal, prioritizes projects, and allocates budget."},
            {"x0": 0.45, "x1": 0.63, "color": "#ff8c42", "title": "Enterprise Manager (Steel)",
             "desc": "Analyzes capacity, evaluates investments, and forecasts ROI."},
            {"x0": 0.65, "x1": 0.83, "color": "#ffc300", "title": "LOCAL Nodes",
             "desc": "Simulate plant data (energy, output, logistics, etc.)."},
            {"x0": 0.85, "x1": 0.98, "color": "#33cc66", "title": f"Recommendation → {recommended}",
             "desc": "Synthesizes results and presents optimal decision."},
        ]

        # Add rectangles (blocks)
        for b in blocks:
            fig.add_shape(
                type="rect",
                x0=b["x0"], y0=0.3, x1=b["x1"], y1=0.7,
                line=dict(color="black", width=1.2),
                fillcolor=b["color"],
                opacity=0.9
            )
            fig.add_annotation(
                x=(b["x0"] + b["x1"]) / 2, y=0.6,
                text=f"<b>{b['title']}</b>",
                showarrow=False, font=dict(size=16, color="white")
            )
            fig.add_annotation(
                x=(b["x0"] + b["x1"]) / 2, y=0.42,
                text=f"<span style='font-size:12px;color:white'>{b['desc']}</span>",
                showarrow=False
            )

        # Add arrows between blocks
        arrow_positions = [(0.23, 0.5), (0.43, 0.5), (0.63, 0.5), (0.83, 0.5)]
        for (x, y) in arrow_positions:
            fig.add_annotation(
                ax=x, ay=y, axref="x", ayref="y",
                x=x + 0.015, y=y,
                showarrow=True,
                arrowhead=3, arrowsize=2, arrowwidth=2, arrowcolor="black"
            )

        # Layout configuration
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="white",
            plot_bgcolor="white",
            title=dict(
                text="Enterprise Decision Flow – From Strategy to Action",
                font=dict(size=18, color="black"),
                x=0.5
            )
        )

        st.plotly_chart(fig, use_container_width=True)
