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

# Run Simulation button + readable info (to the right)
col_btn, col_info = st.columns([0.26, 1])
with col_btn:
    if st.button("Run Simulation"):
        result = run_simulation(query)
        st.session_state["result"] = result

with col_info:
    st.markdown(
        """
        <div style="font-size:16px; color:#1f2937; background:#f4f6f8; padding:10px; border-radius:6px;">
        <strong>Note:</strong> Clicking <strong>Run Simulation</strong> automatically gathers required internal and external
        operational, infrastructure, supply-chain, and market-risk data, then produces a tailored, end-to-end recommendation and roadmap.
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# Results display (unchanged layout, clean formatting)
if "result" in st.session_state:
    result = st.session_state["result"]

    rec = result["recommendation"]
    roadmap = result["roadmap"]
    rationale = result["rationale"]

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

    st.divider()

    # ============================
    # Export Options box (NEW)
    # ============================
    st.header("Export & Deliverables")
    st.markdown(
        """
        <div style="background:#f8fafc; padding:14px; border-radius:8px;">
        <strong>Choose export formats</strong> — select one or more options below and click <em>Generate</em>.
        <br><br>
        <em>Available export types:</em>
        <ul style="margin-top:6px;">
          <li><strong>PDF</strong> — one-page executive summary (board-ready)</li>
          <li><strong>Detailed Power BI report</strong> — deep-dive dataset and visuals for analysts</li>
          <li><strong>Excel</strong> — full tabular export for further analysis</li>
          <li><strong>Create process flow diagram</strong> — generate a process diagram of the simulation flow</li>
        </ul>
        <div style="margin-top:8px; color:#333;">
        <strong>Note:</strong> This is a demo. Clicking <em>Generate</em> will not produce any files — it will only simulate the export action and confirm selection.
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Interactive controls
    col_a, col_b = st.columns([1, 1])
    with col_a:
        export_pdf = st.checkbox("PDF — Executive summary")
        export_powerbi = st.checkbox("Power BI — Detailed report")
    with col_b:
        export_excel = st.checkbox("Excel — Full data export")
        export_flow = st.checkbox("Create process flow diagram")

    generate_clicked = st.button("Generate")

    if generate_clicked:
        # Build list of selected
        selections = []
        if export_pdf:
            selections.append("PDF (Executive summary)")
        if export_powerbi:
            selections.append("Power BI (Detailed report)")
        if export_excel:
            selections.append("Excel (Full data)")
        if export_flow:
            selections.append("Process flow diagram")

        if not selections:
            st.warning("No export format selected. Please select at least one option before clicking Generate.")
        else:
            # Demo behavior: do not produce files — show a clear message
            st.info(
                "Demo mode — export simulation\n\n"
                "You selected: " + ", ".join(selections) + ".\n\n"
                "This is a demonstration environment. Exports are disabled in demo mode and no files will be produced. "
                "In a production deployment, the system would generate the selected deliverables and provide download links here."
            )
            # Provide the uploaded Operational Flow doc path as reference (system will convert this path to a URL in your environment)
            st.markdown(
                """
                **Reference file (uploaded):**  
                [Operational Flow document](/mnt/data/Operational Flow.docx)
                """,
                unsafe_allow_html=True
            )

    st.success("If you need actual exports enabled, tell me which formats to enable and I will implement them.")

# end of app.py
