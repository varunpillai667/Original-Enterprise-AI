===== FILE: app.py =====

# app.py
import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# --- Intro text (short, precise, with numbers) ---
st.markdown(
    """
**Group X** has three subsidiaries — **Ports (4 ports)**, **Steel (4 plants)**, and **Energy (3 power plants)**.  
All outputs in this prototype use **assumed, simplified data** for demonstration only.

---

### Operating Principles

**LOCAL Nodes — Site Layer**  
Installed at every port, steel plant, and power plant. They collect and buffer operational data and send it **only to their own company’s Enterprise Manager (EM)**. LOCAL Nodes perform **no analytics**.

**Enterprise Managers (EMs) — Company Layer**  
Each company has its own EM:
- **Ports EM** managing all 4 ports  
- **Steel EM** managing all 4 steel plants  
- **Energy EM** managing all 3 power plants

Each EM receives data from its own LOCAL Nodes and also connects to the company’s central office systems (ERP, CRM, MES, HRMS). EMs run company-level forecasting, simulations, and decision-making. Companies remain **fully separated** at this layer.

**Group Manager — Group Layer**  
Integrates outputs from all EMs along with group-level systems. Runs cross-company simulations, strategic scenarios, and capital allocation. Every strategic query is **fully visible and explainable**.

---

**Purpose:** This demo illustrates the architecture and decision flow. All numbers and simulations are **illustrative only**.
"""
)

st.markdown("---")

# --- Strategic Query (kept fully visible as requested) ---
st.subheader("Strategic Query")
st.write("Ask a high-level, strategic question for Group X (example: 'How can we increase steel production with minimal investment?').")
query = st.text_area("Enter strategic query here", value="Increase total steel production by 2 MTPA within the next 15 months, allocating the capacity increase appropriately across all steel plants. Ensure that the investments required for this upgrade can be recovered within a payback period of less than 3 years.", height=120)

# --- Run Simulation Button ---
col_run, col_empty = st.columns([1, 5])
with col_run:
    run_button = st.button("Run Simulation")

# Output area
output_placeholder = st.empty()

if run_button:
    if not query.strip():
        st.error("Please enter a strategic query before running the simulation.")
    else:
        with st.spinner("Running simulation and aggregating EM outputs..."):
            try:
                result = run_simulation(query)
            except Exception as exc:
                st.error(f"Simulation failed: {exc}")
                result = None

        if result:
            # Top-level summary
            st.subheader("Simulation Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Recommended Plant / Action", result.get("recommended_plant", "—"))
            with col2:
                exp_inc = result.get("expected_increase_tpa", 0)
                # display in MTPA if value large, else raw
                if exp_inc >= 1_000_000:
                    st.metric("Expected Increase", f"{exp_inc/1_000_000:.2f} MTPA")
                else:
                    st.metric("Expected Increase (tpa)", f"{exp_inc:.0f}")
            with col3:
                st.metric("Estimated Investment (USD)", f"${result.get('investment_usd', 0):,.0f}")

            # ROI / energy
            st.write("")
            cols = st.columns(2)
            with cols[0]:
                st.write(f"**ROI Period:** {result.get('roi_months', '—')} months")
                st.write(f"**Energy Required:** {result.get('energy_required_mw', '—')} MW")
            with cols[1]:
                st.write("**Confidence:**")
                st.progress(int(result.get("confidence_pct", 50)))

            st.markdown("---")

            # Enterprise Manager summaries (ports / steel / energy)
            st.subheader("Enterprise Manager Summaries")
            em_cols = st.columns(3)
            try:
                em_summaries = result.get("em_summaries", {})
            except Exception:
                em_summaries = {}

            # Ports EM
            with em_cols[0]:
                st.markdown("**Ports EM**")
                ports_info = em_summaries.get("ports_info", {})
                st.write(f"- Managed ports: {ports_info.get('num_ports', 4)}")
                if "port_recommendations" in ports_info:
                    for rec in ports_info.get("port_recommendations", []):
                        st.write(f"- {rec}")

            # Steel EM
            with em_cols[1]:
                st.markdown("**Steel EM**")
                steel_info = em_summaries.get("steel_info", {})
                st.write(f"- Managed plants: {steel_info.get('num_plants', 4)}")
                if "plant_recommendations" in steel_info:
                    for rec in steel_info.get("plant_recommendations", []):
                        st.write(f"- {rec}")

            # Energy EM
            with em_cols[2]:
                st.markdown("**Energy EM**")
                energy_info = em_summaries.get("energy_info", {})
                st.write(f"- Managed power plants: {energy_info.get('num_plants', 3)}")
                if "energy_recommendations" in energy_info:
                    for rec in energy_info.get("energy_recommendations", []):
                        st.write(f"- {rec}")

            st.markdown("---")

            # Detailed infrastructure analysis if present
            infra = result.get("infrastructure_analysis", {})
            if infra:
                st.subheader("Infrastructure Analysis")
                if infra.get("port_capacity_analysis"):
                    st.write("**Port Capacity Analysis**")
                    for item in infra.get("port_capacity_analysis", []):
                        st.write(f"- {item}")
                if infra.get("energy_capacity_analysis"):
                    st.write("**Energy Capacity Analysis**")
                    for item in infra.get("energy_capacity_analysis", []):
                        st.write(f"- {item}")

            # Implementation timeline (if available)
            timeline = result.get("implementation_timeline", {})
            if timeline:
                st.subheader("Implementation Timeline")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Planning Phase", f"{timeline.get('planning_months', 0)} months")
                with c2:
                    st.metric("Implementation Phase", f"{timeline.get('implementation_months', 0)} months")
                with c3:
                    st.metric("Stabilization", f"{timeline.get('stabilization_months', 0)} months")

            # Raw result for debugging / transparency (collapsible)
            with st.expander("Full Result (raw)"):
                st.json(result)
        else:
            st.warning("No result returned from simulation. Check logs or inputs.")
