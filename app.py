import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, explain_decision

st.set_page_config(page_title="Original Enterprise AI – Group X Prototype", layout="wide")
st.title("🧠 Original Enterprise AI – Group Manager Cross-EM Demo")

st.markdown("""
This demo shows the **Group Manager** orchestrating across multiple Enterprise Managers:
- Steel EM (manufacturing)
- Ports EM (logistics)
- Energy EM (power)
""")

query = st.text_input("Strategic Query:", "How can we increase steel production with minimal investment?")
capex_limit = st.number_input("Optional CapEx limit (USD):", value=0.0, min_value=0.0, step=10000.0, format="%.2f")

if st.button("Run Simulation"):
    with st.spinner("Running cross-EM simulation..."):
        try:
            capex_value = capex_limit if capex_limit > 0 else None
            result = run_simulation(query, capex_value)

            # Recommendation summary
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant:** {result['recommended_plant']}")
            st.markdown(f"**Expected Increase:** {result['expected_increase_pct']}")
            st.markdown(f"**Investment (USD):** {result['investment_usd']}")
            st.markdown(f"**ROI:** {result['roi_period_months']} months")
            st.markdown(f"**Energy Required:** {result['energy_required_mw']} MW")
            st.info(result['summary'])

            # EM summaries (concise, not raw snapshots)
            st.subheader("Enterprise Manager Summaries (inputs to Group Manager)")
            cols = st.columns(3)
            with cols[0]:
                st.markdown("**Steel EM (Top candidates)**")
                for c in result["em_summaries"]["steel_top_candidates"]:
                    st.write(f"{c['plant_id']}: +{c['feasible_increase_pct']}%  — CapEx ${c['capex_estimate_usd']:,} — Energy {c['energy_required_mw']} MW")
            with cols[1]:
                st.markdown("**Ports EM**")
                p = result["em_summaries"]["ports_info"]
                st.write(f"Port headroom: {p['port_headroom_units']} units (util {p['current_utilization']})")
            with cols[2]:
                st.markdown("**Energy EM**")
                e = result["em_summaries"]["energy_info"]
                st.write(f"Headroom: {e['energy_headroom_mw']} MW (avail {e['energy_available_mw']} MW)")

            # Sankey showing flow: CEO -> GM -> EMs -> Recommendation
            nodes = ["CEO Query", "Group Manager", "Steel EM", "Ports EM", "Energy EM", "Recommendation"]
            label_colors = ["#3498db", "#5dade2", "#ec7063", "#28b463", "#f39c12", "#1abc9c"]
            fig = go.Figure(data=[go.Sankey(
                node=dict(label=nodes, color=label_colors, pad=20, thickness=20),
                link=dict(
                    source=[0, 1, 1, 1],
                    target=[1, 2, 3, 4],
                    value=[1, 1, 1, 1]
                )
            )])
            fig.update_layout(title_text="Cross-EM Orchestration Flow", font_size=12)
            st.plotly_chart(fig, use_container_width=True)

            # Explainable narrative
            st.subheader("Explainable Narrative")
            st.write(explain_decision(query, result))

            if result.get("budget_flag", False):
                st.warning("CapEx limit filtered out candidates. Shown recommendation flags budget constraint.")

        except Exception as e:
            st.error(f"Simulation Error: {e}")
