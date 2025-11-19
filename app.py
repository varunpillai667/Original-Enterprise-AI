# app.py (diagrammatic version)
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, rationale_for_action_plan

# INTERNAL (not shown in UI): local path to uploaded doc (kept only for tooling)
FILE_URL = "/mnt/data/Operational Flow.docx"

st.set_page_config(page_title="Original Enterprise AI – Group Manager Cross-EM Demo", layout="wide")
st.title("🧠 Group Manager Cross-EM Demo — Concept Prototype (Diagram)")

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

def build_diagram_figure():
    """
    Build a simple, minimal, readable diagram using Plotly shapes and annotations.
    The diagram is horizontal: OT Systems -> Local Node -> (Steel EM, Ports EM, Energy EM)
    -> Group Manager -> Recommendation.
    """
    fig = go.Figure()

    # Canvas size
    width = 1000
    height = 320

    # Node positions (x0,x1,y0,y1) in relative coordinates [0..1] scaled to width/height
    nodes = {
        "OT Systems":    {"x": 0.05, "y": 0.5, "w": 0.18, "h": 0.22, "color": "#F0F4F8"},
        "Local Node":    {"x": 0.25, "y": 0.5, "w": 0.14, "h": 0.18, "color": "#DCEEFF"},
        "Steel EM":      {"x": 0.46, "y": 0.28, "w": 0.14, "h": 0.14, "color": "#F6EAEA"},
        "Ports EM":      {"x": 0.46, "y": 0.5,  "w": 0.14, "h": 0.14, "color": "#EAF8F0"},
        "Energy EM":     {"x": 0.46, "y": 0.72, "w": 0.14, "h": 0.14, "color": "#FFF6E5"},
        "Group Manager": {"x": 0.72, "y": 0.5,  "w": 0.18, "h": 0.22, "color": "#E8F0FA"},
        "Recommendation":{"x": 0.92, "y": 0.5,  "w": 0.12, "h": 0.18, "color": "#E8FFF0"},
    }

    # draw rectangles for nodes
    for label, n in nodes.items():
        x0 = n["x"] - n["w"]/2
        x1 = n["x"] + n["w"]/2
        y0 = n["y"] - n["h"]/2
        y1 = n["y"] + n["h"]/2
        fig.add_shape(
            type="rect",
            x0=x0, y0=y0, x1=x1, y1=y1,
            xref="x", yref="y",
            line=dict(color="#3a3a3a", width=1),
            fillcolor=n["color"],
            layer="below",
            opacity=1.0,
            )
        # label centered
        fig.add_annotation(x=n["x"], y=n["y"],
                           text=f"<b>{label}</b>",
                           showarrow=False,
                           font=dict(size=13, color="#111111"),
                           xanchor="center",
                           yanchor="middle")

    # helper to compute connection points
    def right_center(n):
        return (n["x"] + n["w"]/2, n["y"])
    def left_center(n):
        return (n["x"] - n["w"]/2, n["y"])
    def top_center(n):
        return (n["x"], n["y"] - n["h"]/2)
    def bottom_center(n):
        return (n["x"], n["y"] + n["h"]/2)

    # links: draw arrows as shapes (lines with arrowhead style)
    arrow_color = "#6b6b6b"
    arrow_width = 2

    # OT -> Local Node
    ox, oy = right_center(nodes["OT Systems"])
    lx, ly = left_center(nodes["Local Node"])
    fig.add_annotation(x=lx-0.01, y=ly,
                       ax=ox+0.01, ay=oy,
                       xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowsize=1.2, arrowwidth=arrow_width,
                       arrowcolor=arrow_color)

    # Local Node -> each EM (slightly curved)
    lnx, lny = right_center(nodes["Local Node"])
    for em in ["Steel EM", "Ports EM", "Energy EM"]:
        tx, ty = left_center(nodes[em])
        fig.add_annotation(x=tx-0.01, y=ty,
                           ax=lnx+0.02, ay=lny,
                           xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=1.0, arrowwidth=arrow_width,
                           arrowcolor=arrow_color)

    # Each EM -> Group Manager
    gxn, gyn = left_center(nodes["Group Manager"])
    for em in ["Steel EM", "Ports EM", "Energy EM"]:
        sx, sy = right_center(nodes[em])
        fig.add_annotation(x=gxn+0.01, y=gyn,
                           ax=sx-0.01, ay=sy,
                           xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=1.0, arrowwidth=arrow_width,
                           arrowcolor=arrow_color)

    # Group Manager -> Recommendation
    gx, gy = right_center(nodes["Group Manager"])
    rx, ry = left_center(nodes["Recommendation"])
    fig.add_annotation(x=rx-0.01, y=ry,
                       ax=gx+0.01, ay=gy,
                       xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowsize=1.2, arrowwidth=arrow_width+0.5,
                       arrowcolor=arrow_color)

    # Add small helper text under diagram (single-line)
    fig.add_annotation(x=0.5, y=0.05, text="Data flow: OT telemetry → Local Node (preprocess) → Enterprise Managers → Group Manager → Recommendation",
                       showarrow=False, font=dict(size=11, color="#222222"), xref="x", yref="y")

    # layout and axes
    fig.update_xaxes(visible=False, range=[0,1])
    fig.update_yaxes(visible=False, range=[0,1])

    fig.update_layout(
        width=960, height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white",
    )

    return fig

if st.button("Preview Diagram Only"):
    # quick preview for diagram design
    fig = build_diagram_figure()
    st.plotly_chart(fig, use_container_width=True)

if st.button("Run Simulation & Diagram"):
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

            # Show action plan
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

            # Render the diagram
            st.subheader("Data Flow Diagram")
            fig = build_diagram_figure()
            st.plotly_chart(fig, use_container_width=True)

            # Rationale
            st.subheader("Rationale for Action Plan")
            rationale_md = rationale_for_action_plan(query, result)
            st.markdown(rationale_md)

            # Budget note (neutral)
            if result.get("budget_flag", False):
                st.warning("The CapEx limit filtered out all candidates; the recommendation shows the top candidate and flags the budget constraint.")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
