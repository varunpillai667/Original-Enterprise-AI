# File: app.py
import streamlit as st
from decision_engine import run_simulation

st.set_page_config(layout="wide", page_title="Enterprise AI – Group X Strategic Simulator")

# ---- INTRODUCTION SECTION ----
st.title("Enterprise AI – Group X Strategic Simulator")

st.markdown(
    """
    <div style="font-size:16px; line-height:1.4; margin-bottom:15px;">
    This simulation models how Enterprise Managers (EMs) and Group Managers coordinate upgrades across
    Group X’s assets. Local nodes report into their respective EMs, company systems feed real-time data,
    and the Group Manager integrates everything at the enterprise level. The simulation considers steel plants,
    ports, and power plants, along with all required operational, external, and infrastructural variables.
    <br><br>
    All calculations are based on assumptions for demonstration purposes.
    </div>
    """,
    unsafe_allow_html=True
)

# ---- STRATEGIC QUERY ----
default_query = (
    "How can Group X increase steel production by approximately 2 MTPA in a reasonable time, "
    "and what is the expected timeline for recovering the investment?"
)

st.subheader("Strategic Query")
query = st.text_area(
    "Enter your high-level strategic query",
    value=default_query,
    height=120
)

# ---- RUN SIMULATION BUTTON + INFO TEXT ----
col_btn, col_info = st.columns([0.28, 1])

with col_btn:
    if st.button("Run Simulation"):
        result = run_simulation(query)
        st.session_state["result"] = result

with col_info:
    st.markdown(
        """
        <span style="font-size: 13px; color:#555;">
        (Clicking <strong>Run Simulation</strong> fetches all internal and external operating data and generates a complete, end-to-end solution.)
        </span>
        """,
        unsafe_allow_html=True
    )

# ---- DISPLAY RESULTS ----
if "result" in st.session_state:
    result = st.session_state["result"]

    rec = result["recommendation"]
    roadmap = result["roadmap"]
    rationale = result["rationale"]

    # --- Main Recommendation ---
    st.header("Recommendation")

    st.subheader(rec["headline"])
    st.write(rec["summary"])

    metrics = rec["metrics"]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Added Capacity (MTPA)", f"{metrics['added_mtpa']:.3f}")
    col2.metric("Investment (USD)", f"${metrics['investment_usd']:,}")
    col3.metric("Payback (months)", metrics["estimated_payback_months"])
    col4.metric("Timeline (months)", metrics["project_timeline_months"])
    col5.metric("Confidence", f"{metrics['confidence_pct']}%")

    st.divider()

    # --- Key Recommendations Section ---
    st.subheader("Key Recommendations")
    for step in rec["key_recommendations"]:
        with st.expander(step["step"]):
            st.markdown(f"**Owner:** {step['owner']}")
            st.markdown(f"**Estimated Duration:** {step['duration_months']} months")
            st.markdown("**Details:**")
            for d in step["details"]:
                st.markdown(f"- {d}")
            if "plants_in_scope" in step:
                st.markdown("**Plants in Scope:** " + ", ".join(step["plants_in_scope"]))

    st.divider()

    # --- Per Plant Upgrades ---
    st.subheader("Per-Plant Upgrades")
    for plant in rec["per_plant_upgrades"]:
        with st.expander(f"{plant['plant_name']} (+{plant['added_mtpa']} MTPA)"):
            st.markdown(f"**Current Capacity:** {plant['current_capacity_tpa']:,} tpa")
            st.markdown("**Upgrade Scope:**")
            for item in plant["upgrade_scope"]:
                st.markdown(f"- {item}")
            st.markdown(f"**Investment:** ${plant['capex_total_usd']:,}")
            st.markdown(f"**Estimated Payback:** {plant['estimated_payback_months']} months")
            st.markdown("**Hiring Requirements:**")
            st.write(plant["hiring_estimate"])
            st.markdown("**Schedule (months):**")
            st.write(plant["schedule_months"])

    st.divider()

    # --- Roadmap Section ---
    st.subheader("Roadmap (Phases)")

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    phases = roadmap["phases"]

    cols = [c1, c2, c3, c4, c5, c6, c7]
    for col, phase in zip(cols, phases):
        col.markdown(f"**{phase['phase']}**")
        col.markdown(f"Duration: {phase['months']} months")

    st.divider()

    # --- Rationale ---
    st.subheader("Decision Rationale")
    for b in rationale["bullets"]:
        st.markdown(f"- {b}")
