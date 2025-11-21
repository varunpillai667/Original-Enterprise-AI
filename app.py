# File: app.py
# Path: /mount/src/original-enterprise-ai/app.py
"""
Streamlit UI — improved per-plant hiring view and prettier infrastructure analysis output.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import json
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Intro (kept concise)
st.markdown(
    """
**Group X** has three subsidiaries — **Ports (4 ports)**, **Steel (4 plants)**, and **Energy (3 power plants)**.  
All simulation results in this prototype are based on **assumed, simplified data only** and are provided purely for demonstration.
"""
)
st.markdown("---")

# Utility helpers (display formatting)
def _safe_parse_hiring(x: Any) -> Dict[str, int]:
    """
    Return a dict with keys: engineers, maintenance, operators, project_managers.
    Accepts either dict or JSON-string; returns zeros for missing keys.
    """
    defaults = {"engineers": 0, "maintenance": 0, "operators": 0, "project_managers": 0}
    if x is None:
        return defaults
    if isinstance(x, dict):
        return {k: int(x.get(k, 0)) for k in defaults.keys()}
    if isinstance(x, str):
        try:
            parsed = json.loads(x)
            if isinstance(parsed, dict):
                return {k: int(parsed.get(k, 0)) for k in defaults.keys()}
        except Exception:
            pass
    return defaults

def _humanize_number(v: Any) -> Any:
    """
    Format ints with commas and floats to 2 decimals. Leave other types unchanged.
    """
    try:
        if isinstance(v, float):
            # represent large floats nicely
            return round(v, 2)
        if isinstance(v, int):
            return f"{v:,}"
    except Exception:
        pass
    return v

def _prettify_infra(infra: Dict[str, Any]) -> Dict[str, Any]:
    """
    Round and format infrastructure analysis numbers for display.
    """
    pretty: Dict[str, Any] = {}
    for group, data in (infra or {}).items():
        if not isinstance(data, dict):
            pretty[group] = data
            continue
        pretty[group] = {}
        for k, v in data.items():
            # nested dicts (e.g., ports -> nested stats)
            if isinstance(v, dict):
                pretty[group][k] = {}
                for kk, vv in v.items():
                    if isinstance(vv, (int, float)):
                        pretty[group][k][kk] = _humanize_number(vv)
                    else:
                        pretty[group][k][kk] = vv
            else:
                pretty[group][k] = _humanize_number(v)
    return pretty

# Strategic Query UI
st.subheader("Strategic Query")
query = st.text_area(
    "Enter strategic query here",
    value=(
        "Increase total steel production by 2 MTPA within the next 15 months, "
        "allocating the capacity increase appropriately across all steel plants. "
        "Ensure that the investments required for this upgrade can be recovered "
        "within a payback period of less than 3 years."
    ),
    height=140,
)

# Run Simulation button
if st.button("Run Simulation"):
    if not query.strip():
        st.error("Please enter a strategic query.")
    else:
        with st.spinner("Running simulation..."):
            try:
                result = run_simulation(query)
            except Exception as exc:
                st.error(f"Simulation error: {exc}")
                result = None

        if not result:
            st.error("Simulation returned no result.")
        else:
            # ---------------- Recommendation ----------------
            st.header("Recommendation")
            rec = result.get("recommendation", {})
            st.subheader(rec.get("headline", "Proposed action"))
            if rec.get("summary"):
                st.write(rec["summary"])

            metrics = rec.get("metrics", {})
            cols = st.columns(4)
            added_mtpa = metrics.get("added_mtpa", result.get("expected_increase_tpa", 0) / 1_000_000)
            cols[0].metric("Added (MTPA)", f"{added_mtpa}")
            invest = metrics.get("investment_usd", result.get("investment_usd", 0))
            cols[1].metric("Investment (USD)", f"${invest:,}")
            payback = metrics.get("estimated_payback_months", result.get("roi_months"))
            cols[2].metric("Est. Payback (months)", payback if payback is not None else "—")
            confidence = result.get("confidence_pct", None)
            cols[3].metric("Confidence", f"{confidence}%" if confidence is not None else "N/A")

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

            # ---------------- Roadmap ----------------
            st.header("Roadmap")
            roadmap = result.get("roadmap", {})
            phases = roadmap.get("phases", [])
            st.subheader("Phases")
            for ph in phases:
                ph_name = ph.get("phase", "Phase")
                ph_months = ph.get("months", "—")
                st.write(f"- **{ph_name}** ({ph_months} months)")
                acts = ph.get("activities") or ph.get("notes")
                if isinstance(acts, list):
                    for it in acts:
                        st.write(f"  - {it}")
                elif acts:
                    st.write(f"  - {acts}")

            st.subheader("Per-plant schedule")
            p_sched = roadmap.get("per_plant_schedule", [])
            if p_sched:
                st.table(pd.DataFrame(p_sched))
            else:
                st.write("Per-plant schedule not available.")

            st.markdown("---")

            # ---------------- Decision Rationale ----------------
            st.header("Decision Rationale")
            rationale = result.get("rationale", {})
            bullets = rationale.get("bullets", [])
            st.subheader("Why these recommendations?")
            for b in bullets:
                st.write(f"- {b}")

            st.markdown("---")

            # ------------- Per-Plant Financials (improved hiring view) -------------
            st.subheader("Per-Plant Financials (detailed)")
            steel_info = result.get("em_summaries", {}).get("steel_info", {})
            plant_dist = steel_info.get("plant_distribution", [])

            if plant_dist:
                df = pd.DataFrame(plant_dist)

                # Expand hiring_estimate into separate columns if present (dict or JSON string)
                if "hiring_estimate" in df.columns:
                    hires = df["hiring_estimate"].apply(_safe_parse_hiring).tolist()
                    hires_df = pd.DataFrame(hires, index=df.index)
                    # remove original column and concat expanded hires
                    df = df.drop(columns=["hiring_estimate"]).join(hires_df[["operators", "maintenance", "engineers", "project_managers"]])

                # Format currency-like columns
                if "capex_usd" in df.columns:
                    df["capex_usd"] = df["capex_usd"].apply(lambda x: f"${int(x):,}" if pd.notna(x) else x)
                if "annual_margin_usd" in df.columns:
                    df["annual_margin_usd"] = df["annual_margin_usd"].apply(lambda x: f"${int(x):,}" if pd.notna(x) else x)

                # Ensure column order: id, name, current_capacity_tpa, added_mtpa, added_tpa, capex, annual_margin, operators, maintenance, engineers, project_managers, payback_months
                cols_order = []
                for c in ["id", "name", "current_capacity_tpa", "added_mtpa", "added_tpa", "new_capacity_tpa", "capex_usd", "annual_margin_usd", "operators", "maintenance", "engineers", "project_managers", "payback_months"]:
                    if c in df.columns:
                        cols_order.append(c)
                df = df[cols_order]

                st.table(df)
            else:
                st.write("No per-plant breakdown available.")

            st.markdown("---")

            # ------------- Infrastructure analysis (pretty JSON) -------------
            st.subheader("Infrastructure Analysis (Ports & Energy)")
            infra = result.get("infrastructure_analysis", {})
            pretty_infra = _prettify_infra(infra)
            # Use st.json for collapsible view but with pretty/rounded numbers
            st.json(pretty_infra)

            st.markdown("---")

            # ------------- Full raw result -------------
            with st.expander("Full result (raw)"):
                st.json(result)
