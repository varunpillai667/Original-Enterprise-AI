# app.py
import streamlit as st
import pandas as pd
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

Each EM receives data from its own LOCAL Nodes and also connects to the company’s central office systems (ERP, CRM, MES, HRMS).  
EMs run company-level forecasting, simulations, and decision-making. Companies remain **fully separated** at this layer.

**Group Manager — Group Layer**  
Integrates outputs from all EMs along with group-level systems.  
Runs cross-company simulations, strategic scenarios, and capital allocation.  
Every strategic query is **fully visible and explainable**.

---

**Purpose:** This demo illustrates the architecture and decision flow.  
All numbers and simulations are **illustrative only**.
"""
)

st.markdown("---")

# --- Strategic Query ---
st.subheader("Strategic Query")
st.write("High-level strategic question for Group X.")
query = st.text_area(
    "Enter strategic query here",
    value=(
        "Increase total steel production by 2 MTPA within the next 15 months, "
        "allocating the capacity increase appropriately across all steel plants. "
        "Ensure that the investments required for this upgrade can be recovered "
        "within a payback period of less than 3 years."
    ),
    height=120,
)

# Run Simulation Button
col_run, _ = st.columns([1, 5])
with col_run:
    run_button = st.button("Run Simulation")

if run_button:
    if not query.strip():
        st.error("Please enter a strategic query before running the simulation.")
    else:
        with st.spinner("Running simulation..."):
            try:
                result = run_simulation(query)
            except Exception as exc:
                st.error(f"Simulation failed: {exc}")
                result = None

        if result:
            # Summary metrics
            st.subheader("Simulation Summary")
            c1, c2, c3 = st.columns(3)
            c1.metric("Recommended Plant(s) / Action", result.get("recommended_plant", "—"))
            exp_inc = result.get("expected_increase_tpa", 0)
            if exp_inc >= 1_000_000:
                c2.metric("Expected Increase", f"{exp_inc/1_000_000:.2f} MTPA")
            else:
                c2.metric("Expected Increase (tpa)", f"{exp_inc:,}")
            c3.metric("Estimated Investment (USD)", f"${result.get('investment_usd', 0):,}")

            # ROI and energy
            st.write("")
            r1, r2 = st.columns(2)
            r1.write(f"**ROI Period:** {result.get('roi_months', '—')} months")
            r1.write(f"**Confidence:** {result.get('confidence_pct', '—')}%")
            r2.write(f"**Energy Required:** {result.get('energy_required_mw', '—')} MW")

            st.markdown("---")

            # EM summaries (compact)
            st.subheader("Enterprise Manager Summaries")
            ems = result.get("em_summaries", {})
            cols = st.columns(3)
            # Ports
            with cols[0]:
                st.markdown("**Ports EM**")
                ports_info = ems.get("ports_info", {})
                st.write(f"- Managed ports: {ports_info.get('num_ports', '—')}")
            # Steel
            with cols[1]:
                st.markdown("**Steel EM**")
                steel_info = ems.get("steel_info", {})
                st.write(f"- Managed plants: {steel_info.get('num_plants', '—')}")
            # Energy
            with cols[2]:
                st.markdown("**Energy EM**")
                energy_info = ems.get("energy_info", {})
                st.write(f"- Managed power plants: {energy_info.get('num_plants', '—')}")

            st.markdown("---")

            # Per-plant financial table
            st.subheader("Per-Plant Financials")
            distribution = steel_info.get("plant_distribution", [])
            if distribution:
                df_rows = []
                for p in distribution:
                    df_rows.append({
                        "Plant": p.get("name", p.get("id", "")),
                        "Current Capacity (tpa)": int(p.get("current_capacity_tpa", 0)),
                        "Added (tpa)": int(p.get("added_tpa", 0)),
                        "New Capacity (tpa)": int(p.get("new_capacity_tpa", 0)),
                        "CAPEX (USD)": int(p.get("capex_usd", 0)),
                        "Annual Margin (USD)": int(p.get("annual_margin_usd", 0)),
                        "Payback (months)": p.get("payback_months", None),
                    })
                df = pd.DataFrame(df_rows)
                # format numbers for readability
                df_display = df.copy()
                df_display["Current Capacity (tpa)"] = df_display["Current Capacity (tpa)"].map("{:,}".format)
                df_display["Added (tpa)"] = df_display["Added (tpa)"].map("{:,}".format)
                df_display["New Capacity (tpa)"] = df_display["New Capacity (tpa)"].map("{:,}".format)
                df_display["CAPEX (USD)"] = df_display["CAPEX (USD)"].map(lambda x: f"${x:,}")
                df_display["Annual Margin (USD)"] = df_display["Annual Margin (USD)"].map(lambda x: f"${x:,}")
                st.table(df_display)
            else:
                st.write("No per-plant distribution available.")

            st.markdown("---")

            # Infrastructure and timeline
            st.subheader("Infrastructure & Timeline")
            infra = result.get("infrastructure_analysis", {})
            for line in infra.get("port_capacity_analysis", []):
                st.write(f"- {line}")
            for line in infra.get("energy_capacity_analysis", []):
                st.write(f"- {line}")

            timeline = result.get("implementation_timeline", {})
            if timeline:
                st.write("")
                t1, t2, t3 = st.columns(3)
                t1.metric("Planning", f"{timeline.get('planning_months', 0)} months")
                t2.metric("Implementation", f"{timeline.get('implementation_months', 0)} months")
                t3.metric("Stabilization", f"{timeline.get('stabilization_months', 0)} months")

            # Notes & recommendations
            st.markdown("---")
            st.subheader("Notes & Recommendations")
            notes = result.get("notes", {})
            assumptions = notes.get("assumptions", {})
            st.write("**Assumptions**")
            capex_ass = assumptions.get('capex_per_mtpa_usd')
            if capex_ass is not None:
                st.write(f"- CAPEX per 1 MTPA: ${capex_ass:,}")
            else:
                st.write(f"- CAPEX per 1 MTPA: —")
            st.write(f"- Margin per tonne: ${assumptions.get('margin_per_ton_usd', '—')}")
            st.write(f"- Energy per 1 MTPA: {assumptions.get('mw_per_mtpa', '—')} MW")

            st.write("")
            st.write("**Recommendations**")
            for rec in notes.get("recommendations", []):
                st.write(f"- {rec}")

            st.markdown("---")
            with st.expander("Full Result (raw)"):
                st.json(result)
        else:
            st.warning("No result returned from simulation. Check logs or inputs.")
