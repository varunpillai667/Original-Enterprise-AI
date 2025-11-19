# app.py
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, rationale_for_action_plan

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

# Default strategic query requested by you
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

            # Show action plan (clear instruction) instead of generic summary or CapEx note
            action = result.get('action_plan', result.get('summary', 'No action plan available.'))
            st.info(action)

            # Enterprise Manager Summaries — Unit Details (no provenance, no document references)
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

            # ---------- SIMPLE, MINIMAL, READABLE SANKey ----------
            st.subheader("System Connectivity & Data Flow (concept)")

            # Clear, short nodes
            nodes = [
                "OT Systems",         # 0
                "Local Node",         # 1
                "Steel EM",           # 2
                "Ports EM",           # 3
                "Energy EM",          # 4
                "Group Manager",      # 5
                "Recommendation"      # 6
            ]

            # We draw only the obvious primary flows: OT->LocalNode, LocalNode->SteelEM, HQ->EMs (collapsed),
            # EMs -> Group Manager, Group Manager -> Recommendation.
            # Keep values small and consistent so widths are readable.
            source = [0, 1, 2, 3, 4, 5]
            target = [1, 2, 5, 5, 5, 6]
            value  = [3, 2, 1, 1, 1, 2]  # illustrative weights

            node_colors = ["#E8F3FF", "#D6EBFF", "#F5E6E6", "#E8F7EA", "#FFF3D6", "#DDEBF7", "#D1F0E1"]
            link_color = "rgba(120,120,120,0.4)"  # neutral gray links

            fig = go.Figure(go.Sankey(
                arrangement="fixed",
                node = dict(
                    pad = 20,
                    thickness = 18,
                    line = dict(color = "black", width = 0.5),
                    label = nodes,
                    color = node_colors,
                    x=[0.0, 0.15, 0.45, 0.45, 0.45, 0.75, 0.95],  # horizontal positions to keep layout compact and linear
                    y=[0.5, 0.5, 0.2, 0.5, 0.8, 0.5, 0.5]          # vertical positions to avoid overlap
                ),
                link = dict(
                    source = source,
                    target = target,
                    value = value,
                    color = [link_color] * len(source)
                )
            ))

            # Minimal, readable layout
            fig.update_layout(
                margin=dict(l=10, r=10, t=20, b=10),
                font=dict(size=12),
                title_text="Simple Data Flow — OT → Local Node → EMs → Group",
                height=300
            )

            st.plotly_chart(fig, use_container_width=True)

            # Rationale for Action Plan (explains why the plan was given, based on data)
            st.subheader("Rationale for Action Plan")
            rationale_md = rationale_for_action_plan(query, result)
            st.markdown(rationale_md)

            # Budget note: user-visible but neutral (keeps user informed)
            if result.get("budget_flag", False):
                st.warning("The CapEx limit filtered out all candidates; the recommendation shows the top candidate and flags the budget constraint.")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
