# app.py
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation  # assumes decision_engine, enterprise_manager, group_manager are present

# Tooling note: local uploaded doc (not shown in UI). Use this path if tooling needs it.
FILE_URL = "/mnt/data/Operational Flow.docx"

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Short intro (clean)
st.markdown(
    """
**This is a mock prototype created to demonstrate the Original Enterprise AI concept.**  
A strategic query has been pre-filled for demonstration. Results come from the prototype's sample data and are for illustrative purposes only.

**About Group X (example):**  
Group X in this prototype includes **4 ports, 4 steel production plants and 3 power plants**.  
Local Nodes push per-site telemetry to Enterprise Managers (EMs). EMs evaluate options for their company. The Group Manager combines EM outputs to produce cross-enterprise recommendations.
"""
)

# Default strategic query (kept as requested)
default_query = (
    "HOW CAN WE INCREASE THE STEEL PRODUCTION BY 2 MTPA WHERE THE ADDITIONAL INVESTMENT MADE "
    "SHOULD BE RECOVERED IN LESS THAN 9 MONTHS."
)
query = st.text_input("Strategic Query:", default_query)

def build_diagram_figure():
    """Minimal, readable data-flow diagram."""
    fig = go.Figure()
    fig.update_layout(
        width=1000,
        height=320,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(color="#111111"),
    )

    def draw_box(x, y, w, h, label, color):
        fig.add_shape("rect", x0=x - w/2, y0=y - h/2, x1=x + w/2, y1=y + h/2,
                      line=dict(color="#333", width=1), fillcolor=color)
        fig.add_annotation(x=x, y=y, text=f"<b>{label}</b>", showarrow=False, font=dict(size=12, color="#111"))

    # Local nodes (left)
    draw_box(0.12, 0.28, 0.20, 0.14, "Local Nodes\n(per unit — Steel)", "#EAF4FF")
    draw_box(0.12, 0.50, 0.20, 0.14, "Local Nodes\n(per unit — Ports)", "#EAF4FF")
    draw_box(0.12, 0.72, 0.20, 0.14, "Local Nodes\n(per unit — Energy)", "#EAF4FF")

    # EMs (middle)
    draw_box(0.40, 0.28, 0.18, 0.12, "Steel EM", "#FDEEEE")
    draw_box(0.40, 0.50, 0.18, 0.12, "Ports EM", "#EEF9F0")
    draw_box(0.40, 0.72, 0.18, 0.12, "Energy EM", "#FFF7E6")

    # Group manager & Recommendation (right)
    draw_box(0.72, 0.50, 0.18, 0.20, "Group Manager", "#E9F2FF")
    draw_box(0.92, 0.50, 0.12, 0.14, "Recommendation", "#E8FFF0")

    # Straight arrows (clear)
    def arrow(ax, ay, x, y, width=2, head=3):
        fig.add_annotation(x=x, y=y, ax=ax, ay=ay, showarrow=True,
                           arrowhead=head, arrowwidth=width, arrowcolor="#222")

    # Local -> EM
    arrow(0.22, 0.28, 0.31, 0.28)
    arrow(0.22, 0.50, 0.31, 0.50)
    arrow(0.22, 0.72, 0.31, 0.72)

    # EM -> GM
    arrow(0.49, 0.28, 0.63, 0.50)
    arrow(0.49, 0.50, 0.63, 0.50)
    arrow(0.49, 0.72, 0.63, 0.50)

    # GM -> Recommendation
    arrow(0.81, 0.50, 0.86, 0.50, width=3, head=4)

    fig.add_annotation(x=0.5, y=0.02, text="Data flow: Local Nodes → EMs → Group Manager → Recommendation",
                       showarrow=False, font=dict(size=11, color="#222"))
    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1])
    return fig

