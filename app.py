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
question = st.text_input("Example: How can we increase steel production with minimal investment?")

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
        # 4️⃣ Data and Decision Flow (Sankey Diagram)
        # -----------------------------------------------------------------------------
        st.subheader("📊 Data and Decision Flow")

        # Define node labels
        nodes = [
            "CEO Query",
            "Group Manager",
            "Enterprise Manager (Steel)",
            "LOCAL Nodes",
            "Recommendation"
        ]

        # Define links between nodes (fixed structure)
        links = dict(
            source=[0, 1, 2, 3],
            target=[1, 2, 3, 4],
            value=[1, 1, 1, 1]
        )

        # Create the Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=25,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color=["#1f77b4", "#6baed6", "#e6550d", "#fdae6b", "#31a354"]
            ),
            link=links
        )])

        fig.update_layout(
            height=300,
            paper_bgcolor="#f9f9f9",
            plot_bgcolor="#f9f9f9",
            font=dict(size=13, color="black")
        )

        st.plotly_chart(fig, use_container_width=True)
