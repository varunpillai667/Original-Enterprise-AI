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
        # 4️⃣ Data and Decision Flow (Readable, Scaled & Centered)
        # -----------------------------------------------------------------------------
        st.subheader("📊 Data and Decision Flow")

        recommended = result['Recommended Plant']

        fig = go.Figure()

        # Define block layout manually for fixed coordinate space
        y_center = 0.5
        block_width = 0.15
        block_height = 0.25
        gap = 0.04

        blocks = [
            {"x": 0.0, "color": "#007acc", "title": "CEO Query",
             "desc": "Defines strategic objectives such as increasing steel output."},
            {"x": 0.2, "color": "#00b4d8", "title": "Group Manager",
             "desc": "Interprets strategy, sets enterprise targets and allocates budgets."},
            {"x": 0.4, "color": "#ff8c42", "title": "Enterprise Manager (Steel)",
             "desc": "Analyzes plant performance, investment options, and ROI scenarios."},
            {"x": 0.6, "color": "#ffc300", "title": "LOCAL Nodes",
             "desc": "Aggregate plant-level data (energy, output, cost) for modeling."},
            {"x": 0.8, "color": "#33cc66", "title": f"Recommendation → {recommended}",
             "desc": "Synthesizes all results and provides optimal actionable decision."}
        ]

        # Draw each rectangular block and its annotations
        for b in blocks:
            x0 = b["x"]
            x1 = x0 + block_width
            fig.add_shape(
                type="rect",
                x0=x0, y0=y_center - block_height / 2,
                x1=x1, y1=y_center + block_height / 2,
                line=dict(color="black", width=1.5),
                fillcolor=b["color"], opacity=0.9
            )
            fig.add_annotation(
                x=(x0 + x1) / 2, y=y_center + 0.07,
                text=f"<b>{b['title']}</b>",
                font=dict(size=16, color="white"),
                showarrow=False
            )
            fig.add_annotation(
                x=(x0 + x1) / 2, y=y_center - 0.05,
                text=f"<span style='font-size:13px;color:white'>{b['desc']}</span>",
                showarrow=False
            )

        # Draw arrows between the blocks
        for i in range(len(blocks) - 1):
            start_x = blocks[i]["x"] + block_width
            end_x = blocks[i + 1]["x"]
            fig.add_annotation(
                ax=start_x + gap / 4, ay=y_center,
                x=end_x - gap / 4, y=y_center,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True,
                arrowhead=3, arrowsize=2, arrowwidth=2, arrowcolor="black"
            )

        # Lock the coordinate system and remove axis visuals
        fig.update_xaxes(range=[-0.05, 1.05], visible=False)
        fig.update_yaxes(range=[0, 1], visible=False)

        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=60, b=20),
            paper_bgcolor="white",
            plot_bgcolor="white",
            title=dict(
                text="Enterprise Decision Flow – From Strategy to Action",
                font=dict(size=18, color="black"),
                x=0.5
            )
        )

        st.plotly_chart(fig, use_container_width=True)
