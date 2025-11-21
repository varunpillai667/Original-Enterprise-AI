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
- **Steel EM** — collects data from all steel plant LOCAL Nodes and connects to MES, quality systems, and the company ERP at the steel company office.
- **Energy EM** — collects data from all power plant LOCAL Nodes and connects to SCADA/DCS and energy management systems.

Each EM combines LOCAL Node data with company-level systems (ERP, CRM, MES, HRMS) to run forecasting, optimization, and company-level decision-making while keeping companies **logically separated**.

**Group Manager — Group Layer**  
The Group Manager sits at Group X headquarters and integrates outputs from all EMs and group-level systems (treasury, ESG, planning). It runs cross-company simulations, resource allocation, and strategic scenario analysis. Every strategic query at this layer is **fully visible, explainable, and auditable**.

**Purpose:** This prototype demonstrates architecture and decision flow; all values are illustrative.
"""
)

st.markdown("---")

# ------------------------
# Strategic Query (kept visible and framed as requested)
# ------------------------
st.subheader("Strategic Query")
st.write(
    "Enter a high-level strategic question for Group X. Example shown is prefilled with the approved query."
)
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

# Run Simulation button
col_run, _ = st.columns([1, 6])
with col_run:
    run_button = st.button("Run Simulation")

# ------------------------
# Simulation output area
# ------------------------
if run_button:
    if not query.strip():
        st.error("Please enter a strategic query before running the simulation.")
    else:
        with st.spinner("Running simulation and aggregating EM outputs..."):
            try:
                result = run_simulation(query)
            except Exception as exc:
                st.error(f"Simulation failed: {exc}")
                result = None

        if not result:
            st.warning("No result returned from simulation. Check logs or inputs.")
        else:
            # Section 1: Recommendation
            st.header("Recommendation")
            rec = result.get("recommendation", {})
            st.subheader(rec.get("headline", "Proposed action"))
            if rec.get("summary"):
                st.write(rec["summary"])

            metrics = rec.get("metrics", {})
            mcols = st.columns(4)
            # Safely format metrics
            added_mtpa = metrics.get("added_mtpa")
            invest = metrics.get("investment_usd", 0)
            payback = metrics.get("estimated_payback_months")
            confidence = metrics.get("confidence_pct", result.get("confidence_pct", "—"))

            mcols[0].metric("Added (MTPA)", f"{added_mtpa:.3f}" if isinstance(added_mtpa, float) else (str(added_mtpa) if added_mtpa is not None else "—"))
            mcols[1].metric("Investment (USD)", f"${invest:,}" if isinstance(invest, (int, float)) else "—")
            mcols[2].metric("Est. Payback (months)", f"{payback}" if payback is not None else "—")
            mcols[3].metric("Confidence", f"{confidence}%")

            st.markdown("---")

            # Section 2: Roadmap
            st.header("Roadmap")
            roadmap = result.get("roadmap", {})
            st.subheader("Phases")
            for ph in roadmap.get("phases", []):
                st.write(f"- **{ph['phase']}** ({ph['months']} months): {ph['notes']}")
            st.subheader("Per-plant actions")
            for act in roadmap.get("per_plant_actions", []):
                st.write(f"- {act}")

            st.markdown("---")

            # Section 3: Decision Rationale
            st.header("Decision Rationale")
            rationale = result.get("rationale", {})
            st.subheader("Why this recommendation?")
            for b in rationale.get("bullets", []):
                st.write(f"- {b}")

            st.subheader("Key assumptions")
            assump = rationale.get("assumptions", {})
            # defensive formatting
            capex_ass = assump.get("capex_per_mtpa_usd", result.get("notes", {}).get("assumptions", {}).get("capex_per_mtpa_usd"))
            margin_ass = assump.get("margin_per_ton_usd", result.get("notes", {}).get("assumptions", {}).get("margin_per_ton_usd"))
            mw_ass = assump.get("mw_per_mtpa", result.get("notes", {}).get("assumptions", {}).get("mw_per_mtpa"))
            if capex_ass is not None:
                st.write(f"- CAPEX per 1 MTPA: ${capex_ass:,}")
            else:
                st.write("- CAPEX per 1 MTPA: —")
            st.write(f"- Margin per tonne: ${margin_ass if margin_ass is not None else '—'}")
            st.write(f"- Energy per 1 MTPA: {mw_ass if mw_ass is not None else '—'} MW")

            refs = rationale.get("references", {})
            if refs:
                st.write("")
                st.subheader("Reference documents")
                # display local paths (these are uploaded file paths)
                op_doc = refs.get("operational_flow_doc") or "/mnt/data/Operational Flow.docx"
                pdf_doc = refs.get("concept_pdf") or "/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf"
                st.write(f"- Operational Flow (uploaded): `{op_doc}`")
                st.write(f"- Concept PDF (uploaded): `{pdf_doc}`")

            st.markdown("---")

            # Per-plant financials (detailed)
            st.subheader("Per-Plant Financials (detailed)")
            steel_info = result.get("em_summaries", {}).get("steel_info", {})
            distribution = steel_info.get("plant_distribution", [])
            if distribution:
                rows = []
                for p in distribution:
                    rows.append({
                        "Plant": p.get("name", p.get("id", "")),
                        "Current (tpa)": int(p.get("current_capacity_tpa", 0)),
                        "Added (tpa)": int(p.get("added_tpa", 0)),
                        "New (tpa)": int(p.get("new_capacity_tpa", 0)),
                        "CAPEX (USD)": int(p.get("capex_usd", 0)),
                        "Annual Margin (USD)": int(p.get("annual_margin_usd", 0)),
                        "Payback (months)": p.get("payback_months", None),
                    })
                df = pd.DataFrame(rows)
                # format for readability
                df_display = df.copy()
                df_display["Current (tpa)"] = df_display["Current (tpa)"].map("{:,}".format)
                df_display["Added (tpa)"] = df_display["Added (tpa)"].map("{:,}".format)
                df_display["New (tpa)"] = df_display["New (tpa)"].map("{:,}".format)
                df_display["CAPEX (USD)"] = df_display["CAPEX (USD)"].map(lambda x: f"${x:,}")
                df_display["Annual Margin (USD)"] = df_display["Annual Margin (USD)"].map(lambda x: f"${x:,}")
                st.table(df_display)
            else:
                st.write("No plant distribution available.")

            st.markdown("---")
            with st.expander("Full result (raw)"):
                st.json(result)
