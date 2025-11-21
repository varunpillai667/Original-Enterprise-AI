# app.py
import streamlit as st
import pandas as pd
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Full intro / Operating Principles restored
st.markdown(
    """
**Group X** has three subsidiaries — **Ports (4 ports)**, **Steel (4 plants)**, and **Energy (3 power plants)**.  
All simulation results in this prototype are based on **assumed, simplified data only** and are provided purely for demonstration.

### Operating Principles

**LOCAL Nodes — Site Layer**  
LOCAL Nodes collect and forward operational data from each site (ports, steel plants, power plants) to their respective Enterprise Manager (EM). LOCAL Nodes do minimal processing.

**Enterprise Managers (EMs) — Company Layer**  
Each company (Ports, Steel, Energy) has an EM that aggregates local nodes and connects to company-level systems (ERP, MES, SCADA). EMs make company-level decisions and feed summary data to the Group Manager.

**Group Manager — Group Layer**  
The Group Manager aggregates EM outputs and group-level systems to run cross-company simulations and strategic queries. All strategic queries are explainable and auditable.

**Purpose:** Prototype demonstration; values are illustrative and based on assumed data.
"""
)

st.markdown("---")

# Strategic Query
st.subheader("Strategic Query")
st.write("Enter a high-level strategic question. Default example is prefilled.")

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

# Run button
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
            # ==============================
            # Recommendation
            # ==============================
            st.header("Recommendation")
            rec = result.get("recommendation", {})
            st.subheader(rec.get("headline", "Proposed action"))
            if rec.get("summary"):
                st.write(rec["summary"])

            metrics = rec.get("metrics", {})
            cols = st.columns(4)
            cols[0].metric("Added (MTPA)", metrics.get("added_mtpa", 0))
            cols[1].metric("Investment (USD)", f"${metrics.get('investment_usd',0):,}")

            payback = metrics.get("estimated_payback_months", "—")
            cols[2].metric("Est. Payback (months)", payback)

            confidence = result.get("confidence_pct", None)
            cols[3].metric("Confidence", f"{confidence}%" if confidence else "N/A")

            if rec.get("actions"):
                st.subheader("Key recommended actions")
                for a in rec.get("actions", [])[:6]:
                    st.write(f"- {a}")

            debug_lines = result.get("notes", {}).get("debug", [])
            if debug_lines:
                with st.expander("Debug / data-loading notes"):
                    for d in debug_lines:
                        st.write(f"- {d}")

            st.markdown("---")

            # ==============================
            # Roadmap
            # ==============================
            st.header("Roadmap")
            roadmap = result.get("roadmap", {})
            phases = roadmap.get("phases", [])

            st.subheader("Phases")
            for ph in phases:
                st.write(f"- **{ph.get('phase')}** ({ph.get('months','—')} months)")
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

            st.markdown("---")

            # ==============================
            # Rationale
            # ==============================
            st.header("Decision Rationale")

            rationale = result.get("rationale", {})
            bullets = rationale.get("bullets", [])

            st.subheader("Why these recommendations?")
            for b in bullets:
                st.write(f"- {b}")

            # REMOVED: Key assumptions section

            refs = rationale.get("references", {})
            if refs:
                st.subheader("Reference documents")
                st.write(f"- Operational Flow: `{refs.get('operational_flow_doc')}`")
                st.write(f"- Concept PDF: `{refs.get('concept_pdf')}`")

            st.markdown("---")

            # ==============================
            # Per-plant financials
            # ==============================
            st.subheader("Per-Plant Financials (detailed)")
            steel_info = result.get("em_summaries", {}).get("steel_info", {})
            plant_dist = steel_info.get("plant_distribution", [])

            if plant_dist:
                df = pd.DataFrame(plant_dist)
                if "capex_usd" in df.columns:
                    df["capex_usd"] = df["capex_usd"].apply(lambda x: f"${x:,}")
                if "annual_margin_usd" in df.columns:
                    df["annual_margin_usd"] = df["annual_margin_usd"].apply(lambda x: f"${x:,}")
                st.table(df)

            st.markdown("---")

            # Infrastructure analysis
            st.subheader("Infrastructure analysis (ports & energy)")
            st.json(result.get("infrastructure_analysis", {}))

            st.markdown("---")

            # Raw result
            with st.expander("Full result (raw)"):
                st.json(result)
