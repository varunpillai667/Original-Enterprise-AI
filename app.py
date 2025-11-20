# app.py
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

st.markdown("""
**This is a mock prototype created to demonstrate the Original Enterprise AI concept.**  
Group X: 4 ports, 4 steel plants, 3 power plants. The prototype uses sample data only.
""")

default_query = "HOW CAN WE INCREASE THE STEEL PRODUCTION BY 2 MTPA WHERE THE ADDITIONAL INVESTMENT MADE SHOULD BE RECOVERED WITHIN 3 YEARS."
query = st.text_input("Strategic Query:", default_query)

def build_diagram_figure():
    fig = go.Figure()
    fig.update_layout(width=900, height=300, plot_bgcolor="white", margin=dict(l=10,r=10,t=10,b=10))
    def draw_box(x,y,w,h,label,color):
        fig.add_shape(type="rect", x0=x-w/2, y0=y-h/2, x1=x+w/2, y1=y+h/2, line=dict(color="#333"), fillcolor=color)
        fig.add_annotation(x=x,y=y,text=f"<b>{label}</b>", showarrow=False)
    draw_box(0.12,0.5,0.2,0.18,"Local Nodes\n(per unit)","#EAF4FF")
    draw_box(0.4,0.5,0.18,0.18,"Enterprise Managers\n(Steel/Ports/Energy)","#FDEEEE")
    draw_box(0.72,0.5,0.18,0.22,"Group Manager","#E9F2FF")
    draw_box(0.92,0.5,0.12,0.12,"Recommendation","#E8FFF0")
    def arrow(ax,ay,x,y): fig.add_annotation(x=x,y=y,ax=ax,ay=ay,showarrow=True,arrowcolor="#222")
    arrow(0.22,0.5,0.31,0.5); arrow(0.49,0.5,0.63,0.5); arrow(0.81,0.5,0.86,0.5)
    fig.update_xaxes(visible=False, range=[0,1]); fig.update_yaxes(visible=False, range=[0,1])
    return fig

if st.button("Run Simulation"):
    with st.spinner("Running simulation..."):
        try:
            result = run_simulation(query)
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant(s):** {result.get('recommended_plant')}")
            expected = result.get("expected_increase_tpa")
            st.markdown(f"**Expected Increase:** {expected:,} tpa" if isinstance(expected,int) else f"**Expected Increase:** {expected}")
            inv = result.get("investment_usd")
            st.markdown(f"**Investment (USD):** ${inv:,.0f}" if isinstance(inv,(int,float)) else f"**Investment (USD):** {inv}")
            st.markdown(f"**Combined ROI:** {result.get('roi_months')} months")
            st.markdown(f"**Energy Required:** {result.get('energy_required_mw')} MW")
            st.success(result.get("action_plan"))

            # allocations (clear)
            allocations = result.get("allocations")
            if allocations:
                st.markdown("**Allocation per plant (operational | expansion | capex):**")
                for a in allocations:
                    pid = a.get("plant_id")
                    op = a.get("allocated_operational_tpa",0)
                    exp = a.get("allocated_expansion_tpa",0)
                    capexp = a.get("expansion_capex",0)
                    opcap = a.get("op_capex_used",0)
                    st.write(f"- {pid}: operational {op:,} tpa | expansion {exp:,} tpa | op capex ${opcap:,} | expansion capex ${capexp:,}")

            # concise EM summaries
            st.subheader("Enterprise Manager Summaries — Unit Details (concise)")
            cols = st.columns(3)
            with cols[0]:
                st.markdown("**Steel EM — Top Candidates**")
                for c in result["em_summaries"].get("steel_top_candidates", []):
                    st.write(f"- {c['plant_id']} — Increase: {c['feasible_increase_tpa']:,} tpa | OpCapEx: ${c['op_capex_estimate_usd']:,} | ROI: {c['roi_months']} m")
            with cols[1]:
                st.markdown("**Ports EM — Aggregate**")
                pinfo = result["em_summaries"].get("ports_info",{})
                ph = pinfo.get("port_headroom_tpa")
                st.write(f"- Headroom: {ph:,} tpa ({ph/1_000_000:.2f} Mtpa)" if ph is not None else "- Headroom: N/A")
            with cols[2]:
                st.markdown("**Energy EM — Aggregate**")
                einfo = result["em_summaries"].get("energy_info",{})
                eh = einfo.get("energy_headroom_mw")
                st.write(f"- Available: {eh} MW" if eh is not None else "- Available: N/A")

            st.subheader("Data Flow Diagram")
            st.plotly_chart(build_diagram_figure(), use_container_width=True)

            # Rationale: explicit and human-friendly
            st.subheader("Rationale for Action Plan")
            st.markdown(result.get("summary",""))
            why = result.get("why_chosen", [])
            if why:
                st.markdown("**Why this solution was chosen:**")
                for line in why:
                    st.markdown(f"- {line}")

            # numeric context
            just = result.get("justification",{})
            if just:
                st.markdown("**Numeric context / checks:**")
                if just.get("energy_headroom_mw") is not None:
                    st.markdown(f"- Energy headroom: {just.get('energy_headroom_mw')} MW")
                if just.get("port_headroom_tpa") is not None:
                    ph = just.get("port_headroom_tpa")
                    st.markdown(f"- Port headroom: {ph:,} tpa ({ph/1_000_000:.2f} Mtpa)")

        except Exception as e:
            st.error(f"Simulation Error: {e}")
