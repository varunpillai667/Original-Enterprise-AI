import streamlit as st
import pandas as pd
import json
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

st.markdown(
    """
### Introduction

**Group X** operates **4 ports**, **4 steel plants**, and **3 power plants**.  
All simulation results in this prototype are based on **assumed, simplified data only**, used only for conceptual demonstration.

### Operating Principles

**LOCAL Nodes — Site Layer**  
LOCAL Nodes collect and transmit operational data from each port, steel plant, and power plant.  
They do minimal processing.

**Enterprise Managers (EMs) — Company Layer**  
Each company has an EM:  
- **Ports EM** (manages all 4 ports)  
- **Steel EM** (manages all 4 steel plants)  
- **Energy EM** (manages all 3 power plants**)  

EMs collect data both from LOCAL nodes and from their **company-level IT systems** (ERP, MES, SCADA, planning systems).  
They make company-level decisions and send consolidated information upward.

**Group Manager — Group Layer**  
The Group Manager connects all EMs and **group-level systems**, enabling Group-X-wide coordination, simulations, and decisions.

**Purpose of this prototype:**  
Explain how a multi-layer enterprise system could respond to strategic questions using simulated data.
"""
)

st.markdown("---")

def parse_hiring(x: Any) -> Dict[str, int]:
    base = {"engineers": 0, "maintenance": 0, "operators": 0, "project_managers": 0}
    if isinstance(x, dict):
        return {k: int(x.get(k, 0)) for k in base}
    if isinstance(x, str):
        try:
            j = json.loads(x)
            if isinstance(j, dict):
                return {k: int(j.get(k, 0)) for k in base}
        except:
            pass
    return base

def nice_number(v: Any):
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return round(v, 2)
    return v

def pretty_infra(data: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for section, vals in (data or {}).items():
        if isinstance(vals, dict):
            out[section] = {k: nice_number(v) for k, v in vals.items()}
        else:
            out[section] = vals
    return out

st.subheader("Strategic Query")
query = st.text_area(
    "Enter high-level strategic query",
    value=(
        "Increase total steel production by 2 MTPA within the next 15 months, "
        "allocating the capacity increase appropriately across all steel plants. "
        "Ensure that the investments required for this upgrade can be recovered "
        "within a payback period of less than 3 years."
    ),
    height=140,
)

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

    # Recommendation — full width
    st.header("Recommendation")
    st.subheader(rec.get("headline", "Proposed action"))
    if rec.get("summary"):
        st.write(rec["summary"])

    metrics = rec.get("metrics", {})
    mcols = st.columns(4)
    mcols[0].metric("Added (MTPA)", metrics.get("added_mtpa", "—"))
    mcols[1].metric("Investment (USD)", f"${metrics.get('investment_usd',0):,}")
    mcols[2].metric("Est. Payback (months)", metrics.get("estimated_payback_months","—"))
    mcols[3].metric("Confidence", f"{result.get('confidence_pct','—')}%")

    if rec.get("actions"):
        st.subheader("Key recommended actions")
        for a in rec.get("actions", [])[:8]:
            st.write(f"- {a}")

    debug_lines = result.get("notes", {}).get("debug", [])
    if debug_lines:
        with st.expander("Debug / data-loading notes"):
            for d in debug_lines:
                st.write(f"- {d}")

    st.markdown("---")

    # Roadmap — clean horizontal layout below Recommendation
    st.header("Roadmap (Phases)")
    phases = roadmap.get("phases", [])
    if phases:
        cols = st.columns(len(phases))
        for col, ph in zip(cols, phases):
            html = f"""
            <div style="padding:14px; min-width:200px; box-sizing:border-box;">
                <div style="font-weight:700; font-size:15px; margin-bottom:6px; white-space:nowrap;">
                    {ph.get('phase','')}
                </div>
                <div style="margin-bottom:6px;">
                    <strong>Duration:</strong> {ph.get('months','—')} months
                </div>
                <div style="font-size:13px; color:#444; white-space:normal;">
                    {ph.get('notes','')}
                </div>
            </div>
            """
            col.markdown(html, unsafe_allow_html=True)
    else:
        st.write("No roadmap phases available.")

    st.markdown("---")

    st.subheader("Per-Plant Schedule")
    p_sched = roadmap.get("per_plant_schedule", [])
    if p_sched:
        st.table(pd.DataFrame(p_sched))
    else:
        st.write("Schedule unavailable.")

    st.markdown("---")

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
            if "hiring_estimate" in df.columns:
                hires = df["hiring_estimate"].apply(parse_hiring)
                hires_df = pd.DataFrame(list(hires))
                df = pd.concat([df.drop(columns=["hiring_estimate"]), hires_df], axis=1)
            if "capex_usd" in df.columns:
                df["capex_usd"] = df["capex_usd"].apply(lambda x: f"${x:,}")
            if "annual_margin_usd" in df.columns:
                df["annual_margin_usd"] = df["annual_margin_usd"].apply(lambda x: f"${x:,}")
            st.table(df[[c for c in df.columns if c in ["name","current_capacity_tpa","added_mtpa","capex_usd","annual_margin_usd","payback_months"]]])
        else:
            st.write("No plant distribution available.")

    st.markdown("---")

    st.header("Infrastructure Analysis")
    infra = pretty_infra(result.get("infrastructure_analysis", {}))
    ports = infra.get("ports", {})
    energy = infra.get("energy", {})

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Ports")
        if ports:
            preferred_order = [
                "total_port_capacity_tpa",
                "used_port_tpa",
                "group_port_share_tpa",
                "spare_port_tpa",
                "available_port_for_steel_tpa",
                "port_throughput_required_tpa",
            ]
            for key in preferred_order:
                if key in ports:
                    label = key.replace("_", " ").title()
                    st.write(f"- **{label}:** {ports[key]}")
            for k, v in ports.items():
                if k not in preferred_order:
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
        else:
            st.write("No port data.")

    with c2:
        st.subheader("Energy")
        if energy:
            preferred_energy_order = [
                "total_energy_capacity_mw",
                "used_energy_mw",
                "group_energy_share_mw",
                "spare_energy_mw",
                "available_energy_for_steel_mw",
                "energy_required_mw",
            ]
            for key in preferred_energy_order:
                if key in energy:
                    label = key.replace("_", " ").title()
                    st.write(f"- **{label}:** {energy[key]}")
            for k, v in energy.items():
                if k not in preferred_energy_order:
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
        else:
            st.write("No energy data.")

    st.markdown("---")
