# app.py
import streamlit as st
import pandas as pd
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Intro
st.markdown(
    """
**Group X** has three subsidiaries — **Ports (4 ports)**, **Steel (4 plants)**, and **Energy (3 power plants)**.  
All simulation results in this prototype are based on **assumed, simplified data only** and are provided purely for demonstration.

### Operating Principles

**LOCAL Nodes — Site Layer**  
LOCAL Nodes collect and forward operational data from each site (ports, steel plants, power plants) to their respective Enterprise Manager (EM). LOCAL Nodes do minimal processing.

**Enterprise Managers (EMs) — Company Layer**  
Each company (Ports, Steel, Energy) has an EM that aggregates local nodes and connects to company-level systems. EMs make company-level decisions and feed summary data to the Group Manager.

**Group Manager — Group Layer**  
The Group Manager aggregates EM outputs and group-level systems to run cross-company simulations and strategic queries. All strategic queries are explainable and auditable.

**Purpose:** Prototype demonstration; values are illustrative and based on assumed data.
"""
)

st.markdown("---")

# Strategic Query Input
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

# Run Simulation
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

            # --------------------------------------------------
            # Recommendation Section
            # --------------------------------------------------
            st.header("Recommendation")
            rec = result.get("recommendation", {})
            st.subheader(rec.get("headline", ""))

            if rec.get("summary"):
                st.write(rec["summary"])

            metrics = rec.get("metrics", {})
            cols = st.columns(4)

            cols[0].metric("Added (MTPA)", metrics.get("added_mtpa", 0))
            cols[1].metric("Investment (USD)", f"${metrics.get('investment_usd',0):,}")
            cols[2].metric("Est. Payback (months)", metrics.get("estimated_payback_months","—"))
            cols[3].metric("Confidence", f"{result.get('confidence_pct','N/A')}%")

            if rec.get("actions"):
                st.subheader("Key Recommended Actions")
                for a in rec.get("actions", [])[:6]:
                    st.write(f"- {a}")

            debug_lines = result.get("notes", {}).get("debug", [])
            if debug_lines:
                with st.expander("Debug Information"):
                    for d in debug_lines:
                        st.write(f"- {d}")

            st.markdown("---")

            # --------------------------------------------------
            # Roadmap Section
            # --------------------------------------------------
            st.header("Roadmap")
            roadmap = result.get("roadmap", {})
            phases = roadmap.get("phases", [])

            st.subheader("Phases")
            for ph in phases:
                st.write(f"- **{ph.get('phase')}** ({ph.get('months')} months)")
                acts = ph.get("activities") or ph.get("notes")
                if isinstance(acts, list):
                    for it in acts:
                        st.write(f"  - {it}")
                else:
                    st.write(f"  - {acts}")

            st.subheader("Per-Plant Schedule")
            if roadmap.get("per_plant_schedule"):
                st.table(pd.DataFrame(roadmap["per_plant_schedule"]))

            st.markdown("---")

            # --------------------------------------------------
            # Rationale Section (Assumptions + References REMOVED)
            # --------------------------------------------------
            st.header("Decision Rationale")

            rationale = result.get("rationale", {})
            bullets = rationale.get("bullets", [])

            st.subheader("Why These Recommendations?")
            for b in bullets:
                st.write(f"- {b}")

            # ⛔ Removed: Key Assumptions  
            # ⛔ Removed: Reference Documents

            st.markdown("---")

            # --------------------------------------------------
            # Per-Plant Financials
            # --------------------------------------------------
            st.subheader("Per-Plant Financials")
            plant_dist = result.get("em_summaries", {}).get("steel_info", {}).get("plant_distribution", [])

            if plant_dist:
                df = pd.DataFrame(plant_dist)
                if "capex_usd" in df.columns:
                    df["capex_usd"] = df["capex_usd"].apply(lambda x: f"${x:,}")
                if "annual_margin_usd" in df.columns:
                    df["annual_margin_usd"] = df["annual_margin_usd"].apply(lambda x: f"${x:,}")
                st.table(df)

            st.markdown("---")

            # --------------------------------------------------
            # Infrastructure Analysis
            # --------------------------------------------------
            st.subheader("Infrastructure Analysis (Ports & Energy)")
            st.json(result.get("infrastructure_analysis", {}))

            st.markdown("---")

            # --------------------------------------------------
            # Raw JSON Output
            # --------------------------------------------------
            with st.expander("Full result (raw)"):
                st.json(result)
