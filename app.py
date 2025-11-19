import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, explain_decision

# --- PAGE SETUP ---
st.set_page_config(page_title="Original Enterprise AI – Group X Prototype", layout="wide")

st.title("🧠 Original Enterprise AI – Group X Prototype (Aligned Prototype)")

st.markdown("""
This demo shows how **Original Enterprise AI** processes a CEO’s question through  
**Group Manager → Enterprise Manager → Local Nodes (Ports & Plants)** and returns an explainable recommendation.
""")

# --- STRATEGIC QUERY INPUT ---
st.subheader("Ask a strategic question:")
st.write("Example: *How can we increase steel production with minimal investment?*")

query = st.text_input("Strategic Query:", "How can we increase steel production with minimal investment?")
capex_limit = st.number_input("Optional CapEx limit (USD):", value=0.0, min_value=0.0, step=10000.0, format="%.2f")

if st.button("Run Simulation"):
    with st.spinner("Running enterprise-wide simulation..."):
        try:
            capex_limit_value = capex_limit if capex_limit > 0 else None
            result = run_simulation(query, capex_limit_value)

            st.subheader("AI Recommendation Summary")
            st.markdown(f"**Recommended Plant:** {result['recommended_plant']}")
            st.markdown(f"**Expected Output Increase:** {result['expected_increase_pct']}")
            st.markdown(f"**Capital Investment (USD):** {result['investment_usd']}")
            st.markdown(f"**ROI Period:** {result['roi_period_months']} months")
            st.markdown(f"**Energy Required:** {result['energy_required_mw']} MW")
            st.info(result['summary'])

            # --- EXPLAINABLE AI INSIGHT ---
            st.subheader("💭 Explainable AI Insight")
            explanation = explain_decision(query, result)
            st.write(explanation)

            # --- DATA AND DECISION FLOW ---
            st.subheader("📊 Data and Decision Flow")
            st.caption("Integrated Decision Flow – Strategy, Logistics, and Operations")

            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=30,
                    thickness=25,
                    line=dict(color="black", width=0.5),
                    label=[
                        "CEO Query",
                        "Group Manager",
                        "Enterprise Manager (Steel)",
                        "Port (Import)",
                        f"{result['recommended_plant']}",
                        "Port (Export)",
                        "Final Recommendation"
                    ],
                    color=[
                        "#3498db", "#5dade2", "#ec7063",
                        "#28b463", "#f39c12", "#17a589", "#1abc9c"
                    ],
                ),
                link=dict(
                    source=[0, 1, 2, 3, 4, 5],
                    target=[1, 2, 3, 4, 5, 6],
                    value=[10, 10, 10, 10, 10, 10],
                    color="rgba(160,160,160,0.5)"
                )
            )])

            fig.update_layout(
                title_text="Integrated Decision Flow – From CEO Strategy to Operational Action",
                font=dict(size=14, color="black"),
                plot_bgcolor="white",
                paper_bgcolor="white"
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Simulation Error: {e}")