# Run Simulation (single action)
if st.button("Run Simulation"):
    with st.spinner("Running cross-EM simulation..."):
        try:
            result = run_simulation(query)

            # --- Recommendation summary ---
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant(s):** {result.get('recommended_plant', 'N/A')}")
            st.markdown(f"**Expected Increase:** {result.get('expected_increase_tpa', 'N/A'):,} tpa")
            inv = result.get('investment_usd')
            if isinstance(inv, (int, float)):
                st.markdown(f"**Investment (USD):** ${inv:,.0f}")
            else:
                st.markdown(f"**Investment (USD):** {inv}")
            st.markdown(f"**Combined ROI:** {result.get('roi_months', 'N/A')} months")
            st.markdown(f"**Energy Required:** {result.get('energy_required_mw', 'N/A')} MW")

            # Action plan as clear instruction
            st.success(result.get('action_plan', result.get('summary', 'No action plan available.')))

            # --- Enterprise Manager Summaries (clean & concise) ---
            st.subheader("Enterprise Manager Summaries — Unit Details")
            cols = st.columns(3)

            # Steel: concise lines (Plant | Increase | CapEx | ROI)
            with cols[0]:
                st.markdown("**Steel EM — Top Candidates**")
                top_candidates = result["em_summaries"].get("steel_top_candidates", [])
                if top_candidates:
                    for c in top_candidates:
                        plant = c.get('plant_id', 'N/A')
                        inc = c.get('feasible_increase_tpa', 0)
                        cap = c.get('capex_estimate_usd', 'N/A')
                        roi = c.get('roi_months', 'N/A')
                        # keep it short and readable
                        cap_str = f"${cap:,.0f}" if isinstance(cap, (int, float)) else cap
                        st.write(f"- **{plant}** — Increase: {inc:,} tpa | CapEx: {cap_str} | ROI: {roi} months")
                else:
                    st.write("No steel candidates available.")

                st.markdown("**All Steel Units (Company B)**")
                for su in result["em_summaries"].get("steel_units_details", []):
                    pid = su.get('plant_id', 'N/A')
                    cap_tpa = su.get('capacity_tpa', 'N/A')
                    util = su.get('utilization', 'N/A')
                    st.write(f"- {pid} — Capacity: {cap_tpa:,} tpa | Utilization: {util:.2f}" if isinstance(util, (int, float)) else f"- {pid} — Capacity: {cap_tpa:,} tpa")

            # Ports: show total headroom in Mtpa and list ports succinctly
            with cols[1]:
                st.markdown("**Ports EM — Aggregate**")
                ports_info = result["em_summaries"].get("ports_info", {})
                port_headroom_tpa = ports_info.get("port_headroom_tpa")
                if port_headroom_tpa is not None:
                    st.write(f"Aggregate port headroom: {port_headroom_tpa:,} tpa ({port_headroom_tpa / 1_000_000:.2f} Mtpa)")
                else:
                    st.write("Aggregate port headroom: N/A")

                st.markdown("**All Port Units (Company A)**")
                for p in result["em_summaries"].get("port_units_details", []):
                    pid = p.get('port_id', 'N/A')
                    cap_mt = p.get('annual_capacity_mt', 'N/A')
                    thr_mt = p.get('current_throughput_mt', 'N/A')
                    st.write(f"- {pid} — Capacity: {cap_mt} Mtpa | Throughput: {thr_mt} Mtpa")

            # Energy: show total available and per-plant available
            with cols[2]:
                st.markdown("**Energy EM — Aggregate**")
                e = result["em_summaries"].get("energy_info", {})
                energy_headroom = e.get("energy_headroom_mw", e.get("energy_available_mw"))
                if energy_headroom is not None:
                    st.write(f"Aggregate available energy: {energy_headroom} MW")
                else:
                    st.write("Aggregate available energy: N/A")

                st.markdown("**All Power Plant Units (Company C)**")
                for plant in result["em_summaries"].get("energy_units_details", []):
                    pid = plant.get('plant_id', 'N/A')
                    avail = plant.get('available_mw', plant.get('capacity_mw', 'N/A'))
                    st.write(f"- {pid} — Available: {avail} MW")

            # Diagram
            st.subheader("Data Flow Diagram")
            st.plotly_chart(build_diagram_figure(), use_container_width=True)

            # Rationale: friendly explanation (no raw JSON)
            st.subheader("Rationale for Action Plan")
            st.markdown(result.get("summary", ""))

            justification = result.get("justification", {})
            if justification:
                # map breach codes to readable text
                breach_map = {
                    "insufficient_single_plant_increase": "No single plant could deliver the full required increase; combined plants were considered.",
                    "roi_exceeds_limit": "One or more individual candidates had ROI above the required recovery period.",
                    "energy_shortfall": "Energy availability is a constraint for the uplift.",
                    "port_shortfall": "Port handling capacity is a constraint for shipments."
                }

                breaches = justification.get("breaches", [])
                mitigations = justification.get("mitigations", [])

                # numeric context
                ctx = []
                if justification.get("energy_headroom_mw") is not None:
                    ctx.append(f"- Energy headroom: {justification.get('energy_headroom_mw')} MW")
                if justification.get("port_headroom_tpa") is not None:
                    ph = justification.get("port_headroom_tpa")
                    ctx.append(f"- Port headroom: {ph:,} tpa ({ph / 1_000_000:.2f} Mtpa)")
                if result.get("expected_increase_tpa") is not None:
                    ctx.append(f"- Expected increase (tpa): {result.get('expected_increase_tpa'):,} tpa")

                if ctx:
                    st.markdown("**Context:**")
                    for line in ctx:
                        st.markdown(line)

                if breaches:
                    st.markdown("**Identified Constraints / Breaches:**")
                    for b in breaches:
                        st.markdown(f"- {breach_map.get(b, b)}")

                if mitigations:
                    st.markdown("**Suggested Mitigations / Next Steps:**")
                    for m in mitigations:
                        st.markdown(f"- {m}")

            # budget flag note
            if result.get("budget_flag", False):
                st.warning("Candidate selection was influenced by budget or ROI constraints. See Rationale for details.")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
