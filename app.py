# app.py
import streamlit as st
import pandas as pd
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Intro (kept concise)
st.markdown(
    """
**Group X**: Ports (4 ports), Steel (4 plants), Energy (3 power plants).  
All prototype outputs use **assumed, simplified data** for demonstration.
"""
)

st.markdown("---")

# Strategic query input
st.subheader("Strategic Query")
query = st.text_area(
    "Enter strategic query",
    value=(
        "Increase total steel production by 2 MTPA within the next 15 months, "
        "allocating the capacity increase appropriately across all steel plants. "
        "Ensure that the investments required for this upgrade can be recovered "
        "within a payback period of less than 3 years."
    ),
    height=120,
)
run_button = st.button("Run Simulation")

if run_button:
    if not query.strip():
        st.error("Enter a strategic query.")
    else:
        with st.spinner("Running simulation..."):
            try:
                result = run_simulation(query)
            except Exception as e:
                st.error(f"Simulation error: {e}")
                result = None

        if not result:
            st.warning("No result returned.")
        else:
            # Section 1: Recommendation
            st.header("Recommendation")
            rec = result.get("recommendation", {})
            st.subheader(rec.get("headline", "Proposed action"))
            st.write(rec.get("summary", ""))
            metrics = rec.get("metrics", {})
            cols = st.columns(4)
            cols[0].metric("Added (MTPA)", f"{metrics.get('added_mtpa', '—'):.3f}")
            cols[1].metric("Investment (USD)", f"${metrics.get('investment_usd', 0):,}")
            payback = metrics.get("estimated_payback_months")
            cols[2].metric("Est. Payback (months)", f"{payback if payback is not None else '—'}")
            cols[3].metric("Confidence", f"{metrics.get('confidence_pct', '—')}%")

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
            assumptions = rationale.get("assumptions", {})
            st.write(f"- CAPEX per 1 MTPA: ${assumptions.get('capex_per_mtpa_usd', '—'):,}")
            st.write(f"- Margin per tonne: ${assumptions.get('margin_per_ton_usd', '—')}")
            st.write(f"- Energy per 1 MTPA: {assumptions.get('mw_per_mtpa', '—')} MW")

            refs = rationale.get("references", {})
            if refs:
                st.write("")
                st.subheader("Reference documents")
                st.write(f"- Operational Flow (local path): {refs.get('operational_flow_doc')}")
                st.write(f"- Concept PDF (local path): {refs.get('concept_pdf')}")

            st.markdown("---")

            # Per-plant financials table (for transparency)
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
                df_display = df.copy()
                df_display["Current (tpa)"] = df_display["Current (tpa)"].map("{:,}".format)
                df_display["Added (tpa)"] = df_display["Added (tpa)"].map("{:,}".format)
                df_display["New (tpa)"] = df_display["New (tpa)"].map("{:,}".format)
                df_display["CAPEX (USD)"] = df_display["CAPEX (USD)"].map(lambda x: f"${x:,}")
                df_display["Annual Margin (USD)"] = df_display["Annual Margin (USD)"].map(lambda x: f"${x:,}")
                st.table(df_display)
            else:
                st.write("No plant distribution available.")

            # Full raw result (collapsible)
            with st.expander("Full result (raw)"):
                st.json(result)
