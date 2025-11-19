# app.py
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, rationale_for_action_plan

# INTERNAL (tooling only): local path to uploaded doc (not shown in UI)
FILE_URL = "/mnt/data/Operational Flow.docx"

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Intro / Context (short Group X description included)
st.markdown(
    """
**This is a mock prototype created to demonstrate and clarify the Original Enterprise AI concept.**  
A strategic query has been pre-filled as an example. The results shown after running the simulation are produced from assumed sample data for demonstration purposes only.

**About Group X (example):**  
Group X is a sample industrial group consisting of three companies — a ports company, a steel manufacturing company, and an energy generation company. This prototype demonstrates how their operational and enterprise data would flow from Local Nodes to Enterprise Managers and finally to the Group Manager.

Each Enterprise Manager can independently produce operational recommendations for the units and systems connected to it at the company level.  
However, Enterprise Managers cannot access the Group Manager or any cross-enterprise data.  
Only the Group Manager performs cross-enterprise reasoning by combining insights from multiple Enterprise Managers.
"""
)

# Strategic query
query = st.text_input("Strategic Query:", "How can we increase the steel production by 2 MTPA.")
capex_limit = st.number_input(
    "Optional CapEx limit (USD):",
    value=0.0,
    min_value=0.0,
    step=50000.0,
    format="%.2f"
)

def build_diagram_figure():
    """Clean data-flow diagram with straight arrows."""
    fig = go.Figure()
    fig.update_layout(
        width=1000,
        height=320,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(color="#111111")
    )

    def draw_box(x, y, w, h, label, color):
        fig.add_shape(
            type="rect",
            x0=x - w/2, y0=y - h/2,
            x1=x + w/2, y1=y + h/2,
            line=dict(color="#333333", width=1),
            fillcolor=color
        )
        fig.add_annotation(x=x, y=y, text=f"<b>{label}</b>", showarrow=False, font=dict(size=12))

    draw_box(0.12, 0.28, 0.20, 0.16, "Local Nodes\n(multiple units\nfor Steel EM)", "#EAF4FF")
    draw_box(0.12, 0.50, 0.20, 0.16, "Local Nodes\n(multiple units\nfor Ports EM)", "#EAF4FF")
    draw_box(0.12, 0.72, 0.20, 0.16, "Local Nodes\n(multiple units\nfor Energy EM)", "#EAF4FF")

    draw_box(0.40, 0.28, 0.18, 0.14, "Steel EM", "#FDEEEE")
    draw_box(0.40, 0.50, 0.18, 0.14, "Ports EM", "#EEF9F0")
    draw_box(0.40, 0.72, 0.18, 0.14, "Energy EM", "#FFF7E6")

    draw_box(0.72, 0.50, 0.18, 0.20, "Group Manager", "#E9F2FF")
    draw_box(0.92, 0.50, 0.12, 0.16, "Recommendation", "#E8FFF0")

    def straight_arrow(x0, y0, x1, y1):
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0,
            showarrow=True, arrowhead=3,
            arrowsize=1.0, arrowwidth=2, arrowcolor="#333333"
        )

    # Local → EM
    straight_arrow(0.22, 0.28, 0.31, 0.28)
    straight_arrow(0.22, 0.50, 0.31, 0.50)
    straight_arrow(0.22, 0.72, 0.31, 0.72)

    # EM → Group Manager
    straight_arrow(0.49, 0.28, 0.63, 0.50)
    straight_arrow(0.49, 0.50, 0.63, 0.50)
    straight_arrow(0.49, 0.72, 0.63, 0.50)

    # GM → Recommendation
    straight_arrow(0.81, 0.50, 0.86, 0.50)

    fig.add_annotation(
        x=0.5, y=0.04, showarrow=False,
        text="Data flow: Local Nodes (per unit) → EMs → Group Manager → Recommendation",
        font=dict(size=11)
    )

    fig.update_xaxes(visible=False, range=[0,1])
    fig.update_yaxes(visible=False, range=[0,1])
    return fig

# Run Simulation
if st.button("Run Simulation"):
    with st.spinner("Running cross-EM simulation and building diagram..."):
        try:
            capex_value = capex_limit if capex_limit > 0 else None
            result = run_simulation(query, capex_value)

            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant:** {result.get('recommended_plant')}")
            st.markdown(f"**Expected Increase:** {result.get('expected_increase_pct')}")
            inv = result.get('investment_usd')
            st.markdown(f"**Investment (USD):** ${inv:,}" if isinstance(inv, (int, float)) else f"**Investment (USD):** {inv}")
            st.markdown(f"**ROI:** {result.get('roi_period_months')} months")
            st.markdown(f"**Energy Required:** {result.get('energy_required_mw')} MW")

            st.info(result.get('action_plan', 'No action plan available.'))

            # EM summaries
            st.subheader("Enterprise Manager Summaries — Unit Details")
            cols = st.columns(3)

            # Steel EM
            with cols[0]:
                st.markdown("**Steel EM — Top Candidates**")
                for c in result["em_summaries"].get("steel_top_candidates", []):
                    st.write(
                        f"{c['plant_id']}: +{c['feasible_increase_pct']}% — "
                        f"CapEx ${c['capex_estimate_usd']:,} — Energy {c['energy_required_mw']} MW"
                    )
                st.markdown("**All Steel Units (Company B):**")
                for su in result["em_summaries"].get("steel_units_details", []):
                    st.write(
                        f"- {su['plant_id']}: capacity {su['capacity']} units, "
                        f"utilization {su['utilization']}, capex est ${su['capex_estimate_usd']:,}, "
                        f"ROI {su['roi_months']} months"
                    )

            # Ports EM
            with cols[1]:
                st.markdown("**Ports EM — Aggregate**")
                p = result["em_summaries"].get("ports_info", {})
                st.write(
                    f"Aggregate port headroom: {p.get('port_headroom_units')} units "
                    f"(avg util {p.get('current_utilization')})"
                )
                st.markdown("**All Port Units (Company A):**")
                for port in result["em_summaries"].get("port_units_details", []):
                    st.write(f"- {port['port_id']}: capacity {port['capacity']}, utilization {port['utilization']}")

            # Energy EM
            with cols[2]:
                st.markdown("**Energy EM — Aggregate**")
                e = result["em_summaries"].get("energy_info", {})
                st.write(
                    f"Aggregate headroom: {e.get('energy_headroom_mw')} MW "
                    f"(avail {e.get('energy_available_mw')} MW)"
                )
                st.markdown("**All Power Plant Units (Company C):**")
                for plant in result["em_summaries"].get("energy_units_details", []):
                    st.write(
                        f"- {plant['plant_id']}: capacity {plant['capacity_mw']} MW, "
                        f"utilization {plant['utilization']}, avail {plant['available_mw']} MW"
                    )

            # Diagram
            st.subheader("Data Flow Diagram")
            st.plotly_chart(build_diagram_figure(), use_container_width=True)

            # Rationale — FIXED (no duplicate header)
            st.subheader("Rationale for Action Plan")
            rationale_md = rationale_for_action_plan(query, result)
            rationale_md = rationale_md.replace("Rationale for Action Plan", "").strip()  # FIX
            st.markdown(rationale_md)

            if result.get("budget_flag", False):
                st.warning(
                    "The CapEx limit filtered out all candidates; "
                    "the recommendation shows the top candidate and flags the budget constraint."
                )

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
