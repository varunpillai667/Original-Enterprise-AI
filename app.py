# app.py
import streamlit as st
from decision_engine import run_simulation, rationale_for_action_plan
import plotly.graph_objects as go

# INTERNAL (not shown in UI): path to uploaded operational flow doc (for tooling only)
DOC_PATH = "/mnt/data/Operational Flow.docx"

st.set_page_config(page_title="Original Enterprise AI – Group Manager Cross-EM Demo", layout="wide")
st.title("🧠 Group Manager Cross-EM Demo — Concept Prototype")

st.markdown(
    """
**This prototype visualizes the concept idea and data flow for the multi-layer Original Enterprise AI architecture.**  
- Group Manager runs cross-enterprise simulations across Enterprise Managers.  
- Enterprise Managers evaluate company units (HQ + Local Nodes).  
- Local Nodes collect telemetry from OT systems at Ports & Plants.
"""
)

# Default strategic query
query = st.text_input("Strategic Query:", "How can we increase the steel production 2 MTPA.")
capex_limit = st.number_input(
    "Optional CapEx limit (USD):",
    value=0.0,
    min_value=0.0,
    step=50000.0,
    format="%.2f"
)

if st.button("Run Simulation"):
    with st.spinner("Running cross-EM simulation..."):
        try:
            capex_value = capex_limit if capex_limit > 0 else None
            result = run_simulation(query, capex_value)

            # Recommendation card
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant:** {result.get('recommended_plant', 'N/A')}")
            st.markdown(f"**Expected Increase:** {result.get('expected_increase_pct', 'N/A')}")
            inv = result.get('investment_usd')
            st.markdown(f"**Investment (USD):** ${inv:,}" if isinstance(inv, (int, float)) else f"**Investment (USD):** {inv}")
            st.markdown(f"**ROI:** {result.get('roi_period_months', 'N/A')} months")
            st.markdown(f"**Energy Required:** {result.get('energy_required_mw', 'N/A')} MW")

            # Show action plan (clear instruction)
            action = result.get('action_plan', result.get('summary', 'No action plan available.'))
            st.info(action)

            # Enterprise Manager Summaries — Unit Details
            st.subheader("Enterprise Manager Summaries — Unit Details")

            cols = st.columns(3)
            with cols[0]:
                st.markdown("**Steel EM — Top Candidates**")
                for c in result["em_summaries"].get("steel_top_candidates", []):
                    st.write(
                        f"{c.get('plant_id','N/A')}: +{c.get('feasible_increase_pct','N/A')}% — "
                        f"CapEx ${c.get('capex_estimate_usd','N/A'):,} — Energy {c.get('energy_required_mw','N/A')} MW"
                    )
                st.markdown("**All Steel Units (Company B):**")
                for su in result["em_summaries"].get("steel_units_details", []):
                    st.write(
                        f"- {su.get('plant_id','N/A')}: capacity {su.get('capacity','N/A')} units, "
                        f"utilization {su.get('utilization','N/A')}, capex est ${su.get('capex_estimate_usd','N/A'):,}, "
                        f"ROI {su.get('roi_months','N/A')} months"
                    )

            with cols[1]:
                st.markdown("**Ports EM — Aggregate**")
                p = result["em_summaries"].get("ports_info", {})
                st.write(
                    f"Aggregate port headroom: {p.get('port_headroom_units','N/A')} units "
                    f"(avg util {p.get('current_utilization','N/A')})"
                )
                st.markdown("**All Port Units (Company A):**")
                for port in result["em_summaries"].get("port_units_details", []):
                    st.write(f"- {port.get('port_id','N/A')}: capacity {port.get('capacity','N/A')}, utilization {port.get('utilization','N/A')}")

            with cols[2]:
                st.markdown("**Energy EM — Aggregate**")
                e = result["em_summaries"].get("energy_info", {})
                st.write(
                    f"Aggregate headroom: {e.get('energy_headroom_mw','N/A')} MW "
                    f"(avail {e.get('energy_available_mw','N/A')} MW)"
                )
                st.markdown("**All Power Plant Units (Company C):**")
                for plant in result["em_summaries"].get("energy_units_details", []):
                    st.write(
                        f"- {plant.get('plant_id','N/A')}: capacity {plant.get('capacity_mw','N/A')} MW, "
                        f"utilization {plant.get('utilization','N/A')}, avail {plant.get('available_mw','N/A')} MW"
                    )

            # ---------- MINIMAL, READABLE DATA FLOW (text-based) ----------
            # The user asked for simple, minimum and readable data flow; no system connectivity diagram.
            st.subheader("Data Flow (simple)")
            # Use HTML for crisp, dark, readable typography. This is intentionally minimal and centered.
            data_flow_html = """
<div style="font-family:Arial, Helvetica, sans-serif; color:#111111; font-size:16px; line-height:1.4;">
  <div style="text-align:center; margin-bottom:10px;">
    <strong>OT Systems</strong> &nbsp;→&nbsp; <strong>Local Node</strong> &nbsp;→&nbsp;
    <strong>Enterprise Managers</strong> (Steel · Ports · Energy) &nbsp;→&nbsp;
    <strong>Group Manager</strong> &nbsp;→&nbsp; <strong>Recommendation</strong>
  </div>
  <div style="text-align:center; color:#333333; font-size:13px;">
    Data flows: OT telemetry (SCADA/MES/TOS) → Local Node preprocessing → EM evaluations → Group-level orchestration.
  </div>
</div>
"""
            st.markdown(data_flow_html, unsafe_allow_html=True)

            # Rationale for Action Plan (explains why the plan was given, based on data)
            st.subheader("Rationale for Action Plan")
            rationale_md = rationale_for_action_plan(query, result)
            # Render rationale as markdown (it is already formatted)
            st.markdown(rationale_md)

            # Budget note (neutral)
            if result.get("budget_flag", False):
                st.warning("The CapEx limit filtered out all candidates; the recommendation shows the top candidate and flags the budget constraint.")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
