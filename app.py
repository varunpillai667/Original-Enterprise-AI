import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, explain_decision

st.set_page_config(page_title="Original Enterprise AI – Group Manager Cross-EM Demo", layout="wide")
st.title("🧠 Group Manager Cross-EM Demo — Concept Prototype")

st.markdown("""
**This prototype visualizes the concept idea and data flow for the multi-layer Original Enterprise AI architecture.**  
- Group Manager runs cross-enterprise simulations across Enterprise Managers.  
- Enterprise Managers evaluate company units (HQ + Local Nodes).  
- Local Nodes collect telemetry from OT systems at Ports & Plants.
""")

query = st.text_input("Strategic Query:", "How can we increase the steel production 2 MTPA.")
capex_limit = st.number_input("Optional CapEx limit (USD):", value=0.0, min_value=0.0, step=50000.0, format="%.2f")

if st.button("Run Simulation"):
    with st.spinner("Running cross-EM simulation..."):
        try:
            capex_value = capex_limit if capex_limit > 0 else None
            result = run_simulation(query, capex_value)

            # Recommendation card
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant:** {result['recommended_plant']}")
            st.markdown(f"**Expected Increase:** {result['expected_increase_pct']}")
            st.markdown(f"**Investment (USD):** ${result['investment_usd']:,}")
            st.markdown(f"**ROI:** {result['roi_period_months']} months")
            st.markdown(f"**Energy Required:** {result['energy_required_mw']} MW")

            # Show action plan (clear instruction) instead of generic summary or CapEx note
            action = result.get('action_plan', result.get('summary', 'No action plan available.'))
            st.info(action)

            # EM summaries and full unit details (no provenance, no doc references)
            st.subheader("Enterprise Manager Summaries — Unit Details")

            cols = st.columns(3)
            with cols[0]:
                st.markdown("**Steel EM — Top Candidates**")
                for c in result["em_summaries"]["steel_top_candidates"]:
                    st.write(f"{c['plant_id']}: +{c['feasible_increase_pct']}% — CapEx ${c['capex_estimate_usd']:,} — Energy {c['energy_required_mw']} MW")
                st.markdown("**All Steel Units (Company B):**")
                for su in result["em_summaries"].get("steel_units_details", []):
                    st.write(f"- {su['plant_id']}: capacity {su['capacity']} units, utilization {su['utilization']}, capex est ${su['capex_estimate_usd']:,}, ROI {su.get('roi_months','N/A')} months")

            with cols[1]:
                st.markdown("**Ports EM — Aggregate**")
                p = result["em_summaries"]["ports_info"]
                st.write(f"Aggregate port headroom: {p['port_headroom_units']} units (avg util {p['current_utilization']})")
                st.markdown("**All Port Units (Company A):**")
                for port in result["em_summaries"].get("port_units_details", []):
                    st.write(f"- {port['port_id']}: capacity {port['capacity']}, utilization {port['utilization']}")

            with cols[2]:
                st.markdown("**Energy EM — Aggregate**")
                e = result["em_summaries"]["energy_info"]
                st.write(f"Aggregate headroom: {e['energy_headroom_mw']} MW (avail {e['energy_available_mw']} MW)")
                st.markdown("**All Power Plant Units (Company C):**")
                for plant in result["em_summaries"].get("energy_units_details", []):
                    st.write(f"- {plant['plant_id']}: capacity {plant['capacity_mw']} MW, utilization {plant['utilization']}, avail {plant.get('available_mw','N/A')} MW")

            # Sankey visualization to show architecture flow (illustrative)
            nodes = [
                "OT Systems (SCADA/MES/TOS)", "Local Node",
                "Steel HQ (ERP)", "Steel EM",
                "Ports HQ (ERP)", "Ports EM",
                "Energy HQ (ERP)", "Energy EM",
                "Group Manager", "Recommendation"
            ]
            node_colors = ["#d6eaf8","#aed6f1","#f9e79f","#f5b7b1","#d5f5e3","#fad7a0","#d6eaf8","#f5cba7","#5dade2","#1abc9c"]
            source = [0, 0, 1, 2, 3, 4, 5, 6, 7]
            target = [1, 2, 3, 3, 8, 5, 8, 7, 8]
            value = [5, 2, 3, 4, 3, 2, 4, 3, 5]

            fig = go.Figure(data=[go.Sankey(
                node=dict(label=nodes, color=node_colors, pad=15, thickness=20),
                link=dict(source=source, target=target, value=value)
            )])
            fig.update_layout(title_text="System Connectivity & Data Flow (concept)", font_size=11)
            st.plotly_chart(fig, use_container_width=True)

            # Explainable narrative (formatted)
            st.subheader("Explainable Narrative")
            st.markdown(explain_decision(query, result))

            # Budget note: user-visible but neutral
            if result.get("budget_flag", False):
                st.warning("The CapEx limit filtered out all candidates; the recommendation shows the top candidate and flags the budget constraint.")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
