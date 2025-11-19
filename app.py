# app.py (final - runs simulation + diagram automatically)
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, rationale_for_action_plan

# INTERNAL: local path to uploaded doc (kept for tooling only; NOT shown in UI)
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

# Updated default strategic query (exact wording requested)
query = st.text_input("Strategic Query:", "How can we increase the steel production by 2 MTPA.")
capex_limit = st.number_input(
    "Optional CapEx limit (USD):",
    value=0.0,
    min_value=0.0,
    step=50000.0,
    format="%.2f"
)

def build_diagram_figure(steel_local_count=4, ports_local_count=4, energy_local_count=3):
    """
    Build a compact, readable diagram showing:
      - OT Systems -> multiple Local Nodes per EM -> each EM -> Group Manager -> Recommendation
    Local node counts are parameterized (default: 4 steel, 4 ports, 3 energy).
    """
    fig = go.Figure()
    # use normalized coordinates 0..1 for layout; we'll map fonts/colors for readability
    # base canvas
    fig.update_layout(width=1000, height=360, plot_bgcolor="white",
                      margin=dict(l=10, r=10, t=10, b=10), font=dict(color="#111111"))

    # main boxes positions
    # OT Systems (left)
    ot = {"x": 0.06, "y": 0.5, "w": 0.16, "h": 0.20, "label": "OT Systems\n(SCADA / MES / TOS)", "color": "#F3F6FA"}

    # Local nodes clusters for each EM (as small repeated boxes visually)
    ln_x = 0.22
    steel_y = 0.28
    ports_y = 0.5
    energy_y = 0.72
    ln_w = 0.12
    ln_h = 0.08

    em_x = 0.44
    em_w = 0.16
    em_h = 0.14

    gm_x = 0.72
    gm = {"x": gm_x, "y": 0.5, "w": 0.18, "h": 0.22, "label": "Group Manager", "color": "#E9F2FF"}
    rec = {"x": 0.92, "y": 0.5, "w": 0.12, "h": 0.18, "label": "Recommendation", "color": "#E8FFF0"}

    # draw OT box
    def rect_add(x, y, w, h, label, color):
        x0, x1 = x - w/2, x + w/2
        y0, y1 = y - h/2, y + h/2
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                      xref="x", yref="y", line=dict(color="#333333", width=1),
                      fillcolor=color)
        fig.add_annotation(x=x, y=y, text=f"<b>{label}</b>", showarrow=False,
                           font=dict(size=12, color="#111111"))

    rect_add(ot["x"], ot["y"], ot["w"], ot["h"], ot["label"], ot["color"])

    # helper to place multiple local node boxes (small) per EM
    def add_local_nodes(cluster_x, cluster_y, count, title):
        # vertical spacing
        gap = 0.02
        total_h = (count * ln_h) + ((count-1) * gap)
        start_y = cluster_y - total_h/2 + ln_h/2
        y_positions = [start_y + i*(ln_h+gap) for i in range(count)]
        node_ids = []
        for i, y in enumerate(y_positions):
            label = f"Local Node\n{title}-{i+1}"
            rect_add(cluster_x, y, ln_w, ln_h, label, "#EEF7FF")
            node_ids.append((cluster_x + ln_w/2, y))  # right center for arrow end
        return node_ids

    # add steel local nodes
    steel_locals = add_local_nodes(ln_x, steel_y, steel_local_count, "Steel")
    ports_locals = add_local_nodes(ln_x, ports_y, ports_local_count, "Port")
    energy_locals = add_local_nodes(ln_x, energy_y, energy_local_count, "Energy")

    # add EM boxes
    rect_add(em_x, steel_y, em_w, em_h, "Steel EM", "#FDEEEE")
    rect_add(em_x, ports_y, em_w, em_h, "Ports EM", "#EEF9F0")
    rect_add(em_x, energy_y, em_w, em_h, "Energy EM", "#FFF7E6")

    # add Group Manager and Recommendation
    rect_add(gm["x"], gm["y"], gm["w"], gm["h"], gm["label"], gm["color"])
    rect_add(rec["x"], rec["y"], rec["w"], rec["h"], rec["label"], rec["color"])

    # draw arrows (OT -> each local node cluster center)
    # single arrow from OT right-center to each cluster left side to avoid clutter
    ot_right_x = ot["x"] + ot["w"]/2
    def add_arrow(ax, ay, bx, by, width=2):
        fig.add_annotation(x=bx, y=by, ax=ax, ay=ay, xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=1.0, arrowwidth=width, arrowcolor="#6b6b6b")

    # cluster centroids
    def cluster_centroid(locals):
        xs = [p[0] for p in locals]
        ys = [p[1] for p in locals]
        return (min(xs)-0.06, sum(ys)/len(ys))  # a bit left of first local node

    sx, sy = cluster_centroid(steel_locals)
    px, py = cluster_centroid(ports_locals)
    ex, ey = cluster_centroid(energy_locals)

    add_arrow(ot_right_x, ot["y"], sx, sy)
    add_arrow(sx + 0.12, sy, em_x - em_w/2, steel_y)   # steel locals -> steel EM
    add_arrow(px + 0.12, py, em_x - em_w/2, ports_y)   # ports locals -> ports EM
    add_arrow(ex + 0.12, ey, em_x - em_w/2, energy_y)  # energy locals -> energy EM

    # EMs -> Group Manager (one arrow each)
    em_right_x = em_x + em_w/2
    add_arrow(em_right_x, steel_y, gm["x"] - gm["w"]/2, gm["y"])
    add_arrow(em_right_x, ports_y, gm["x"] - gm["w"]/2, gm["y"])
    add_arrow(em_right_x, energy_y, gm["x"] - gm["w"]/2, gm["y"])

    # Group Manager -> Recommendation
    gm_right = gm["x"] + gm["w"]/2
    rec_left = rec["x"] - rec["w"]/2
    add_arrow(gm_right, gm["y"], rec_left, rec["y"], width=2.5)

    # small caption under diagram
    fig.add_annotation(x=0.5, y=0.03,
                       text="Data flow: OT telemetry → Local Nodes (per unit) → Enterprise Managers → Group Manager → Recommendation",
                       showarrow=False, font=dict(size=11, color="#222222"))

    # hide axes
    fig.update_xaxes(visible=False, range=[0,1])
    fig.update_yaxes(visible=False, range=[0,1])

    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
    return fig

# Run Simulation (single action: run + diagram)
if st.button("Run Simulation"):
    with st.spinner("Running cross-EM simulation and building diagram..."):
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

            # Show action plan clearly
            action = result.get('action_plan', result.get('summary', 'No action plan available.'))
            st.info(action)

            # Unit summaries
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

            # Render the diagram automatically with counts from mock_data length
            steel_count = len(result["em_summaries"].get("steel_units_details", [])) or 4
            ports_count = len(result["em_summaries"].get("port_units_details", [])) or 4
            energy_count = len(result["em_summaries"].get("energy_units_details", [])) or 3
            fig = build_diagram_figure(steel_local_count=steel_count,
                                       ports_local_count=ports_count,
                                       energy_local_count=energy_count)
            st.subheader("Data Flow Diagram")
            st.plotly_chart(fig, use_container_width=True)

            # Rationale
            st.subheader("Rationale for Action Plan")
            rationale_md = rationale_for_action_plan(query, result)
            st.markdown(rationale_md)

            # budget info (neutral)
            if result.get("budget_flag", False):
                st.warning("The CapEx limit filtered out all candidates; the recommendation shows the top candidate and flags the budget constraint.")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
