# ------------------------------
# File: app.py
# ------------------------------
import streamlit as st
import pandas as pd
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Compact intro (tight spacing) with EM simulation capability
st.markdown(
    """
**Group X** operates 4 ports, 4 steel plants and 3 power plants.  
All simulation results are based on assumed, simplified data for conceptual demonstration.

**Operating principles** — LOCAL nodes collect and forward site data. EMs (Ports EM, Steel EM, Energy EM) aggregate local data, connect to company systems (ERP/MES/SCADA) and can perform **company-level simulations and decisions**. The Group Manager aggregates EM outputs and runs cross-company simulations.

Purpose: produce a single, risk-adjusted recommendation and roadmap that considers internal and external factors.
"""
)

st.markdown("---")

# helpers
def parse_hiring(x: Any) -> Dict[str, int]:
    base = {"engineers": 0, "maintenance": 0, "operators": 0, "project_managers": 0}
    if isinstance(x, dict):
        return {k: int(x.get(k, 0)) for k in base}
    return base

def pretty_infra(data: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for section, vals in (data or {}).items():
        if isinstance(vals, dict):
            out[section] = {k: (f"{v:,}" if isinstance(v, int) else round(v,2)) for k, v in vals.items()}
        else:
            out[section] = vals
    return out

st.subheader("Strategic Query")
default_query = ("What is the recommended approach for increasing Group X’s steel production by approximately 2 MTPA, "
                 "including the upgrades required across steel plants, the expected investment, the realistic implementation timeline, "
                 "and the estimated period in which the investment can be recovered?")
query = st.text_area("Enter high-level strategic query", value=default_query, height=120)

# Run
if st.button("Run Simulation"):

    if not query.strip():
        st.error("Please enter a strategic query.")
        st.stop()

    with st.spinner("Running risk-adjusted simulation..."):
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
    c1.metric("Added (MTPA)", metrics.get("added_mtpa", "—"))
    c2.metric("Investment (USD, risk-adjusted)", f"${metrics.get('investment_usd_risk_adjusted', metrics.get('investment_usd_base',0)):,}")
    c3.metric("Est. Payback (months, risk)", metrics.get("estimated_payback_months_risk","—"))
    c4.metric("Confidence (%)", f"{result.get('confidence_pct','—')}%")

    if rec.get("actions"):
        st.subheader("Key recommended actions")
        for a in rec.get("actions", [])[:8]:
            st.write(f"- {a}")

    debug_lines = result.get("notes", {}).get("debug", [])
    if debug_lines:
        with st.expander("Data / debug notes"):
            for d in debug_lines:
                st.write(f"- {d}")

    st.markdown("---")

    # Roadmap (below recommendation) show base vs risk-adjusted months
    st.header("Roadmap (Phases) — Base vs Risk-Adjusted")
    phases = roadmap.get("phases", [])
    if phases:
        cols = st.columns(len(phases))
        for col, ph in zip(cols, phases):
            base_m = ph.get("months_base", "—")
            risk_m = ph.get("months_risk", "—")
            col.markdown(
                f"""
                <div style="padding:10px; min-width:160px; box-sizing:border-box;">
                  <div style="font-weight:700; font-size:14px; margin-bottom:4px; white-space:nowrap;">{ph.get('phase','')}</div>
                  <div style="font-size:13px; margin-bottom:4px;"><strong>Base:</strong> {base_m} months</div>
                  <div style="font-size:13px; margin-bottom:6px;"><strong>Risk adj:</strong> {risk_m} months</div>
                  <div style="font-size:12px; color:#444;">{ph.get('notes','')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.write("No roadmap data.")

    st.markdown("---")

    # Per-Plant Schedule
    st.subheader("Per-Plant Schedule (Risk-adjusted windows)")
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
            st.table(df[[c for c in df.columns if c in ["name","current_capacity_tpa","added_mtpa","capex_usd","annual_margin_usd","base_payback_months"]]])
        else:
            st.write("No plant distribution available.")

    st.markdown("---")

    # Infrastructure analysis (side-by-side)
    st.header("Infrastructure Analysis (Ports | Energy)")
    infra = pretty_infra(result.get("infrastructure_analysis", {}))
    ports = infra.get("ports", {})
    energy = infra.get("energy", {})

    col_ports, col_energy = st.columns(2)
    with col_ports:
        st.subheader("Ports")
        if ports:
            for k,v in ports.items():
                st.write(f"- **{k.replace('_',' ').title()}:** {v}")
        else:
            st.write("No port data.")
    with col_energy:
        st.subheader("Energy")
        if energy:
            for k,v in energy.items():
                st.write(f"- **{k.replace('_',' ').title()}:** {v}")
        else:
            st.write("No energy data.")

    st.markdown("---")
