# app.py
import streamlit as st
import pandas as pd
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# ------------------------
# Full Intro / Operating Principles (restored)
# ------------------------
st.markdown(
    """
**Group X** has three subsidiaries — **Ports (4 ports)**, **Steel (4 plants)**, and **Energy (3 power plants)**.  
All simulation results in this prototype are based on **assumed, simplified data only** and are provided purely for demonstration.

### Operating Principles

**LOCAL Nodes — Site Layer**  
LOCAL Nodes are deployed at every port, steel plant, and power plant. They collect, buffer, validate, and securely transmit operational data (from SCADA, MES, TOS, DCS) **only to their own company’s Enterprise Manager (EM)**. LOCAL Nodes remain lightweight and do **not** perform analytics.

**Enterprise Managers (EMs) — Company Layer**  
Each subsidiary has a dedicated Enterprise Manager:
- **Ports EM** — collects data from all port LOCAL Nodes and connects to port-level systems (TOS, VTMS, PCS).  
- **Steel EM** — collects data from all steel plant LOCAL Nodes and connects to MES, quality systems, and the steel company ERP.  
- **Energy EM** — collects data from all power plant LOCAL Nodes and connects to SCADA/DCS and energy management systems.

**Group Manager — Group Layer**  
The Group Manager sits at Group X headquarters and integrates outputs from all EMs and group-level systems (treasury, ESG, planning). It runs cross-company simulations, resource allocation, and strategic scenario analysis. Every strategic query is **fully visible, explainable, and auditable**.

**Purpose:** This prototype demonstrates architecture and decision flow; all values are illustrative.
"""
)

st.markdown("---")

# ------------------------
# Strategic Query
# ------------------------
st.subheader("Strategic Query")
st.write("Enter a high-level strategic question. The default example is pre-filled.")

query = st.text_area(
    "Enter strategic query here",
    value=(
        "Increase total steel production by 2 MTPA within the next 15 months, "
        "allocating the capacity increase appropriately across all steel plants. "
        "Ensure that the investments required for this upgrade can be recovered "
        "within a payback period of less than 3 years."
    ),
    height=120,
)

# ------------------------
# Run Simulation
# ------------------------
if st.button("Run Simulation"):
    if not query.strip():
        st.error("Please enter a strategic query.")
    else:
        with st.spinner("Running simulation…"):
            result = run_simulation(query)

        if not result:
            st.error("Simulation did not return any result.")
        else:

            # --------------------------
            # Section 1: Recommendation
            # --------------------------
            st.header("Recommendation")

            rec = result["recommendation"]
            st.subheader(rec["headline"])
            st.write(rec["summary"])

            metrics = rec["metrics"]
            cols = st.columns(4)
            cols[0].metric("Added (MTPA)", metrics["added_mtpa"])
            cols[1].metric("Investment (USD)", f"${metrics['investment_usd']:,}")
            cols[2].metric("Payback (months)", metrics["estimated_payback_months"])
            cols[3].metric("Confidence", f"{metrics['confidence_pct']}%")

            # Debug info
            debug_lines = result.get("notes", {}).get("debug", [])
            if debug_lines:
                with st.expander("Debug / data-loading notes"):
                    for line in debug_lines:
                        st.write(f"- {line}")

            st.markdown("---")

            # --------------------------
            # Section 2: Roadmap
            # --------------------------
            st.header("Roadmap")

            roadmap = result["roadmap"]
            st.subheader("Phases")
            for ph in roadmap["phases"]:
                st.write(f"- **{ph['phase']}** ({ph['months']} months): {ph['notes']}")

            st.subheader("Per-plant actions")
            for a in roadmap["per_plant_actions"]:
                st.write(f"- {a}")

            st.markdown("---")

            # --------------------------
            # Section 3: Decision Rationale
            # --------------------------
            st.header("Decision Rationale")

            rationale = result["rationale"]
            st.subheader("Why this recommendation?")
            for b in rationale["bullets"]:
                st.write(f"- {b}")

            st.subheader("Key assumptions")
            assump = rationale["assumptions"]
            st.write(f"- CAPEX per MTPA: ${assump['capex_per_mtpa_usd']:,}")
            st.write(f"- Margin per tonne: ${assump['margin_per_ton_usd']:,}")
            st.write(f"- Energy per MTPA: {assump['mw_per_mtpa']} MW")

            st.subheader("Reference documents")
            refs = rationale["references"]
            st.write(f"- Operational Flow: `{refs['operational_flow_doc']}`")
            st.write(f"- Concept PDF: `{refs['concept_pdf']}`")

            st.markdown("---")

            # --------------------------
            # Per-plant Financial Table
            # --------------------------
            st.subheader("Per-Plant Financials")

            dist = result["em_summaries"]["steel_info"]["plant_distribution"]
            df = pd.DataFrame(dist)

            df["capex_usd"] = df["capex_usd"].apply(lambda x: f"${x:,}")
            df["annual_margin_usd"] = df["annual_margin_usd"].apply(lambda x: f"${x:,}")

            st.table(df)

            st.markdown("---")

            with st.expander("Full result (raw)"):
                st.json(result)
