# app.py
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, rationale_for_action_plan

# INTERNAL (tooling only): local path to uploaded doc (not shown in UI)
FILE_URL = "/mnt/data/Operational Flow.docx"

st.set_page_config(page_title="Original Enterprise AI – Group Manager Cross-EM Demo", layout="wide")
st.title("🧠 Group Manager Cross-EM Demo — Concept Prototype (Diagram)")

st.markdown(
    """
This prototype visualizes the concept idea and data flow for the multi-layer Original Enterprise AI architecture.

- Group Manager runs cross-enterprise simulations across Enterprise Managers.
- Enterprise Managers evaluate company units (HQ + Local Nodes).
- Local Nodes collect telemetry from OT systems at each factory/port/power plant.
"""
)

# Exact strategic query requested
query = st.text_input("Strategic Query:", "How can we increase the steel production by 2 MTPA.")
capex_limit = st.number_input(
    "Optional CapEx limit (USD):",
    value=0.0,
    min_value=0.0,
    step=50000.0,
    format="%.2f"
)

def build_diagram_figure():
    """
    Clean diagram:
    OT Systems → Local Nodes (multiple units for each EM) → Steel EM / Ports EM / Energy EM → Group Manager → Recommendation
    """
    fig = go.Figure()
    fig.update_layout(
        width=1000, height=320,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(color="#111111")
    )

    # Helper for drawing boxes
    def draw_box(x, y, w, h, label, color):
        fig.add_shape(
            type="rect",
            x0=x - w/2, y0=y - h/2,
            x1=x + w/2, y1=y + h/2,
            line=dict(color="#333333", width=1),
            fillcolor=color
        )
        fig.add_annotation(
            x=x, y=y, text=f"<b>{label}</b>",
            showarrow=False, font=dict(size=12, color="#111111")
        )

    # Main boxes (positions chosen for clarity)
    draw_box(0.08, 0.5, 0.16, 0.22, "OT Systems\n(SCADA / MES / TOS)", "#F3F6FA")
    draw_box(0.26, 0.28, 0.18, 0.16, "Local Nodes\n(multiple units\nfor Steel EM)", "#EAF4FF")
    draw_box(0.26, 0.50, 0.18, 0.16, "Local Nodes\n(multiple units\nfor Ports EM)", "#EAF4FF")
    draw_box(0.26, 0.72, 0.18, 0.16, "Local Nodes\n(multiple units\nfor Energy EM)", "#EAF4FF")

    draw_box(0.48, 0.28, 0.18, 0.14, "Steel EM", "#FDEEEE")
    draw_box(0.48, 0.50, 0.18, 0.14, "Ports EM", "#EEF9F0")
    draw_box(0.48, 0.72, 0.18, 0.14, "Energy EM", "#FFF7E6")

    draw_box(0.72, 0.50, 0.18, 0.20, "Group Manager", "#E9F2FF")
    draw_box(0.92, 0.50, 0.12, 0.16, "Recommendation", "#E8FFF0")

    # Helper for arrows
    def arrow(from_x, from_y, to_x, to_y, w=2):
        fig.add_annotation(
            x=to_x, y=to_y,
            ax=from_x, ay=from_y,
            xref="x", yref="y",
            showarrow=True,
            arrowhead=3, arrowsize=1.1,
            arrowwidth=w, arrowcolor="#555555"
        )

    # OT → Local Node clusters
    arrow(0.16, 0.50, 0.17, 0.28)
    arrow(0.16, 0.50, 0.17, 0.50)
    arrow(0.16, 0.50, 0.17, 0.72)

    # Local Nodes → each EM
    arrow(0.35, 0.28, 0.39, 0.28)
    arrow(0.35, 0.50, 0.39, 0.50)
    arrow(0.35, 0.72, 0.39, 0.72)

    # EMs → Group Manager
    arrow(0.57, 0.28, 0.63, 0.50)
    arrow(0.57, 0.50, 0.63, 0.50)
    arrow(0.57, 0.72, 0.63, 0.50)

    # Group Manager → Recommendation
    arrow(0.81, 0.50, 0.86, 0.50, w=2.5)

    # Caption under diagram
    fig.add_annotation(
        x=0.5, y=0.04,
        text="Data flow: OT telemetry → Local Nodes (per unit) → EMs → Group Manager → Recommendation",
        showarrow=False,
        font=dict(size=11, color="#222222")
    )

    fig.update_xaxes(visible=False, range=[0,1])
    fig.update_yaxes(visible=False, range=[0,1])
    return fig

# Run Simulation (single action: run + diagram)
if st.button("Run Simulation"):
    with st.spinner("Running cross-EM simulation and building diagram..."):
        try:
            capex_value = capex_limit if capex_limit > 0 else None
            result = run_simulation(query, capex_value)

            # Recommendation card (concise)
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant:** {result.get('recommended_plant', 'N/A')}")
            st.markdown(f"**Expected Increase:** {result.get('expected_increase_pct', 'N/A')}")
            inv = result.get('investment_usd')
            st.markdown(f"**Investment (USD):** ${inv:,}" if isinstance(inv, (int, float)) else f"**Investment (USD):** {inv}")
            st.markdown(f"**ROI:** {result.get('roi_period_months', 'N/A')} months")
            st.markdown(f"**Energy Required:** {result.get('energy_required_mw', 'N/A')} MW")

            # Action plan (clear instruction)
            action = result.get('action_plan', result.get('summary', 'No action plan available.'))
            st.info(action)

            # Unit summaries (compact)
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

            # Render the simplified diagram
            st.subheader("Data Flow Diagram")
            fig = build_diagram_figure()
            st.plotly_chart(fig, use_container_width=True)

            # Rationale for action plan
            st.subheader("Rationale for Action Plan")
            rationale_md = rationale_for_action_plan(query, result)
            st.markdown(rationale_md)

            # Neutral budget notice if applicable
            if result.get("budget_flag", False):
                st.warning("The CapEx limit filtered out all candidates; the recommendation shows the top candidate and flags the budget constraint.")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
