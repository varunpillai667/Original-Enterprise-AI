# =========================
# File: app.py
# =========================
import streamlit as st
from decision_engine import run_simulation

st.set_page_config(layout="wide", page_title="Enterprise AI – Group X Strategic Simulator")

# Introduction
st.title("Enterprise AI – Group X Strategic Simulator")
st.markdown(
    """
    <div style="font-size:16px; line-height:1.4; margin-bottom:12px;">
    This simulation models how Enterprise Managers (EMs) and the Group Manager coordinate upgrades across Group X’s assets.
    Local nodes report to EMs; EMs connect to company systems; the Group Manager integrates at enterprise level.
    The model considers steel plants, ports and power plants together with operational and external factors.
    <br><br>
    All calculations are based on assumed data for demonstration purposes.
    </div>
    """,
    unsafe_allow_html=True
)

# Strategic Query
default_query = (
    "How can Group X increase steel production by approximately 2 MTPA in a reasonable time, "
    "and what is the expected timeline for recovering the investment?"
)
st.subheader("Strategic Query")
query = st.text_area("Enter your high-level strategic query", value=default_query, height=120)

# Run button and enlarged info text (human readable, next to button)
col_btn, col_info = st.columns([0.26, 1])
with col_btn:
    if st.button("Run Simulation"):
        result = run_simulation(query)
        st.session_state["result"] = result

with col_info:
    st.markdown(
        """
        <div style="font-size:16px; color:#1f2937; background:#f4f6f8; padding:10px; border-radius:6px;">
        <strong>Note:</strong> Clicking <strong>Run Simulation</strong> triggers automatic gathering of required internal
        and external operational, infrastructure, supply-chain and market-risk data, and produces a complete, end-to-end
        recommendation and implementation roadmap tailored to your query.
        </div>
        """,
        unsafe_allow_html=True
    )

# Display results
if "result" in st.session_state:
    result = st.session_state["result"]

    rec = result["recommendation"]
    roadmap = result["roadmap"]
    rationale = result["rationale"]

    st.header("Recommendation")
    st.subheader(rec["headline"])
    st.write(rec["summary"])

    metrics = rec["metrics"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Added Capacity (MTPA)", f"{metrics['added_mtpa']:.3f}")
    c2.metric("Investment (USD)", f"${metrics['investment_usd']:,}")
    c3.metric("Estimated Payback (months)", metrics["estimated_payback_months"])
    c4.metric("Project Timeline (months)", metrics["project_timeline_months"])
    c5.metric("Confidence", f"{metrics['confidence_pct']}%")

    st.divider()

    st.subheader("Key Recommendations (Full Program Steps)")
    for i, step in enumerate(rec["key_recommendations"], start=1):
        with st.expander(f"{i}. {step['step']}"):
            st.markdown(f"**Owner:** {step['owner']}")
            st.markdown(f"**Estimated duration:** {step['duration_months']} months")
            st.markdown("**Details:**")
            for d in step.get("details", []):
                st.markdown(f"- {d}")
            if step.get("plants_in_scope"):
                st.markdown("**Plants in scope:** " + ", ".join(step["plants_in_scope"]))

    st.divider()

    st.subheader("Per-Plant Upgrade Specifications")
    for p in rec["per_plant_upgrades"]:
        with st.expander(f"{p['plant_name']} — add {p['added_mtpa']} MTPA"):
            st.markdown(f"- Current capacity (tpa): {p['current_capacity_tpa']:,}")
            st.markdown(f"- Added capacity (tpa): {p['added_tpa']:,}")
            st.markdown(f"- Total CAPEX (USD): ${p['capex_total_usd']:,}")
            st.markdown(f"- Estimated payback (months): {p['estimated_payback_months']}")
            st.markdown("- Hiring estimate:")
            st.write(p['hiring_estimate'])
            st.markdown("- Upgrade scope:")
            for u in p['upgrade_scope']:
                st.markdown(f"  - {u}")
            st.markdown("- CAPEX breakdown:")
            for k,v in p['capex_breakdown_usd'].items():
                st.markdown(f"  - {k}: ${v:,}")
            st.markdown(f"- Schedule (months): {p['schedule_months']}")

    st.divider()

    st.subheader("Roadmap (Phases)")
    phases = roadmap.get("phases", [])
    if phases:
        cols = st.columns(len(phases))
        for col, ph in zip(cols, phases):
            col.markdown(f"**{ph['phase']}**")
            col.markdown(f"Duration: {ph['months']} months")

    st.divider()

    st.subheader("Decision Rationale — explanation for every recommendation")
    for b in rationale.get("bullets", []):
        st.write(f"- {b}")

    st.success("Complete recommendation and roadmap generated.")
