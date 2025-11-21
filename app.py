# app.py
import streamlit as st
import pandas as pd
import json
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Intro
st.markdown(
    """
### Introduction

**Group X** operates **4 ports**, **4 steel plants**, and **3 power plants**.  
All simulation results in this prototype are based on **assumed, simplified data only**, used only for conceptual demonstration.

### Operating Principles
LOCAL Nodes -> Enterprise Managers (EMs) -> Group Manager.
"""
)
st.markdown("---")

# helpers
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
        return round(v,2)
    return v

def pretty_infra(data: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for section, vals in (data or {}).items():
        if isinstance(vals, dict):
            out[section] = {k: nice_number(v) for k, v in vals.items()}
        else:
            out[section] = vals
    return out

# Query
st.subheader("Strategic Query")
query = st.text_area("Enter strategic query", value=("Increase total steel production by 2 MTPA within the next 15 months, allocating appropriately and ensuring payback under 3 years."), height=140)

if st.button("Run Simulation"):
    if not query.strip():
        st.error("Enter a query")
        st.stop()

    with st.spinner("Running simulation..."):
        try:
            result = run_simulation(query)
        except Exception as exc:
            st.error(f"Simulation error: {exc}")
            st.stop()

    # Recommendation
    rec = result.get("recommendation", {})
    st.header("Recommendation")
    st.subheader(rec.get("headline", "Proposed action"))
    if rec.get("summary"):
        st.write(rec["summary"])

    metrics = rec.get("metrics", {})
    cols = st.columns(4)
    cols[0].metric("Added (MTPA)", metrics.get("added_mtpa", "—"))
    cols[1].metric("Investment (USD)", f"${metrics.get('investment_usd',0):,}")
    cols[2].metric("Est. Payback (months)", metrics.get("estimated_payback_months","—"))
    cols[3].metric("Confidence", f"{result.get('confidence_pct','—')}%")

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

    # Roadmap: show phases horizontally
    st.header("Roadmap")
    roadmap = result.get("roadmap", {})
    phases = roadmap.get("phases", [])

    if phases:
        cols_ph = st.columns(len(phases))
        for i, ph in enumerate(phases):
            with cols_ph[i]:
                months = ph.get("months", ph.get("duration_months", "—"))
                st.subheader(ph.get("phase", f"Phase {i+1}"))
                st.write(f"**Duration:** {months} months")
                if ph.get("notes"):
                    st.write(f"- {ph.get('notes')}")
    else:
        st.write("No roadmap phases available.")

    # Per-plant schedule
    st.subheader("Per-Plant Schedule")
    p_sched = roadmap.get("per_plant_schedule", [])
    if p_sched:
        st.table(pd.DataFrame(p_sched))
    else:
        plant_dist = result.get("em_summaries", {}).get("steel_info", {}).get("plant_distribution", [])
        if plant_dist:
            total_added = sum(p.get("added_tpa",0) for p in plant_dist) or 1
            derived=[]
            offset=0
            procurement_total = result.get("metrics", {}).get("estimated_payback_months", 2) or 2
            implementation_total = result.get("implementation_timeline", {}).get("implementation_months", 6) if result.get("implementation_timeline") else 6
            for p in sorted(plant_dist, key=lambda x: x.get("added_tpa",0), reverse=True):
                share = p.get("added_tpa",0)/total_added
                proc=max(1,int(round(2*share)))
                impl=max(1,int(round(6*share)))
                comm=1
                start=offset+1
                online=start+proc+impl+comm
                derived.append({"plant":p.get("name"),"start_month":start,"procurement_months":proc,"implementation_months":impl,"commissioning_months":comm,"expected_online_month":online})
                offset += max(1,int(round(impl*0.5)))
            st.table(pd.DataFrame(derived))
        else:
            st.write("Schedule unavailable.")

    st.markdown("---")

    # Decision Rationale (richer)
    st.header("Decision Rationale")
    for b in result.get("rationale", {}).get("bullets", []):
        st.write(f"- {b}")

    st.markdown("---")

    # Per-plant financials
    st.subheader("Per-Plant Financials (detailed)")
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
        st.table(df)
    else:
        st.write("No plant data available.")

    st.markdown("---")

    # Infrastructure Analysis: ports & energy side-by-side
    st.subheader("Infrastructure Analysis (Ports & Energy)")
    infra = pretty_infra(result.get("infrastructure_analysis", {}))
    ports = infra.get("ports", {})
    energy = infra.get("energy", {})

    col_left, col_right = st.columns(2)
    with col_left:
        if ports:
            st.markdown("#### Ports")
            preferred_order = ["total_port_capacity_tpa","used_port_tpa","group_port_share_tpa","spare_port_tpa","available_port_for_steel_tpa","port_throughput_required_tpa"]
            for k in preferred_order:
                if k in ports:
                    st.write(f"- **{k.replace('_',' ').title()}:** {ports[k]}")
            for k,v in ports.items():
                if k not in preferred_order:
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
        else:
            st.write("No port data.")

    with col_right:
        if energy:
            st.markdown("#### Energy")
            pref_e = ["total_energy_capacity_mw","used_energy_mw","group_energy_share_mw","spare_energy_mw","available_energy_for_steel_mw","energy_required_mw"]
            for k in pref_e:
                if k in energy:
                    st.write(f"- **{k.replace('_',' ').title()}:** {energy[k]}")
            for k,v in energy.items():
                if k not in pref_e:
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
        else:
            st.write("No energy data.")

    st.markdown("---")

    # Full result (human readable) - infra summary side-by-side
    with st.expander("Full result (raw)"):
        st.markdown("## Recommendation")
        st.write(f"**Headline:** {rec.get('headline','')}")
        st.write(f"**Summary:** {rec.get('summary','')}")

        st.markdown("### Metrics")
        for k,v in rec.get("metrics", {}).items():
            st.write(f"- **{k.replace('_',' ').title()}:** {v}")

        st.markdown("### Actions")
        for a in rec.get("actions", []):
            st.write(f"- {a}")

        st.markdown("---")
        st.markdown("## Roadmap (Phases)")
        phases = roadmap.get("phases", [])
        for ph in phases:
            months = ph.get("months", ph.get("duration_months","—"))
            st.write(f"- **{ph.get('phase','Phase')}** ({months} months): {ph.get('notes','')}")

        st.markdown("### Per-Plant Schedule")
        sched = roadmap.get("per_plant_schedule", [])
        if sched:
            st.table(pd.DataFrame(sched))
        else:
            st.write("Schedule unavailable.")

        st.markdown("---")
        st.markdown("## Decision Rationale")
        for b in result.get("rationale", {}).get("bullets", []):
            st.write(f"- {b}")

        st.markdown("---")
        st.markdown("## Infrastructure Summary")
        infra = pretty_infra(result.get("infrastructure_analysis", {}))
        ports = infra.get("ports", {})
        energy = infra.get("energy", {})

        cols_ir = st.columns(2)
        with cols_ir[0]:
            st.markdown("### Ports")
            if ports:
                for k,v in ports.items():
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
            else:
                st.write("No port data.")
        with cols_ir[1]:
            st.markdown("### Energy")
            if energy:
                for k,v in energy.items():
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
            else:
                st.write("No energy data.")
