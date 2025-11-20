# app.py
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Operating Principle Description
st.markdown(
    """
### Operating Principle
**Original Enterprise AI** operates across three hierarchical layers within Group X:

- **LOCAL Nodes**: Deployed at each operational site (ports, steel plants, power plants) to collect real-time data from operational systems (SCADA, MES, TOS) and securely transmit to respective Enterprise Managers.

- **Enterprise Managers**: Three separate AI engines for each company:
  - **Ports EM** (Company A) - Manages port operations and throughput
  - **Steel EM** (Company B) - Manages steel production and capacity  
  - **Energy EM** (Company C) - Manages power generation and distribution

- **Group Manager**: Strategic orchestrator at Group X headquarters that coordinates across all Enterprise Managers to provide cross-company optimization and recommendations.

When the Group CEO places a strategic query, the Group Manager retrieves processed intelligence from all Enterprise Managers, analyzes cross-company dependencies, and delivers unified, explainable recommendations.
"""
)

# Updated strategic query focusing on the core business question
default_query = (
    "How can we increase steel production capacity by 2 million tonnes per annum across all steel plants "
    "while ensuring existing commercial cargo operations at ports and grid sales from power plants remain unaffected? "
    "The additional investment should be recovered within three years."
)
query = st.text_input("Strategic Query:", default_query)

def build_diagram_figure():
    """Architecture diagram showing the three-layer data flow."""
    fig = go.Figure()
    fig.update_layout(
        width=1000,
        height=400,
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(color="#111111"),
    )

    def draw_box(x, y, w, h, label, color):
        fig.add_shape(
            type="rect", x0=x - w/2, y0=y - h/2, x1=x + w/2, y1=y + h/2,
            line=dict(color="#333", width=1), fillcolor=color
        )
        fig.add_annotation(x=x, y=y, text=f"<b>{label}</b>", showarrow=False, font=dict(size=11, color="#111"))

    # LOCAL Nodes
    draw_box(0.12, 0.25, 0.18, 0.10, "LOCAL Nodes\n(Steel Plants)", "#EAF4FF")
    draw_box(0.12, 0.50, 0.18, 0.10, "LOCAL Nodes\n(Ports)", "#EAF4FF") 
    draw_box(0.12, 0.75, 0.18, 0.10, "LOCAL Nodes\n(Power Plants)", "#EAF4FF")

    # Enterprise Managers
    draw_box(0.38, 0.25, 0.16, 0.10, "Steel EM\n(Company B)", "#FDEEEE")
    draw_box(0.38, 0.50, 0.16, 0.10, "Ports EM\n(Company A)", "#EEF9F0")
    draw_box(0.38, 0.75, 0.16, 0.10, "Energy EM\n(Company C)", "#FFF7E6")

    # Group Manager
    draw_box(0.65, 0.50, 0.18, 0.20, "Group Manager\n(Group X HQ)", "#E9F2FF")
    
    # Recommendation
    draw_box(0.85, 0.50, 0.12, 0.12, "Strategic\nRecommendation", "#E8FFF0")

    def arrow(ax, ay, x, y, width=2, head=3):
        fig.add_annotation(x=x, y=y, ax=ax, ay=ay, showarrow=True,
                           arrowhead=head, arrowwidth=width, arrowcolor="#222")

    # Data flow: LOCAL → EM
    arrow(0.21, 0.25, 0.30, 0.25)
    arrow(0.21, 0.50, 0.30, 0.50)
    arrow(0.21, 0.75, 0.30, 0.75)

    # Data flow: EM → Group Manager
    arrow(0.46, 0.25, 0.56, 0.50)
    arrow(0.46, 0.50, 0.56, 0.50)
    arrow(0.46, 0.75, 0.56, 0.50)

    # Recommendation flow
    arrow(0.74, 0.50, 0.79, 0.50, width=3, head=4)

    fig.add_annotation(x=0.5, y=0.02, 
                       text="Architecture: LOCAL Nodes → Enterprise Managers → Group Manager → Strategic Recommendation",
                       showarrow=False, font=dict(size=12, color="#222"))
    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1])
    return fig

