# File: app.py
import streamlit as st
import pandas as pd
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Compact intro
st.markdown(
    """
**Group X** operates 4 ports, 4 steel plants and 3 power plants.  
All simulation results are based on assumed, simplified data for conceptual demonstration.

**Operating principles** — LOCAL nodes collect and forward site data. EMs (Ports EM, Steel EM, Energy EM) aggregate local data, connect to company systems (ERP/MES/SCADA) and can perform **company-level simulations and decisions**. The Group Manager aggregates EM outputs and runs cross-company simulations.

Purpose: produce a single, comprehensive recommendation and execution roadmap that covers internal and external factors required to complete the project.
"""
)

st.markdown("---")

# Strategic Query (single)
st.subheader("Strategic Query")
default_query = (
    "What is the recommended approach for increasing Group X’s steel production by approximately 2 MTPA, "
    "including the upgrades required across steel plants, the expected investment, the realistic implementation timeline, "
    "and the estimated period in which the investment can be recovered?"
)
query = st.text_area("Enter high-level strategic query", value=default_query, height=120)

# helpers
def currency(x):
    if x is None:
        return "—"
    try:
        return f"${int(round(x)):,}"
    except:
        return str(x)

def fmt(x):
    if x is None:
        return "—"
    if isinstance(x, float):
        return round(x,2)
    return x

# Run
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
    metrics = rec.get("metrics", {})

    # Header metrics
    st.header("Recommendation")
    st.subheader(rec.get("headline", "Recommendation"))
    if rec.get("summary"):
        st.write(rec["summary"])

    cols = st.columns(4)
    cols[0].metric("Capacity Added (MTPA)", fmt(metrics.get("added_mtpa")))
    cols[1].metric("Investment (USD)", currency(metrics.get("investment_usd")))
    cols[2].metric("Estimated Payback (months)", fmt(metrics.get("estimated_payback_months")))
    cols[3].metric("Project Timeline (months)", fmt(metrics.get("project_timeline_months")))

    st.write(f"**Confidence:** {result.get('confidence_pct','—')}%")

    st.markdown("---")

    # Key recommendations — exhaustive start->end (show all)
    st.header("Key Recommendations (Full Program Steps)")
    kr = rec.get("key_recommendations", [])
    for i, step in enumerate(kr, start=1):
        st.subheader(f"{i}. {step.get('step')}")
        st.write(f"**Owner:** {step.get('owner')}")
        st.write(f"**Estimated duration:** {step.get('duration_months')} months")
        for d in step.get("details", []):
            st.write(f"- {d}")
        if step.get("plants_in_scope"):
            st.write("**Plants in scope:** " + ", ".join(step.get("plants_in_scope")))
        st.markdown("")

    st.markdown("---")

    # Per-plant upgrades (specifics)
    st.header("Per-Plant Upgrade Specifications")
    per_plants = rec.get("per_plant_upgrades", [])
    for p in per_plants:
        st.subheader(f"{p.get('plant_name')} — add {p.get('added_mtpa')} MTPA")
        st.write(f"- Current capacity (tpa): {p.get('current_capacity_tpa'):,}")
        st.write(f"- Added capacity (tpa): {p.get('added_tpa'):,}")
        st.write(f"- Total CAPEX (USD): {currency(p.get('capex_total_usd'))}")
        st.write(f"- Estimated payback (months): {fmt(p.get('estimated_payback_months'))}")
        st.write(f"- Hiring estimate: {p.get('hiring_estimate')}")
        st.write("- Upgrade scope:")
        for u in p.get("upgrade_scope", []):
            st.write(f"  - {u}")
        st.write("- CAPEX breakdown:")
        for k,v in p.get("capex_breakdown_usd", {}).items():
            st.write(f"  - {k}: {currency(v)}")
        sched = p.get("schedule_months", {})
        st.write(f"- Procurement months: {sched.get('procurement_months')}, Implementation months: {sched.get('implementation_months')}, Commissioning months: {sched.get('commissioning_months')}")
        st.markdown("")

    st.markdown("---")

    # Roadmap phases
    st.header("Roadmap (Phases)")
    phases = result.get("roadmap", {}).get("phases", [])
    if phases:
        cols = st.columns(len(phases))
        for col, ph in zip(cols, phases):
            html = f"""
            <div style="padding:8px; min-width:160px; box-sizing:border-box;">
                <div style="font-weight:700; font-size:14px;">{ph.get('phase')}</div>
                <div style="margin-top:6px;"><strong>Duration:</strong> {ph.get('months')} months</div>
                <div style="font-size:13px; color:#444;">{ph.get('notes','')}</div>
            </div>
            """
            col.markdown(html, unsafe_allow_html=True)
    else:
        st.write("No roadmap available.")

    st.markdown("---")

    # Decision rationale
    st.header("Decision Rationale")
    for b in result.get("rationale",{}).get("bullets",[]):
        st.write(f"- {b}")

    st.markdown("---")

    # Infrastructure plan summary (how ports & energy support without compromising commercial/national supply)
    st.header("Infrastructure Support Plan — Ports & Energy")
    ports_summary = result.get("em_summaries",{}).get("ports",{})
    energy_summary = result.get("em_summaries",{}).get("energy",{})

    st.subheader("Ports: ensuring commercial cargo remains uncompromised")
    st.write(f"- Total port capacity (tpa): {ports_summary.get('total_port_capacity_tpa', '—'):,}")
    st.write(f"- Available for project (tpa): {ports_summary.get('available_for_project_tpa', '—'):,}")
    st.write(f"- Project requirement (tpa): {ports_summary.get('required_for_project_tpa', '—'):,}")
    st.write("- Measures implemented:")
    st.write("  - Reserve temporary berth capacity and 3PL partners for project shipments.")
    st.write("  - Time-windowed arrival scheduling to avoid commercial peaks.")
    st.write("  - Rapid customs lane for project-critical shipments and frame broker agreements.")
    st.write("  - Additional handling shifts during planned ramp windows (maintain full commercial allocations).")

    st.subheader("Energy: ensuring national-grid supply remains uncompromised")
    st.write(f"- Total energy capacity (MW): {energy_summary.get('total_energy_capacity_mw','—')}")
    st.write(f"- Available for project (MW): {energy_summary.get('available_for_project_mw','—')}")
    st.write(f"- Project requirement (MW): {energy_summary.get('required_for_project_mw','—')}")
    st.write("- Measures implemented:")
    st.write("  - Negotiate short-term PPAs for incremental MW during ramp (use renewables + battery where economic).")
    st.write("  - Install WHR / captive generation to reduce grid draw during peak windows.")
    st.write("  - Upgrade substation capacity and implement smart load scheduling so national-grid supply contracts remain intact.")
    st.write("  - Retain prioritization for national-grid supply in dispatch schedules.")

    st.markdown("---")
    st.success("Recommendation & roadmap generated. All sections above provide a complete start-to-finish program guide.")

# End of app.py
