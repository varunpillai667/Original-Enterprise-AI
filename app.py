# =========================
# File: app.py
# =========================
import streamlit as st
import pandas as pd
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Compact intro (tight spacing) including EM capability
st.markdown(
    """
**Group X** operates 4 ports, 4 steel plants and 3 power plants.  
All simulation results are based on assumed, simplified data for conceptual demonstration.

**Operating principles** — LOCAL nodes collect and forward site data. EMs (Ports EM, Steel EM, Energy EM) aggregate local data, connect to company systems (ERP/MES/SCADA) and can perform **company-level simulations and decisions**. The Group Manager aggregates EM outputs and runs cross-company simulations.

Purpose: produce a single, comprehensive recommendation and roadmap that covers internal and external factors required to complete the project.
"""
)

st.markdown("---")

# --- SINGLE Strategic Query box — placed at top (Option A) ---
st.subheader("Strategic Query")
default_query = (
    "What is the recommended approach for increasing Group X’s steel production by approximately 2 MTPA, "
    "including the upgrades required across steel plants, the expected investment, the realistic implementation timeline, "
    "and the estimated period in which the investment can be recovered?"
)
query = st.text_area("Enter high-level strategic query", value=default_query, height=120)

# helpers
def parse_hiring(x: Any):
    base = {"engineers": 0, "maintenance": 0, "operators": 0, "project_managers": 0}
    if isinstance(x, dict):
        return {k: int(x.get(k, 0)) for k in base}
    return base

def format_number(v: Any):
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return round(v, 2)
    return v

# Run simulation
if st.button("Run Simulation"):

    if not query.strip():
        st.error("Please enter a strategic query.")
        st.stop()

    with st.spinner("Running simulation..."):
        try:
            result = run_simulation(query)
        except Exception as exc:
            st.error(f"Simulation error: {exc}")
            st.stop()

    rec = result.get("recommendation", {})
    roadmap = result.get("roadmap", {})

    # Recommendation (full width)
    st.header("Recommendation")
    st.subheader(rec.get("headline", "Proposed action"))
    if rec.get("summary"):
        st.write(rec["summary"])

    metrics = rec.get("metrics", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Capacity Added (MTPA)", metrics.get("added_mtpa", "—"))
    inv = metrics.get("investment_usd", 0) or 0
    c2.metric("Investment (USD)", f"${inv:,}")
    c3.metric("Estimated Payback (months)", metrics.get("estimated_payback_months", "—"))
    c4.metric("Project Timeline (months)", metrics.get("project_timeline_months", "—"))

    # Confidence shown separately (smaller)
    st.write(f"**Confidence:** {result.get('confidence_pct', '—')}%")

    if rec.get("actions"):
        st.subheader("Key recommended actions")
        for a in rec.get("actions", [])[:8]:
            st.write(f"- {a}")

    st.markdown("---")

    # Roadmap — below Recommendation (clean horizontal layout)
    st.header("Roadmap (Phases)")
    phases = roadmap.get("phases", [])
    if phases:
        cols = st.columns(len(phases))
        for col, ph in zip(cols, phases):
            months = ph.get("months", "—")
            html = f"""
            <div style="padding:10px; min-width:160px; box-sizing:border-box;">
                <div style="font-weight:700; font-size:14px; margin-bottom:6px; white-space:nowrap;">{ph.get('phase','')}</div>
                <div style="margin-bottom:6px;"><strong>Duration:</strong> {months} months</div>
                <div style="font-size:13px; color:#444; white-space:normal;">{ph.get('notes','')}</div>
            </div>
            """
            col.markdown(html, unsafe_allow_html=True)
    else:
        st.write("No roadmap phases available.")

    st.markdown("---")

    # Per-Plant Schedule
    st.subheader("Per-Plant Schedule")
    p_sched = roadmap.get("per_plant_schedule", [])
    if p_sched:
        st.table(pd.DataFrame(p_sched))
    else:
        st.write("Schedule unavailable.")

    st.markdown("---")

    # Decision Rationale & Financials
    st.header("Decision Rationale & Financials")
    col_rat, col_fin = st.columns([2, 1])

    with col_rat:
        st.subheader("Decision Rationale")
        for b in result.get("rationale", {}).get("bullets", []):
            st.write(f"- {b}")

    with col_fin:
        st.subheader("Per-Plant Financials")
        plant_dist = result.get("em_summaries", {}).get("steel_info", {}).get("plant_distribution", [])
        if plant_dist:
            df = pd.DataFrame(plant_dist)
            if "capex_usd" in df.columns:
                df["capex_usd"] = df["capex_usd"].apply(lambda x: f"${x:,}")
            if "annual_margin_usd" in df.columns:
                df["annual_margin_usd"] = df["annual_margin_usd"].apply(lambda x: f"${x:,}")
            display_cols = [c for c in df.columns if c in ["name","current_capacity_tpa","added_mtpa","capex_usd","annual_margin_usd","base_payback_months"]]
            if display_cols:
                st.table(df[display_cols])
            else:
                st.write("No plant financials available.")
        else:
            st.write("No plant distribution available.")

    st.markdown("---")

    # Infrastructure (ports & energy) side-by-side
    st.header("Infrastructure Analysis (Ports | Energy)")
    infra = result.get("em_summaries", {})
    ports_info = infra.get("ports_info", {})
    energy_info = infra.get("energy_info", {})

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Ports")
        if ports_info:
            st.write(f"- **Total port capacity (tpa):** {format_number(ports_info.get('total_port_capacity_tpa','—'))}")
            st.write(f"- **Used port (tpa):** {format_number(ports_info.get('used_port_tpa','—'))}")
            st.write(f"- **Required for project (tpa):** {format_number(result.get('recommendation',{}).get('metrics',{}).get('port_throughput_required_tpa','—'))}")
        else:
            st.write("No port data.")
    with c2:
        st.subheader("Energy")
        if energy_info:
            st.write(f"- **Total energy capacity (MW):** {format_number(energy_info.get('total_energy_capacity_mw','—'))}")
            st.write(f"- **Used energy (MW):** {format_number(energy_info.get('used_energy_mw','—'))}")
            st.write(f"- **Required for project (MW):** {format_number(result.get('recommendation',{}).get('metrics',{}).get('energy_required_mw','—'))}")
        else:
            st.write("No energy data.")

    st.markdown("---")

# End of app.py
