import streamlit as st
from decision_engine import run_simulation, explain_decision
import plotly.graph_objects as go
import random

# ---------------------------------------------------------------------
# 🌟 Page Configuration
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Original Enterprise AI – Group X Prototype (Ports Integration)",
    page_icon="🚢",
    layout="wide"
)

# ---------------------------------------------------------------------
# 🌟 Header
# ---------------------------------------------------------------------
st.markdown(
    """
    <style>
        h1, h2, h3, h4, h5, h6 { font-family: 'Inter', sans-serif; }
        .title { text-align: center; margin-bottom: 0px; }
        .subtitle { text-align: center; color: #555; font-size: 18px; margin-bottom: 30px; }
        .highlight-box {
            background-color: #f1f8ff;
            padding: 15px;
            border-radius: 10px;
            border-left: 6px solid #2b8a3e;
        }
        .explain-box {
            background-color: #fff8e1;
            padding: 15px;
            border-radius: 10px;
            border-left: 6px solid #ffb300;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<h1 class='title'>🚢 Original Enterprise AI – Group X Prototype</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='subtitle'>This demo shows how <b>Original Enterprise AI</b> processes a CEO's strategic query through "
    "<b>Group Manager → Enterprise Manager → Port Nodes → Steel Plants</b> and returns an explainable recommendation "
    "that aligns logistics and production.</p>",
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------
# 🧩 User Input Section
# ---------------------------------------------------------------------
st.header("Ask a strategic question:")

query = st.text_input(
    "Strategic Query:",
    placeholder="How can we increase steel production with minimal investment and port efficiency?",
)

# ---------------------------------------------------------------------
# 🧠 Run Simulation Logic
# ---------------------------------------------------------------------
if st.button("Run Simulation", type="primary"):
    if query.strip() == "":
        query = "How can we increase steel production with minimal investment and port efficiency?"

    # Run simulation from decision engine
    result = run_simulation(query)

    # Randomly assign port details for realism
    import_ports = ["Port Alpha", "Port Bravo", "Port Delta"]
    export_ports = ["Port Echo", "Port Foxtrot", "Port Gamma"]

    import_port = random.choice(import_ports)
    export_port = random.choice(export_ports)

    # -----------------------------------------------------------------
    # 📊 Display Results
    # -----------------------------------------------------------------
    st.header("AI Recommendation Summary")

    st.write(f"**Recommended Plant:** {result['Recommended Plant']}")
    st.write(f"**Expected Output Increase:** {result['Expected Output Increase']}")
    st.write(f"**Capital Investment:** {result['Capital Investment']}")
    st.write(f"**ROI Period:** {result['ROI Period']}")
    st.write(f"**Energy Required:** {result['Energy Required']}")
    st.write(f"**Import Port:** {import_port} (raw material intake)")
    st.write(f"**Export Port:** {export_port} (finished product dispatch)")

    summary = (
        f"Increase capacity at {result['Recommended Plant']} using optimized raw material supply via {import_port} "
        f"and outbound logistics through {export_port}. {result['Summary']}"
    )

    st.markdown(f"<div class='highlight-box'>{summary}</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # 💬 Explainable AI Section
    # -----------------------------------------------------------------
    st.header("💬 Explainable AI Insight")
    with st.spinner("Generating AI explanation..."):
        explanation = explain_decision(summary)

    st.markdown(f"<div class='explain-box'>{explanation}</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # 🔄 Data & Decision Flow (Ports + Plants)
    # -----------------------------------------------------------------
    st.header("📊 Data and Decision Flow")

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=30,
                    thickness=25,
                    line=dict(color="black", width=0.5),
                    label=[
                        "CEO Query",
                        "Group Manager",
                        "Enterprise Manager (Steel)",
                        f"{import_port} (Import Port)",
                        f"{result['Recommended Plant']} (Steel Plant)",
                        f"{export_port} (Export Port)",
                        "Recommendation"
                    ],
                    color=[
                        "#2E86DE",
                        "#54A0FF",
                        "#FF6B6B",
                        "#60A917",
                        "#F39C12",
                        "#16A085",
                        "#1DD1A1"
                    ],
                ),
                link=dict(
                    source=[0, 1, 2, 3, 4, 5],
                    target=[1, 2, 3, 4, 5, 6],
                    value=[1, 1, 1, 1, 1, 1],
                    color=["rgba(0,0,0,0.1)"] * 6
                ),
            )
        ]
    )

    fig.update_layout(
        title_text="Integrated Decision Flow – Strategy, Logistics, and Operations",
        font=dict(size=14, color="black"),
        height=500,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)
