import streamlit as st
import plotly.graph_objects as go
from decision_engine import run_simulation, explain_decision

st.set_page_config(page_title="Original Enterprise AI – Group Manager Cross-EM Demo", layout="wide")
st.title("🧠 Group Manager Cross-EM Demo — explicit provenance")

st.markdown("""
**This prototype demonstrates the exact data & control flow described in the whitepaper and operational flow document.**  
- Group Manager reads **group-level systems** (commodity, treasury, ESG) — shown as Group Systems.  
- Enterprise Managers read **Company HQ systems (ERP/Finance)** *and* **Local Nodes** (OT telemetry).  
- Local Nodes connect to OT systems at Ports & Plants (SCADA, MES, TOS).  
Files used for reference (uploaded):  
- Operational Flow: `/mnt/data/Operational Flow.docx`  
- Whitepaper: `/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf`  
""")

query = st.text_input("Strategic Query:", "How can we increase steel production with minimal investment?")
capex_limit = st.number_input("Optional CapEx limit (USD):", value=0.0, min_value=0.0, step=10000.0, format="%.2f")

if st.button("Run Simulation"):
    with st.spinner("Running cross-EM orchestration (Group Manager)..."):
        try:
            capex_value = capex_limit if capex_limit > 0 else None
            result = run_simulation(query, capex_value)

            # Top-level recommendation
            st.subheader("Group Manager Recommendation")
            st.markdown(f"**Plant:** {result['recommended_plant']}")
            st.markdown(f"**Expected Increase:** {result['expected_increase_pct']}")
            st.markdown(f"**Investment (USD):** {result['investment_usd']}")
            st.markdown(f"**ROI:** {result['roi_period_months']} months")
            st.markdown(f"**Energy Required:** {result['energy_required_mw']} MW")
            st.info(result['summary'])

            # Provenance panel: show clearly which systems fed the decision
            st.subheader("Data Provenance (who fed what)")
            prov_cols = st.columns(3)
            with prov_cols[0]:
                st.markdown("**Local Node (OT systems)**")
                st.write(result['provenance']['local_node_id'])
                st.write("Connected OT systems: SCADA, MES, TOS (simulated)")
            with prov_cols[1]:
                st.markdown("**Company HQ systems**")
                st.write(f"Steel HQ: {result['provenance']['steel_hq']}")
                st.write(f"Ports HQ: {result['provenance']['ports_hq']}")
            with prov_cols[2]:
                st.markdown("**Group systems**")
                st.write(result['provenance']['group_systems'])

            # EM summaries (concise)
            st.subheader("Enterprise Manager Summaries (what each EM returned)")
            cols = st.columns(3)
            with cols[0]:
                st.markdown("**Steel EM (top candidates)**")
                for c in result["em_summaries"]["steel_top_candidates"]:
                    st.write(f"{c['plant_id']}: +{c['feasible_increase_pct']}% — CapEx ${c['capex_estimate_usd']:,} — Energy {c['energy_required_mw']} MW")
                    st.write(f"  sources: {c.get('data_sources')}")
            with cols[1]:
                st.markdown("**Ports EM**")
                p = result["em_summaries"]["ports_info"]
                st.write(f"Port headroom: {p['port_headroom_units']} units (util {p['current_utilization']})")
                st.write(f"  sources: {p.get('data_sources')}")
            with cols[2]:
                st.markdown("**Energy EM**")
                e = result["em_summaries"]["energy_info"]
                st.write(f"Headroom: {e['energy_headroom_mw']} MW (avail {e['energy_available_mw']} MW)")
                st.write(f"  sources: {e.get('data_sources')}")

            # Sankey: explicit multi-source flow (OT -> Local Node -> EMs & HQ -> Group Systems -> Recommendation)
            nodes = [
                "SCADA/MES/TOS (OT)", "Local Node", 
                "Steel HQ (ERP)", "Steel EM",
                "Ports HQ (ERP)", "Ports EM",
                "Energy HQ (ERP)", "Energy EM",
                "Group Systems", "Group Manager", "Recommendation"
            ]
            node_colors = ["#d6eaf8","#aed6f1","#f9e79f","#f5b7b1","#d5f5e3","#fad7a0","#d6eaf8","#f5cba7","#d2b4de","#5dade2","#1abc9c"]
            # Define links to show data flow clearly
            source = [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            target = [1, 2, 3, 3, 9, 5, 9, 7, 9, 9, 10]
            # values are illustrative for the diagram
            value = [5, 2, 3, 4, 4, 2, 4, 3, 2, 5, 8]

            fig = go.Figure(data=[go.Sankey(
                node=dict(label=nodes, color=node_colors, pad=15, thickness=20),
                link=dict(source=source, target=target, value=value)
            )])
            fig.update_layout(title_text="System Connectivity & Data Flow (OT → LOCAL → EMs/HQ → Group)", font_size=11)
            st.plotly_chart(fig, use_container_width=True)

            # Explainable narrative (cross-EM)
            st.subheader("Explainable Narrative")
            st.write(explain_decision(query, result))

            if result.get("provenance", {}).get("budget_flag", False):
                st.warning("CapEx limit filtered candidates; the recommendation shows the top candidate with a budget flag.")

        except Exception as e:
            st.error(f"Simulation Error: {e}")
