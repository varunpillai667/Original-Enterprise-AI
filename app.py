# app.py
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation  # decision_engine returns result dict including summary, action_plan, justification, etc.

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
Group X is a sample industrial group consisting of: **4 ports, 4 steel production plants, and 3 power plants**.  
This prototype demonstrates how their operational and enterprise data would flow from Local Nodes to Enterprise Managers and finally to the Group Manager.

Each Enterprise Manager can independently produce operational recommendations for the units and systems connected to it at the company level.  
Enterprise Managers cannot access the Group Manager or any cross-enterprise data. Only the Group Manager performs cross-enterprise reasoning by combining insights from multiple Enterprise Managers.
"""
)

# Default strategic query
default_query = (
    "HOW CAN WE INCREASE THE STEEL PRODUCTION BY 2 MTPA WHERE THE ADDITIONAL INVESTMENT MADE "
    "SHOULD BE RECOVERED IN LESS THAN 9 MONTHS."
)
query = st.text_input("Strategic Query:", default_query)

def build_diagram_figure():
    """Clean data-flow diagram with straight, visible arrows."""
    fig = go.Figure()
    fig.update_layout(
        width=1000,
        height=340,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(color="#111111")
    )

    def draw_box(x, y, w, h, label, color):
        fig.add_shape(
            type="rect",
            x0=x - w/2, y0=y - h/2,
            x1=x + w/2, y1=y + h/2,
            xref="x", yref="y",
            line=dict(color="#333333", width=1),
            fillcolor=color,
            layer="below",
        )
        fig.add_annotation(
            x=x, y=y, text=f"<b>{label}</b>",
            showarrow=False, font=dict(size=12, color="#111111"),
            xref="x", yref="y"
        )

    # Left: Local Nodes clusters (one per EM)
    draw_box(0.12, 0.28, 0.20, 0.16, "Local Nodes\n(multiple units\nfor Steel EM)", "#EAF4FF")
    draw_box(0.12, 0.50, 0.20, 0.16, "Local Nodes\n(multiple units\nfor Ports EM)", "#EAF4FF")
    draw_box(0.12, 0.72, 0.20, 0.16, "Local Nodes\n(multiple units\nfor Energy EM)", "#EAF4FF")

    # Middle: EMs
    draw_box(0.40, 0.28, 0.18, 0.14, "Steel EM", "#FDEEEE")
    draw_box(0.40, 0.50, 0.18, 0.14, "Ports EM", "#EEF9F0")
    draw_box(0.40, 0.72, 0.18, 0.14, "Energy EM", "#FFF7E6")

    # Right: Group Manager and Recommendation
    draw_box(0.72, 0.50, 0.18, 0.20, "Group Manager", "#E9F2FF")
    draw_box(0.92, 0.50, 0.12, 0.16, "Recommendation", "#E8FFF0")

    # Highly visible straight arrows (classic)
    arrow_color = "#111111"
    arrow_width = 3
    arrow_head = 4

    def straight_arrow(x0, y0, x1, y1, width=arrow_width, color=arrow_color, head=arrow_head):
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True,
            arrowhead=head,
            arrowsize=1.0,
            arrowwidth=width,
            arrowcolor=color
        )

    # Local Nodes -> EMs (horizontal)
    straight_arrow(0.22, 0.28, 0.31, 0.28)
    straight_arrow(0.22, 0.50, 0.31, 0.50)
    straight_arrow(0.22, 0.72, 0.31, 0.72)

    # EMs -> Group Manager
    straight_arrow(0.49, 0.28, 0.63, 0.50)
    straight_arrow(0.49, 0.50, 0.63, 0.50)
    straight_arrow(0.49, 0.72, 0.63, 0.50)

    # Group Manager -> Recommendation
    straight_arrow(0.81, 0.50, 0.86, 0.50, width=4, head=5)

    # Caption under diagram
    fig.add_annotation(
        x=0.5, y=0.03,
        text="Data flow: Local Nodes (per unit) → EMs → Group Manager → Recommendation",
        showarrow=False, font=dict(size=11, color="#222222"),
        xref="x", yref="y"
    )

    fig.update_xaxes(visible=False, range=[0,1])
    fig.update_yaxes(visible=False, range=[0,1])
    return fig

# Run Simulation (single action: run + diagram)
if st.button("Run Simulation"):
    with st.spinner("Running cross-EM simulation and building diagram..."):
        try:
            # run simulation (decision_engine will parse query constraints and return combined ROI/selection data)
            result = run_simulation(query)

            # Recommendation card (concise)
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant(s):** {result.get('recommended_plant', 'N/A')}")
            st.markdown(f"**Expected Increase:** {result.get('expected_increase_tpa', 'N/A')} tpa")
            inv = result.get('investment_usd')
            st.markdown(f"**Investment (USD):** ${inv:,}" if isinstance(inv, (int, float)) else f"**Investment (USD):** {inv}")
            st.markdown(f"**Combined ROI:** {result.get('roi_months', 'N/A')} months")
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
                        f"{c.get('plant_id','N/A')}: +{c.get('feasible_increase_tpa','N/A')} tpa — "
                        f"CapEx ${c.get('capex_estimate_usd','N/A'):,} — Energy {c.get('energy_required_mw','N/A')} MW — "
                        f"ROI {c.get('roi_months','N/A')}m — Monthly incremental income ${c.get('incr_monthly_income','N/A'):,}"
                    )
                st.markdown("**All Steel Units (Company B):**")
                for su in result["em_summaries"].get("steel_units_details", []):
                    st.write(
                        f"- {su.get('plant_id','N/A')}: capacity {su.get('capacity_tpa','N/A')} tpa, "
                        f"utilization {su.get('utilization','N/A')}, capex est ${su.get('capex_estimate_usd','N/A'):,}, "
                        f"ROI {su.get('roi_months','N/A')} months"
                    )

            with cols[1]:
                st.markdown("**Ports EM — Aggregate**")
                p = result["em_summaries"].get("ports_info", {})
                port_headroom_tpa = p.get('port_headroom_tpa')
                if port_headroom_tpa is not None:
                    st.write(f"Aggregate port headroom: {port_headroom_tpa:,} tpa ({port_headroom_tpa/1_000_000:.2f} Mtpa)")
                else:
                    st.write("Aggregate port headroom: N/A")
                st.markdown("**All Port Units (Company A):**")
                for port in result["em_summaries"].get("port_units_details", []):
                    st.write(f"- {port.get('port_id','N/A')}: annual capacity {port.get('annual_capacity_mt','N/A')} Mtpa, throughput {port.get('current_throughput_mt','N/A')} Mtpa")

            with cols[2]:
                st.markdown("**Energy EM — Aggregate**")
                e = result["em_summaries"].get("energy_info", {})
                st.write(
                    f"Aggregate headroom: {e.get('energy_headroom_mw','N/A')} MW (available {e.get('energy_available_mw','N/A')} MW)"
                )
                st.markdown("**All Power Plant Units (Company C):**")
                for plant in result["em_summaries"].get("energy_units_details", []):
                    st.write(
                        f"- {plant.get('plant_id','N/A')}: capacity {plant.get('capacity_mw','N/A')} MW, available {plant.get('available_mw','N/A')} MW"
                    )

            # Render the simplified diagram
            st.subheader("Data Flow Diagram")
            st.plotly_chart(build_diagram_figure(), use_container_width=True)

            # Rationale for Action Plan (single header; friendly justification rendering)
            st.subheader("Rationale for Action Plan")
            st.markdown(result.get("summary", ""))

            # Friendly justification
            justification = result.get("justification", {})
            if justification:
                breach_map = {
                    "insufficient_single_plant_increase": "No single plant could deliver the full required increase — a combined plan is needed.",
                    "roi_exceeds_limit": "Estimated ROI for candidate(s) individually exceeded the limit.",
                    "energy_shortfall": "Available energy headroom is insufficient for the uplift requested.",
                    "port_shortfall": "Port headroom/capacity is insufficient for the additional shipments required."
                }

                breaches = justification.get("breaches", [])
                mitigations = justification.get("mitigations", [])

                # numeric context
                ctx_lines = []
                if "energy_headroom_mw" in justification:
                    ctx_lines.append(f"- Energy headroom: {justification.get('energy_headroom_mw')} MW")
                if "port_headroom_tpa" in justification:
                    ctx_lines.append(f"- Port headroom: {justification.get('port_headroom_tpa'):,} tpa ({justification.get('port_headroom_tpa')/1_000_000:.2f} Mtpa)")
                if "expected_increase_tpa" in result:
                    ctx_lines.append(f"- Expected increase (tpa): {result.get('expected_increase_tpa')} tpa")

                if ctx_lines:
                    st.markdown("**Context:**")
                    for line in ctx_lines:
                        st.markdown(line)

                if breaches:
                    st.markdown("**Breaches / Constraints Identified:**")
                    for b in breaches:
                        st.markdown(f"- {breach_map.get(b, b)}")

                if mitigations:
                    st.markdown("**Suggested Mitigations / Next Steps:**")
                    for m in mitigations:
                        st.markdown(f"- {m}")

            if result.get("budget_flag", False):
                st.warning("Candidate selection was influenced by budget or ROI constraints. See Rationale for details.")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
