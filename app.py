# app.py
import streamlit as st
import pandas as pd
import json
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# ---------------------------------------------------------
# FULL INTRO (RESTORED)
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

# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
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
        # keep two decimals for floats
        return round(v, 2)
    return v

def pretty_infra(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a version of infrastructure numbers formatted for display.
    (Numbers are rounded / humanized; structure left intact.)
    """
    out = {}
    for section, vals in (data or {}).items():
        if isinstance(vals, dict):
            out[section] = {}
            for k, v in vals.items():
                # if nested dict (older variants), format inner values too
                if isinstance(v, dict):
                    out[section][k] = {kk: nice_number(vv) for kk, vv in v.items()}
                else:
                    out[section][k] = nice_number(v)
        else:
            out[section] = vals
    return out

# ---------------------------------------------------------
# Strategic Query
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# Run simulation
# ---------------------------------------------------------
if st.button("Run Simulation"):

    if not query.strip():
        st.error("Please enter a query.")
        st.stop()

    with st.spinner("Simulating..."):
        try:
            result = run_simulation(query)
        except Exception as e:
            st.error(str(e))
            st.stop()

    # ---------------------------------------------------------
    # Recommendation
    # ---------------------------------------------------------
    rec = result.get("recommendation", {})
    st.header("Recommendation")
    st.subheader(rec.get("headline", ""))

    if rec.get("summary"):
        st.write(rec["summary"])

    metrics = rec.get("metrics", {})
    cols = st.columns(4)
    cols[0].metric("Added (MTPA)", metrics.get("added_mtpa", "—"))
    cols[1].metric("Investment (USD)", f"${metrics.get('investment_usd',0):,}")
    cols[2].metric("Payback (months)", metrics.get("estimated_payback_months", "—"))
    cols[3].metric("Confidence", f"{result.get('confidence_pct','—')}%")

    if rec.get("actions"):
        st.subheader("Key Recommended Actions")
        for a in rec["actions"][:8]:
            st.write(f"- {a}")

    # Debug logs
    debug = result.get("notes", {}).get("debug", [])
    if debug:
        with st.expander("Debug Notes"):
            for d in debug:
                st.write(f"- {d}")

    st.markdown("---")

    # ---------------------------------------------------------
    # ROADMAP (FULLY RESTORED)
    # ---------------------------------------------------------
    st.header("Roadmap")
    roadmap = result.get("roadmap", {})

    # Phase timeline
    st.subheader("Phases")
    for phase in roadmap.get("phases", []):
        st.write(f"**{phase['phase']}** — {phase['months']} months")
        note = phase.get("notes")
        if note:
            st.write(f"• {note}")

    # ------------------ PER-PLANT SCHEDULE (FIXED) ------------------
    st.subheader("Per-Plant Schedule")
    # Try to find an explicit per_plant_schedule in roadmap
    per_plant_schedule = roadmap.get("per_plant_schedule")
    if per_plant_schedule and isinstance(per_plant_schedule, list) and len(per_plant_schedule) > 0:
        st.table(pd.DataFrame(per_plant_schedule))
    else:
        # Derive schedule if missing: use em_summaries plant_distribution and implementation_timeline
        plant_dist = (result.get("em_summaries", {}) .get("steel_info", {}) .get("plant_distribution", []))
        impl_timeline = result.get("implementation_timeline") or result.get("implementation", {}) or {}
        # Fallback sensible defaults
        procurement_months_total = int(impl_timeline.get("procurement_months", impl_timeline.get("procurement", 2) or 2))
        implementation_months_total = int(impl_timeline.get("implementation_months", impl_timeline.get("implementation", 6) or 6))
        commissioning_months_total = int(impl_timeline.get("commissioning_months", impl_timeline.get("commissioning", 2) or 2))

        if plant_dist:
            # sort by added_tpa descending so largest plants go first
            sorted_plants = sorted(plant_dist, key=lambda x: x.get("added_tpa", 0), reverse=True)
            derived = []
            offset = 0
            total_added = sum(p.get("added_tpa", 0) for p in sorted_plants) or 1
            for p in sorted_plants:
                share = p.get("added_tpa", 0) / total_added if total_added else 1/len(sorted_plants)
                proc_months = max(1, int(round(procurement_months_total * share)))
                impl_months = max(1, int(round(implementation_months_total * share)))
                comm_months = max(1, int(round(commissioning_months_total * share)))
                start_month = offset + 1
                online_month = start_month + proc_months + impl_months + comm_months
                derived.append({
                    "plant": p.get("name", p.get("id", "")),
                    "start_month_planning": start_month,
                    "procurement_window_months": proc_months,
                    "implementation_window_months": impl_months,
                    "commissioning_window_months": comm_months,
                    "expected_online_month": online_month
                })
                # stagger next plant to avoid concurrency
                offset += max(1, int(round(impl_months * 0.5)))
            st.table(pd.DataFrame(derived))
        else:
            st.write("Schedule unavailable.")

    st.markdown("---")

    # ---------------------------------------------------------
    # RATIONALE (no assumptions, no documents)
    # ---------------------------------------------------------
    st.header("Decision Rationale")
    st.subheader("Why these recommendations?")
    for b in result.get("rationale", {}).get("bullets", []):
        st.write(f"- {b}")

    st.markdown("---")

    # ---------------------------------------------------------
    # PER-PLANT FINANCIALS (with cleaned hiring view)
    # ---------------------------------------------------------
    st.subheader("Per-Plant Financials")
    plant_dist = (
        result.get("em_summaries", {})
        .get("steel_info", {})
        .get("plant_distribution", [])
    )

    if plant_dist:
        df = pd.DataFrame(plant_dist)

        if "hiring_estimate" in df.columns:
            hires = df["hiring_estimate"].apply(parse_hiring)
            hires_df = pd.DataFrame(list(hires))
            df = pd.concat([df.drop(columns=["hiring_estimate"]), hires_df], axis=1)

        # Format currency
        if "capex_usd" in df.columns:
            df["capex_usd"] = df["capex_usd"].apply(lambda x: f"${x:,}")
        if "annual_margin_usd" in df.columns:
            df["annual_margin_usd"] = df["annual_margin_usd"].apply(lambda x: f"${x:,}")

        st.table(df)
    else:
        st.write("No plant data.")

    st.markdown("---")

    # ---------------------------------------------------------
    # INFRASTRUCTURE (clean, non-JSON view)
    # ---------------------------------------------------------
    st.subheader("Infrastructure Analysis (Ports & Energy)")

    infra = pretty_infra(result.get("infrastructure_analysis", {}))

    # PORTS
    ports = infra.get("ports", {})
    if ports:
        st.markdown("### Ports")
        # order keys for nicer presentation if present
        preferred_order = ["total_port_capacity_tpa", "used_port_tpa", "group_port_share_tpa", "spare_port_tpa", "available_port_for_steel_tpa", "port_throughput_required_tpa"]
        for key in preferred_order:
            if key in ports:
                label = key.replace("_", " ").title()
                st.write(f"- **{label}:** {ports[key]}")
        # write remaining keys if any
        for k, v in ports.items():
            if k not in preferred_order:
                label = k.replace("_", " ").title()
                st.write(f"- **{label}:** {v}")

    # ENERGY
    energy = infra.get("energy", {})
    if energy:
        st.markdown("### Energy")
        preferred_energy_order = ["total_energy_capacity_mw", "used_energy_mw", "group_energy_share_mw", "spare_energy_mw", "available_energy_for_steel_mw", "energy_required_mw"]
        for key in preferred_energy_order:
            if key in energy:
                label = key.replace("_", " ").title()
                st.write(f"- **{label}:** {energy[key]}")
        for k, v in energy.items():
            if k not in preferred_energy_order:
                label = k.replace("_", " ").title()
                st.write(f"- **{label}:** {v}")

    st.markdown("---")

    # ---------------------------------------------------------
    # Raw JSON
    # ---------------------------------------------------------
    with st.expander("Full result (raw)"):
        st.json(result)
