# app.py
import streamlit as st
import pandas as pd
import json
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# ---------------------------------------------------------
# FULL INTRO (RESTORED EXACTLY)
# ---------------------------------------------------------
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
- **Energy EM** (manages all 3 power plants)  

EMs collect data both from LOCAL nodes and from their **company-level IT systems** (ERP, MES, SCADA, planning systems).  
They make company-level decisions and send consolidated information upward.

**Group Manager — Group Layer**  
The Group Manager connects all EMs and **group-level systems**, enabling Group-X-wide coordination, simulations, and decisions.

**Purpose of this prototype:**  
Explain how a multi-layer enterprise system could respond to strategic questions using simulated data.
"""
)

st.markdown("---")

# -------------------------
# Helpers (display formatting)
# -------------------------
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

# -------------------------
# Strategic Query input
# -------------------------
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

# -------------------------
# Run Simulation button
# -------------------------
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

    # -------------------------
    # Recommendation (left) and Roadmap (right) — horizontal
    # -------------------------
    rec = result.get("recommendation", {})
    roadmap = result.get("roadmap", {})

    st.header("Recommendation & Roadmap")
    col_rec, col_road = st.columns([2, 1])

    with col_rec:
        st.subheader("Recommendation (Executive)")
        st.markdown(f"**{rec.get('headline','')}**")
        if rec.get("summary"):
            st.write(rec["summary"])
        metrics = rec.get("metrics", {})
        metric_cols = st.columns(4)
        metric_cols[0].metric("Added (MTPA)", metrics.get("added_mtpa", "—"))
        metric_cols[1].metric("Investment (USD)", f"${metrics.get('investment_usd',0):,}")
        metric_cols[2].metric("Est. Payback (months)", metrics.get("estimated_payback_months","—"))
        metric_cols[3].metric("Confidence", f"{result.get('confidence_pct','—')}%")

        if rec.get("actions"):
            st.markdown("**Top Actions (prioritized)**")
            for a in rec.get("actions", [])[:6]:
                st.write(f"- {a}")

    with col_road:
        st.subheader("Roadmap (Phases)")
        phases = roadmap.get("phases", [])
        if phases:
            cols_ph = st.columns(len(phases))
            for i, ph in enumerate(phases):
                with cols_ph[i]:
                    st.write(f"**{ph.get('phase','Phase')}**")
                    st.write(f"- Duration: {ph.get('months','—')} months")
                    if ph.get("notes"):
                        st.write(f"- {ph.get('notes')}")
        else:
            st.write("No roadmap phases available.")

    st.markdown("---")

    # -------------------------
    # Per-Plant Schedule (full width)
    # -------------------------
    st.subheader("Per-Plant Schedule")
    p_sched = roadmap.get("per_plant_schedule", [])
    if p_sched:
        st.table(pd.DataFrame(p_sched))
    else:
        st.write("Schedule unavailable.")

    st.markdown("---")

    # -------------------------
    # Decision Rationale (left) and Per-Plant Financials (right) — horizontal
    # -------------------------
    st.header("Decision Rationale & Financials")
    col_rat, col_fin = st.columns([2, 1])

    with col_rat:
        st.subheader("Why these recommendations? (Executive)")
        for b in result.get("rationale", {}).get("bullets", []):
            st.write(f"- {b}")

    with col_fin:
        st.subheader("Per-Plant Financials (top-level)")
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
            # show compact table
            st.table(df[ [c for c in df.columns if c in ["name","current_capacity_tpa","added_mtpa","capex_usd","annual_margin_usd","payback_months"] ] ])
        else:
            st.write("No plant distribution available.")

    st.markdown("---")

    # -------------------------
    # Infrastructure Analysis (Ports | Energy) side-by-side
    # -------------------------
    st.header("Infrastructure Analysis")
    infra = pretty_infra(result.get("infrastructure_analysis", {}))
    ports = infra.get("ports", {})
    energy = infra.get("energy", {})

    col_ports, col_energy = st.columns(2)
    with col_ports:
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

    with col_energy:
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

    # -------------------------
    # Full result (human readable) — side-by-side infra summary inside
    # -------------------------
    with st.expander("Full result (raw) — human readable"):
        # Recommendation + Metrics horizontally
        rec = result.get("recommendation", {})
        metrics = rec.get("metrics", {})
        rcol1, rcol2 = st.columns([2, 1])
        with rcol1:
            st.markdown("### Recommendation")
            st.write(f"**{rec.get('headline','')}**")
            st.write(rec.get("summary",""))
            st.markdown("**Actions**")
            for a in rec.get("actions", []):
                st.write(f"- {a}")
        with rcol2:
            st.markdown("### Key Metrics")
            for k, v in metrics.items():
                st.write(f"- **{k.replace('_',' ').title()}:** {v}")

        st.markdown("---")
        st.markdown("### Roadmap (Phases)")
        phases = roadmap.get("phases", [])
        if phases:
            cols_ph = st.columns(len(phases))
            for i, ph in enumerate(phases):
                with cols_ph[i]:
                    st.write(f"**{ph.get('phase','Phase')}**")
                    st.write(f"- {ph.get('months','—')} months")
                    if ph.get("notes"):
                        st.write(f"- {ph.get('notes')}")
        else:
            st.write("No roadmap phases available.")

        st.markdown("### Per-Plant Schedule")
        sched = roadmap.get("per_plant_schedule", [])
        if sched:
            st.table(pd.DataFrame(sched))
        else:
            st.write("Schedule unavailable.")

        st.markdown("---")
        st.markdown("### Decision Rationale")
        for b in result.get("rationale", {}).get("bullets", []):
            st.write(f"- {b}")

        st.markdown("---")
        st.markdown("### Infrastructure Summary (Ports | Energy)")
        cols_ir = st.columns(2)
        with cols_ir[0]:
            st.markdown("#### Ports")
            if ports:
                for k, v in ports.items():
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
            else:
                st.write("No port data.")
        with cols_ir[1]:
            st.markdown("#### Energy")
            if energy:
                for k, v in energy.items():
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
            else:
                st.write("No energy data.")
