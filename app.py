import streamlit as st
from decision_engine import run_simulation, explain_decision
import plotly.graph_objects as go

st.set_page_config(page_title="Original Enterprise AI – Group X Prototype", layout="wide")

st.title("🧠 Original Enterprise AI – Group X Prototype")
st.write("""
This demo shows how *Original Enterprise AI* processes a CEO's question 
through Group Manager → Enterprise Manager → LOCAL Nodes 
and returns an explainable recommendation.
""")

query = st.text_input("Ask a strategic question:", "How can we increase steel production with minimal investment?")

if st.button("Run Simulation"):
    result = run_simulation()

    st.subheader("AI Recommendation Summary")
    st.write(f"**Recommended Plant:** {result['recommended_plant']}")
    st.write(f"**Expected Output Increase:** {result['expected_output_increase']}")
    st.write(f"**Capital Investment:** {result['capex']}")
    st.write(f"**ROI Period:** {result['roi_period']}")
    st.write(f"**Energy Required:** {result['energy_required_mw']} MW from {result['port_dependency']}")
    st.info(result["narrative"])

    st.subheader("💬 Explainable AI Insight")
    st.write(explain_decision(result["narrative"]))

    fig = go.Figure(go.Sankey(
        node=dict(label=["CEO Query", "Group Manager", "Enterprise Manager (Steel)", "LOCAL Nodes", "Recommendation"]),
        link=dict(source=[0,1,2,3], target=[1,2,3,4], value=[1,1,1,1])
    ))
    fig.update_layout(title_text="Data and Decision Flow", font_size=12)
    st.plotly_chart(fig)