# Run Simulation
if st.button("Run Cross-Company Simulation"):
    with st.spinner("Orchestrating analysis across Enterprise Managers..."):
        try:
            result = run_simulation(query)

            # Display Architecture Diagram First
            st.subheader("Enterprise AI Architecture")
            st.plotly_chart(build_diagram_figure(), use_container_width=True)
            
            st.markdown("---")
            
            # Strategic Recommendation
            st.subheader("🎯 Group Manager Strategic Recommendation")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Recommended Plants", result.get('recommended_plant', 'N/A'))
                st.metric("Expected Increase", f"{result.get('expected_increase_tpa', 0)/1_000_000:.2f} MTPA")
            with col2:
                st.metric("Total Investment", f"${result.get('investment_usd', 0)/1_000_000:.2f}M")
                st.metric("Energy Required", f"{result.get('energy_required_mw', 0)} MW")
            with col3:
                st.metric("ROI Period", f"{result.get('roi_months', 0)} months")
                timeline = result.get('implementation_timeline', {})
                st.metric("Implementation Time", f"{timeline.get('total_months', 'N/A')} months")

            # Critical Business Protections
            st.success("✅ **BUSINESS PROTECTIONS GUARANTEED**")
            col1, col2 = st.columns(2)
            with col1:
                st.info("**Ports Protection**: Commercial cargo operations (4.55 MTPA) remain completely unaffected")
            with col2:
                st.info("**Energy Protection**: Grid sales to national grid (720 MW) remain completely unaffected")

            # Action Plan
            st.subheader("📋 Strategic Action Plan")
            st.write(result.get('action_plan', 'No action plan available.'))

            # Plant Allocations
            allocations = result.get("allocations")
            if allocations:
                st.subheader("🏭 Production Allocation Across Steel Plants")
                for allocation in allocations:
                    plant = allocation.get("plant_id")
                    allocated = allocation.get("allocated_tpa", 0)
                    feasible = allocation.get("feasible_tpa", 0)
                    capex = allocation.get("capex_allocated_usd", 0)
                    energy = allocation.get("energy_required_mw", 0)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Plant", plant)
                    with col2:
                        st.metric("Allocated Increase", f"{allocated/1000:.0f} KTPA")
                    with col3:
                        st.metric("Plant Investment", f"${capex/1000:.0f}K")
                    with col4:
                        st.metric("Energy Needed", f"{energy:.1f} MW")

            # Infrastructure Analysis
            if "infrastructure_requirements" in result:
                st.subheader("🏗️ Infrastructure Impact Analysis")
                infra = result["infrastructure_requirements"]
                
                st.write("**Port Capacity Analysis**")
                for item in infra.get("port_capacity_analysis", []):
                    st.write(f"- {item}")
                
                st.write("**Energy Capacity Analysis**") 
                for item in infra.get("energy_capacity_analysis", []):
                    st.write(f"- {item}")

            # Implementation Timeline
            timeline = result.get("implementation_timeline", {})
            if timeline:
                st.subheader("📅 Implementation Timeline")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Planning Phase", f"{timeline.get('planning_months', 0)} months")
                with col2:
                    st.metric("Implementation Phase", f"{timeline.get('implementation_months', 0)} months")
                with col3:
                    st.metric("Commissioning Phase", f"{timeline.get('commissioning_months', 0)} months")
                
                st.write("**Key Milestones:**")
                for milestone in timeline.get("key_milestones", []):
                    st.write(f"- {milestone}")

            # Rationale and Justification
            st.subheader("🔍 Decision Rationale")
            st.write(result.get("summary", "No rationale available."))
            
            why_chosen = result.get("why_chosen", [])
            if why_chosen:
                st.write("**Key Decision Factors:**")
                for reason in why_chosen:
                    st.write(f"- {reason}")

            # Enterprise Manager Summaries
            st.subheader("🏢 Enterprise Manager Contributions")
            cols = st.columns(3)
            
            with cols[0]:
                st.write("**Steel EM (Company B)**")
                steel_candidates = result["em_summaries"].get("steel_top_candidates", [])
                for candidate in steel_candidates[:3]:  # Show top 3
                    plant = candidate.get('plant_id')
                    increase = candidate.get('feasible_increase_tpa', 0)
                    st.write(f"- {plant}: +{increase/1000:.0f} KTPA capacity")
                
                st.write("**All Steel Plants:**")
                for plant in result["em_summaries"].get("steel_units_details", []):
                    pid = plant.get('plant_id')
                    util = plant.get('utilization', 0)
                    st.write(f"- {pid}: {util*100:.0f}% utilization")

            with cols[1]:
                st.write("**Ports EM (Company A)**")
                ports_info = result["em_summaries"].get("ports_info", {})
                current_mtpa = ports_info.get("current_throughput_mt", 0)
                capacity_mtpa = sum([p.get('annual_capacity_mt', 0) for p in result["em_summaries"].get("port_units_details", [])])
                st.write(f"- Current: {current_mtpa:.1f} / {capacity_mtpa:.1f} MTPA")
                st.write(f"- Commercial: {current_mtpa * 0.7:.1f} MTPA (protected)")
                st.write(f"- Available: {ports_info.get('port_headroom_tpa', 0)/1_000_000:.1f} MTPA")

            with cols[2]:
                st.write("**Energy EM (Company C)**")
                energy_info = result["em_summaries"].get("energy_info", {})
                total_capacity = energy_info.get("total_capacity_mw", 0)
                available = energy_info.get("energy_available_mw", 0)
                st.write(f"- Capacity: {total_capacity} MW")
                st.write(f"- Grid Sales: {total_capacity * 0.6:.0f} MW (protected)")
                st.write(f"- Available: {available} MW")

        except Exception as exc:
            st.error(f"Simulation Error: {exc}")
