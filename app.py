import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, explain_decision

st.set_page_config(page_title="Original Enterprise AI – Group Manager Cross-EM Demo", layout="wide")
st.title("🧠 Group Manager Cross-EM Demo — explicit provenance removed")

st.markdown("""
**This prototype visualizes the concept idea and data flow for the multi-layer Original Enterprise AI architecture.**  
- Group Manager reads group-level signals (market, treasury, ESG).  
- Enterprise Managers read Company HQ systems (ERP/Finance) and Local Nodes (OT telemetry).  
- Local Nodes collect telemetry from OT systems at Ports & Plants (SCADA, MES, TOS).
""")

# Updated default strategic query per request
query = st.text_input("Strategic Query:", "How can we increase the steel production 2 MTPA.")
capex_limit = st.number_input("Optional CapEx limit (USD):", value=0.0, min_value=0.0, step=10000.0, format="%.2f")

if st.button("Run Simulation"):
    with st.spinner("Running cross-EM orchestration (Group Manager)..."):
        try:
            capex_value = capex_limit if capex_limit > 0 else None
            result = run_simulation(query, capex_value)

            # Top-level recommendation
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant:** {result['recommended_plant']}")
            st.markdown(f"**Expected Increase:** {result['expected_increase_pct']}")
            st.markdown(f"**Investment (USD):** {result['investment_usd']}")
            st.markdown(f"**ROI:** {result['roi_period_months']} months")
            st.markdown(f"**Energy Required:** {result['energy_required_mw']} MW")
            st.info(result['summary'])

            # EM summaries — show top candidates and full unit lists + details for ports & plants
            st.subheader("Enterprise Manager Summaries (what each EM returned)")

            cols = st.columns(3)
            with cols[0]:
                st.markdown("**Steel EM (Top candidates)**")
                for c in result["em_summaries"]["steel_top_candidates"]:
                    st.write(f"{c['plant_id']}: +{c['feasible_increase_pct']}% — CapEx ${c['capex_estimate_usd']:,} — Energy {c['energy_required_mw']} MW")
                st.markdown("**All Steel Units (Company B):**")
                # display full steel units and a short status per unit if available
                steel_units = result["em_summaries"].get("steel_units_details", [])
                for su in steel_units:
                    st.write(f"- {su['plant_id']}: capacity {su['capacity']}, utilization {su['utilization']}, capex est ${su['capex_estimate_usd']:,}")

            with cols[1]:
                st.markdown("**Ports EM**")
                p_summary = result["em_summaries"]["ports_info"]
                st.write(f"Aggregate port headroom: {p_summary['port_headroom_units']} units (util {p_summary['current_utilization']})")
                st.markdown("**All Port Units (Company A):**")
                for port in result["em_summaries"].get("port_units_details", []):
                    st.write(f"- {port['port_id']}: capacity {port['capacity']}, utilization {port['utilization']}")

            with cols[2]:
                st.markdown("**Energy EM**")
                e_summary = result["em_summaries"]["energy_info"]
                st.write(f"Aggregate headroom: {e_summary['energy_headroom_mw']} MW (avail {e_summary['energy_available_mw']} MW)")
                st.markdown("**All Power Plant Units (Company C):**")
                for plant in result["em_summaries"].get("energy_units_details", []):
                    st.write(f"- {plant['plant_id']}: capacity {plant['capacity_mw']} MW, utilization {plant['utilization']}")

            # Sankey visualization (unchanged)
            nodes = [
                "SCADA/MES/TOS (OT)", "Local Node",
                "Steel HQ (ERP)", "Steel EM",
                "Ports HQ (ERP)", "Ports EM",
                "Energy HQ (ERP)", "Energy EM",
                "Group Systems", "Group Manager", "Recommendation"
            ]
            node_colors = ["#d6eaf8","#aed6f1","#f9e79f","#f5b7b1","#d5f5e3","#fad7a0","#d6eaf8","#f5cba7","#d2b4de","#5dade2","#1abc9c"]
            source = [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            target = [1, 2, 3, 3, 9, 5, 9, 7, 9, 9, 10]
            value = [5, 2, 3, 4, 4, 2, 4, 3, 2, 5, 8]

            fig = go.Figure(data=[go.Sankey(
                node=dict(label=nodes, color=node_colors, pad=15, thickness=20),
                link=dict(source=source, target=target, value=value)
            )])
            fig.update_layout(title_text="System Connectivity & Data Flow (OT → LOCAL → EMs/HQ → Group)", font_size=11)
            st.plotly_chart(fig, use_container_width=True)

            # Explainable narrative
            st.subheader("Explainable Narrative")
            st.write(explain_decision(query, result))

            if result.get("provenance", {}).get("budget_flag", False):
                st.warning("CapEx limit filtered candidates; the recommendation shows the top candidate with a budget flag.")

        except Exception as e:
            st.error(f"Simulation Error: {e}")
