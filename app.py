# app.py
# Streamlit interface for the Original Enterprise AI prototype

import streamlit as st
from decision_engine import run_simulation, explain_decision

st.set_page_config(page_title="Original Enterprise AI Prototype", layout="centered")

st.title("🧠 Original Enterprise AI — Group X Prototype")
st.markdown("""
This demo shows how **Original Enterprise AI** processes a CEO's question through:
**Group Manager → Enterprise Manager → Local Nodes**  
and returns an explainable AI recommendation.
""")

# -----------------------------------------------------------------------------
# 1️⃣  CEO Question Input
# -----------------------------------------------------------------------------
st.subheader("Ask a strategic question:")
question = st.text_input("Example: How can we increase steel production with minimal investment?")

if st.button("Run Simulation"):
    with st.spinner("Running enterprise simulation..."):
        # Run mock decision simulation
        result = run_simulation()

        # Display results
        st.header("AI Recommendation Summary")
        st.markdown(f"**Recommended Plant:** {result['Recommended Plant']}")
        st.markdown(f"**Expected Output Increase:** {result['Expected Output Increase']}")
        st.markdown(f"**Capital Investment:** {result['Capital Investment']}")
        st.markdown(f"**ROI Period:** {result['ROI Period']}")
        st.markdown(f"**Energy Required:** {result['Energy Required']}")

        st.info(result['Summary'])

        # -----------------------------------------------------------------------------
        # 2️⃣  GPT Explanation Section
        # -----------------------------------------------------------------------------
        st.subheader("💬 Explainable AI Insight")

        explanation = explain_decision(result['Summary'])
        st.markdown(explanation)

        # -----------------------------------------------------------------------------
        # 3️⃣  Optional Data Display
        # -----------------------------------------------------------------------------
        with st.expander("📊 Data and Decision Flow"):
            st.json(result)
