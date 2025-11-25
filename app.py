# File: app.py
import streamlit as st
from decision_engine import run_simulation

st.set_page_config(layout="wide", page_title="Enterprise AI – Group X Strategic Simulator")
st.title("Enterprise AI – Group X Strategic Simulator")

st.markdown(
    """
    <div style="font-size:16px; line-height:1.4; margin-bottom:12px;">
    This simulation models how Enterprise Managers (EMs) and the Group Manager coordinate upgrades across Group X’s assets.
    Local nodes report to EMs; EMs connect to company systems; the Group Manager integrates at enterprise level.
    The model considers steel plants, ports and power plants together with operational and external factors.
    <br><br>
    <em>All calculations are based on assumed data for demonstration purposes.</em>
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

# ------------------------
# Stock market controls
# ------------------------
st.markdown("**External factors** — optional")
include_stock = st.checkbox("Include stock market factor in simulation", value=False, help="Enable to model market-driven risk adjustments (margin erosion, capex inflation, confidence).")
stock_market_payload = None
if include_stock:
    col1, col2 = st.columns([1, 1])
    with col1:
        idx_change = st.number_input("Index change (%)", value=-5.0, step=0.5, help="Enter expected % change in major index (negative for decline).")
    with col2:
        volatility = st.selectbox("Volatility", options=["Low", "Medium", "High"], index=1, help="Higher volatility amplifies market impact.")
    stock_market_payload = {"index_change_pct": float(idx_change), "volatility": volatility}

# Run Simulation button + readable info (to the right)
col_btn, col_info = st.columns([0.26, 1])
with col_btn:
    if st.button("Run Simulation"):
        result = run_simulation(query, stock_market=stock_market_payload)
        st.session_state["result"] = result

with col_info:
    st.markdown(
        """
        <div style="font-size:16px; color:#1f2937; background:#f4f6f8; padding:10px; border-radius:6px;">
        <strong>Note:</strong> Clicking <strong>Run Simulation</strong> automatically gathers required internal and external
        operational, infrastructure, supply-chain, and market-risk data (demo assumptions), then produces a tailored, end-to-end recommendation and roadmap.
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

if "result" in st.session_state:
    result = st.session_state["result"]

    rec = result["recommendation"]
    roadmap = result["roadmap"]
    rationale = result["rationale"]
    stock_info = result.get("stock_market_assumptions", {})

    # Header metrics
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

    # Show stock market assumptions if used
    if stock_info.get("applied"):
        st.subheader("Stock Market Assumptions & Impact")
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.markdown(f"- Index change: **{stock_info['index_change_pct']}%**")
            st.markdown(f"- Volatility: **{stock_info['volatility']}**")
        with col_b:
            st.markdown("**Impact summary:**")
            st.markdown(f"- Market shock index: **{stock_info['market_shock']}**")
            st.markdown(f"- Margin down adjustment applied: **{stock_info['add_margin_down']:+.4f}**")
            st.markdown(f"- Capex inflation adjustment applied: **{stock_info['add_capex_inflation']:+.4f}**")
            st.markdown(f"- Confidence penalty applied: **{stock_info['confidence_penalty']} pts**")
            st.markdown(f"- Reason: {stock_info['reason']}")

        st.divider()

    # Key recommendations
    st.subheader("Key Recommendations")
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

    # Per-plant upgrades — clean, no JSON/code blocks
    st.subheader("Per-Plant Upgrade Specifications")
    for p in rec["per_plant_upgrades"]:
        with st.expander(f"{p['plant_name']} — add {p['added_mtpa']} MTPA"):
            st.markdown(f"**Current capacity:** {p['current_capacity_tpa']:,} tpa")
            st.markdown(f"**Added capacity:** {p['added_tpa']:,} tpa")
            st.markdown(f"**Total CAPEX:** ${p['capex_total_usd']:,}")
            st.markdown(f"**Estimated payback:** {p['estimated_payback_months']} months")

            st.markdown("**Hiring estimate:**")
            hires = p.get("hiring_estimate", {})
            st.markdown(f"- Engineers: {hires.get('engineers', 0)}  ")
            st.markdown(f"- Maintenance: {hires.get('maintenance', 0)}  ")
            st.markdown(f"- Operators: {hires.get('operators', 0)}  ")
            st.markdown(f"- Project managers: {hires.get('project_managers', 0)}  ")

            st.markdown("**Upgrade scope:**")
            for u in p.get("upgrade_scope", []):
                st.markdown(f"- {u}")

            st.markdown("**CAPEX breakdown:**")
            for k, v in p.get("capex_breakdown_usd", {}).items():
                st.markdown(f"- {k}: ${v:,}")

            st.markdown("**Schedule (months):**")
            sched = p.get("schedule_months", {})
            st.markdown(f"- Procurement: {sched.get('procurement_months','—')} months  ")
            st.markdown(f"- Implementation: {sched.get('implementation_months','—')} months  ")
            st.markdown(f"- Commissioning: {sched.get('commissioning_months','—')} months  ")
            st.markdown(f"- Expected online: {sched.get('expected_time_to_online_months','—')} months  ")

    st.divider()

    # Roadmap horizontally
    st.subheader("Roadmap (Phases)")
    phases = roadmap.get("phases", [])
    if phases:
        cols = st.columns(len(phases))
        for col, ph in zip(cols, phases):
            col.markdown(f"**{ph['phase']}**")
            col.markdown(f"Duration: {ph['months']} months")

    st.divider()

    # Decision rationale
    st.subheader("Decision Rationale — explanation for every recommendation")
    for b in rationale.get("bullets", []):
        st.markdown(f"- {b}")

    st.success("Complete recommendation and roadmap generated.")
