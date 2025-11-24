# ------------------------------
# File: decision_engine.py
# ------------------------------
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List

# Executive consulting-grade decision engine
# Documentation prioritized over inline comments.

CAPEX_PER_MTPA_USD = 420_000_000
MARGIN_PER_TON_USD = 120
MW_PER_MTPA = 2.5
CARGO_TONNE_PER_STEEL_TONNE = 0.15

PORT_UTILIZATION = 0.70
PORT_GROUP_SHARE_OF_USED = 1.0 / 3.0

ENERGY_UTILIZATION = 0.75
ENERGY_GRID_SHARE_OF_USED = 3.0 / 4.0

START_CONFIDENCE = 88
MIN_CONFIDENCE = 50

USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]  # SP1..SP4

CANDIDATE_MOCKS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

# Uploaded doc path (preserved for traceability)
OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"

def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

def _approx_equal(a: float, b: float, rel_tol: float = 0.01) -> bool:
    if b == 0:
        return abs(a) < 1e-6
    return abs(a - b) <= max(rel_tol * abs(b), 1e-6)

def _load_mock_data() -> Dict[str, Any]:
    debug: List[str] = []
    for p in CANDIDATE_MOCKS:
        try:
            if p.exists():
                with open(p, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                debug.append(f"Loaded mock_data.json from {p}")
                return {"data": data, "debug": debug, "path": str(p)}
        except Exception as exc:
            debug.append(f"Failed to load {p}: {exc}")
    debug.append("No mock_data.json found; using built-in defaults.")
    defaults = {
        "steel": {"plants": [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]},
        "ports": {"ports": [
            {"id":"P1","capacity_tpa":2_000_000},
            {"id":"P2","capacity_tpa":1_800_000},
            {"id":"P3","capacity_tpa":1_600_000},
            {"id":"P4","capacity_tpa":1_400_000},
        ]},
        "energy": {"plants": [
            {"id":"E1","capacity_mw":500},
            {"id":"E2","capacity_mw":450},
            {"id":"E3","capacity_mw":400},
        ]}
    }
    return {"data": defaults, "debug": debug, "path": None}

def _parse_query(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    out = {"target_mtpa": 2.0, "target_months": None, "max_payback_months": None, "debug": []}
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            out["target_mtpa"] = float(m.group(1))
        except:
            out["debug"].append("Failed parsing target MTPA; using 2.0")
    mm = re.search(r'(\d{1,3})\s*(?:months|month)', q)
    if mm:
        try:
            out["target_months"] = int(mm.group(1))
        except:
            out["debug"].append("Failed parsing months; ignoring")
    pp = re.search(r'payback.*?(?:less than|within|<)\s*(\d+)\s*(years|year)', q)
    if pp:
        try:
            out["max_payback_months"] = int(pp.group(1)) * 12
        except:
            out["debug"].append("Failed parsing payback; ignoring")
    return out

def _rank_by_roi(breakdown: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for p in breakdown:
        capex = float(p.get("capex_usd", 0)) or 1.0
        margin = float(p.get("annual_margin_usd", 0))
        p["roi_proxy"] = (margin / capex) if capex else 0.0
    return sorted(breakdown, key=lambda x: x["roi_proxy"], reverse=True)

def _stress_test_margin(margin_drop_pct: float, total_margin: float) -> Dict[str, Any]:
    stressed_margin = total_margin * (1 - margin_drop_pct)
    return {"stress_pct": margin_drop_pct, "stressed_margin": stressed_margin}

def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query(query)
    debug: List[str] = parsed.get("debug", [])

    loaded = _load_mock_data()
    data = loaded.get("data", {})
    debug += loaded.get("debug", [])
    if loaded.get("path"):
        debug.append(f"Using mock file: {loaded.get('path')}")

    plants = (data.get("steel") or {}).get("plants") or []
    if len(plants) < 4:
        debug.append("Steel plant data incomplete; applying 4-plant defaults.")
        plants = [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]

    ports = (data.get("ports") or {}).get("ports") or []
    if not ports:
        debug.append("Ports data missing; using defaults.")
        ports = [
            {"id":"P1","capacity_tpa":2_000_000},
            {"id":"P2","capacity_tpa":1_800_000},
            {"id":"P3","capacity_tpa":1_600_000},
            {"id":"P4","capacity_tpa":1_400_000},
        ]

    energy_plants = (data.get("energy") or {}).get("plants") or []
    if not energy_plants:
        debug.append("Energy data missing; using defaults.")
        energy_plants = [
            {"id":"E1","capacity_mw":500},
            {"id":"E2","capacity_mw":450},
            {"id":"E3","capacity_mw":400},
        ]

    total_port_capacity = sum(int(p.get("capacity_tpa", 0)) for p in ports)
    used_port = PORT_UTILIZATION * total_port_capacity
    group_port_share = used_port * PORT_GROUP_SHARE_OF_USED
    spare_port = total_port_capacity - used_port
    available_port_for_steel = spare_port + group_port_share

    total_energy_capacity = sum(float(e.get("capacity_mw", 0)) for e in energy_plants)
    used_energy = ENERGY_UTILIZATION * total_energy_capacity
    grid_energy_share = used_energy * ENERGY_GRID_SHARE_OF_USED
    group_energy_share = used_energy - grid_energy_share
    spare_energy = total_energy_capacity - used_energy
    available_energy_for_steel = spare_energy + group_energy_share

    num_plants = min(4, len(plants))
    dist_mtpa = USER_DISTRIBUTION_MTPA[:num_plants]
    added_tpa_list = [int(round(m * 1_000_000)) for m in dist_mtpa]

    breakdown: List[Dict[str, Any]] = []
    total_added_tpa = 0
    total_capex = 0.0
    total_margin = 0.0

    for idx in range(num_plants):
        p = plants[idx]
        added = added_tpa_list[idx]
        mtpa_added = added / 1_000_000.0
        capex = _capex_for_mtpa(mtpa_added)
        margin = _annual_margin_for_tpa(added)
        payback_months = None if margin == 0 else (capex / margin) * 12.0
        hires_units = max(1, int(round(mtpa_added * 10)))
        breakdown.append({
            "id": p.get("id"),
            "name": p.get("name", p.get("id", "")),
            "current_capacity_tpa": int(p.get("current_capacity_tpa", 0)),
            "added_tpa": int(added),
            "added_mtpa": round(mtpa_added, 3),
            "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + added),
            "capex_usd": int(round(capex)),
            "annual_margin_usd": int(round(margin)),
            "payback_months": None if payback_months is None else round(payback_months, 1),
            "hiring_estimate": {
                "operators": hires_units * 5,
                "maintenance": hires_units * 2,
                "engineers": hires_units * 1,
                "project_managers": 1
            }
        })
        total_added_tpa += added
        total_capex += capex
        total_margin += margin

    total_added_mtpa = total_added_tpa / 1_000_000.0
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)
    port_required_tpa = int(round(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE))
    aggregated_payback_months = None if total_margin == 0 else (total_capex / total_margin) * 12.0

    planning = 3
    procurement = max(2, int(round(2 + total_added_mtpa * 4)))
    implementation = max(3, int(round(4 + total_added_mtpa * 6)))
    commissioning = max(1, int(round(implementation * 0.25)))
    stabilization = max(1, int(round(commissioning * 0.5)))
    estimated_total_months = planning + procurement + implementation + commissioning + stabilization

    validations = {"checks": [], "passed": True}
    target_mtpa = parsed.get("target_mtpa", 2.0)
    if _approx_equal(total_added_mtpa, target_mtpa, rel_tol=0.01):
        validations["checks"].append({"name": "Target MTPA", "status": "pass", "detail": f"Added {total_added_mtpa:.3f} MTPA meets target {target_mtpa} MTPA"})
    else:
        validations["checks"].append({"name": "Target MTPA", "status": "fail", "detail": f"Added {total_added_mtpa:.3f} MTPA does not match target {target_mtpa} MTPA"})
        validations["passed"] = False

    max_payback = parsed.get("max_payback_months")
    if max_payback is not None:
        if aggregated_payback_months is not None and aggregated_payback_months <= max_payback:
            validations["checks"].append({"name": "Payback", "status": "pass", "detail": f"Aggregated payback {aggregated_payback_months:.1f} months <= requested {max_payback} months"})
        elif aggregated_payback_months is None:
            validations["checks"].append({"name": "Payback", "status": "fail", "detail": "Unable to compute aggregated payback (zero margin)."})
            validations["passed"] = False
        else:
            validations["checks"].append({"name": "Payback", "status": "fail", "detail": f"Aggregated payback {aggregated_payback_months:.1f} months exceeds requested {max_payback} months"})
            validations["passed"] = False

    if energy_required_mw <= available_energy_for_steel + 1e-6:
        validations["checks"].append({"name": "Energy", "status": "pass", "detail": f"Needs {energy_required_mw:.2f} MW; available {available_energy_for_steel:.2f} MW"})
    else:
        validations["checks"].append({"name": "Energy", "status": "fail", "detail": f"Needs {energy_required_mw:.2f} MW; available {available_energy_for_steel:.2f} MW"})
        validations["passed"] = False

    if port_required_tpa <= available_port_for_steel + 1e-6:
        validations["checks"].append({"name": "Ports", "status": "pass", "detail": f"Requires {port_required_tpa:,} tpa; available {int(available_port_for_steel):,} tpa"})
    else:
        validations["checks"].append({"name": "Ports", "status": "fail", "detail": f"Requires {port_required_tpa:,} tpa; available {int(available_port_for_steel):,} tpa"})
        validations["passed"] = False

    if parsed.get("target_months") is not None:
        if estimated_total_months <= parsed.get("target_months"):
            validations["checks"].append({"name": "Schedule", "status": "pass", "detail": f"Estimated {estimated_total_months} months <= target {parsed.get('target_months')} months"})
        else:
            validations["checks"].append({"name": "Schedule", "status": "fail", "detail": f"Estimated {estimated_total_months} months exceeds target {parsed.get('target_months')} months"})
            validations["passed"] = False

    ranked = _rank_by_roi(breakdown)
    phase_a = [p["name"] for p in ranked[:2]]
    phase_b = [p["name"] for p in ranked[2:]] if len(ranked) > 2 else []

    stress_10 = _stress_test_margin(0.10, total_margin)
    stress_20 = _stress_test_margin(0.20, total_margin)

    headline = f"Executive Recommendation: +{total_added_mtpa:.3f} MTPA (staged, ROI-first)"
    metrics = {
        "added_tpa": int(total_added_tpa),
        "added_mtpa": round(total_added_mtpa, 3),
        "investment_usd": int(round(total_capex)),
        "estimated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "port_throughput_required_tpa": int(port_required_tpa),
    }

    actions = [
        "Phase A (0–9 months): Deploy MES + targeted automation and modular EAF cells at highest-ROI plants (immediate OEE uplift).",
        "Parallel: Secure long-lead equipment purchase agreements (frame contracts) and pre-qualify suppliers to compress procurement.",
        "Phase B (6–15 months): Execute raw-material handling upgrades, stockyard automation and port corridor arrangements to protect commercial cargo throughput.",
        "Energy program: negotiate short-term PPAs + implement WHR & substation uprates; include battery buffering where marginal cost permits.",
        "Finance: Stage CAPEX by ROI (Phase A first). Create a project-level PMO with weekly gates and KPI dashboards (delivery, cost, energy, port throughput).",
        "Risk & Mitigation: Pre-negotiated 3PL and temporary berth leases; contingency PPA tranche; supplier SLAs with penalties for key long-lead items."
    ]

    rationale_bullets: List[str] = []
    rationale_bullets.append("MES + targeted automation: Rapidly improves OEE and reduces commissioning ramp time — shortest path to cash flow improvement and payback acceleration.")
    rationale_bullets.append("Modular EAF approach: Faster installation, modular commissioning, better capital efficiency vs full greenfield expansion.")
    rationale_bullets.append("Supplier & procurement controls: Compresses critical path by aligning lead times and de-risking long-lead items via frame contracts.")
    rationale_bullets.append("Port corridor & logistics orchestration: Ensures commercial cargo SLAs are protected while supporting increased raw-material flow.")
    rationale_bullets.append("Energy program (PPA + WHR + buffering): Reduces exposure to grid deficits and improves operating margins, directly shortening payback.")
    rationale_bullets.append(f"Staging recommendation: Phase A targets {', '.join(phase_a)} to maximize early ROI; Phase B handles remaining plants to smooth capex and schedule risk.")

    for chk in validations["checks"]:
        status = chk["status"].upper()
        rationale_bullets.append(f"Validation — {chk['name']}: {status} — {chk['detail']}")

    mitigations: List[str] = []
    for chk in validations["checks"]:
        if chk["status"] == "fail":
            if chk["name"] == "Payback":
                mitigations.append("Staged capex (Phase A focused on highest ROI), renegotiate pricing, or increase product margin via premium SKUs.")
            if chk["name"] == "Energy":
                mitigations.append("Secure short-term PPA, deploy temporary generation or reduce peak loads via process tuning.")
            if chk["name"] == "Ports":
                mitigations.append("Contract third-party logistics (3PL), lease temporary berth capacity, or stage material arrivals.")
            if chk["name"] == "Schedule":
                mitigations.append("Add contracted installation crews, parallelize engineering and procurement, or accept phased delivery.")
            if chk["name"] == "Target MTPA":
                mitigations.append("Redistribute increases or accept phased completion to meet timeline with lower risk.")

    if mitigations:
        rationale_bullets.append("Mitigations / Alternatives:")
        rationale_bullets += mitigations

    confidence = START_CONFIDENCE
    for chk in validations["checks"]:
        if chk["status"] == "fail":
            confidence -= 10
    if stress_10["stressed_margin"] <= 0:
        confidence -= 5
    confidence = max(confidence, MIN_CONFIDENCE)

    per_plant_schedule = []
    sorted_breakdown = _rank_by_roi(breakdown)
    offset = 0
    for p in sorted_breakdown:
        share = p["added_tpa"] / (total_added_tpa or 1)
        proc = max(1, int(round(procurement * share))) if 'procurement' in locals() else 2
        impl = max(1, int(round(implementation * share))) if 'implementation' in locals() else 6
        comm = max(1, int(round(commissioning * share))) if 'commissioning' in locals() else 1
        start = offset + 1
        online = start + proc + impl + comm
        per_plant_schedule.append({
            "plant": p["name"],
            "start_month_planning": start,
            "procurement_window_months": proc,
            "implementation_window_months": impl,
            "commissioning_window_months": comm,
            "expected_online_month": online
        })
        offset += max(1, int(round(impl * 0.5)))

    result = {
        "recommendation": {
            "headline": headline,
            "summary": f"Stage capacity additions to prioritize ROI and protect commercial operations; Phase A targets {', '.join(phase_a)} for fastest return.",
            "metrics": metrics,
            "actions": actions,
            "distribution": [{"plant": d["name"], "added_mtpa": d["added_mtpa"], "capex_usd": d["capex_usd"], "payback_months": d["payback_months"]} for d in breakdown]
        },
        "roadmap": {
            "phases": [
                {"phase": "Planning", "months": planning, "notes": "Engineering, permits, PMO setup"},
                {"phase": "Procurement", "months": procurement, "notes": "Frame contracts, long-lead orders"},
                {"phase": "Implementation", "months": implementation, "notes": "Installation & integration"},
                {"phase": "Commissioning", "months": commissioning, "notes": "Cold / hot commissioning"},
                {"phase": "Stabilization", "months": stabilization, "notes": "Ramp & optimization"},
            ],
            "per_plant_schedule": per_plant_schedule
        },
        "rationale": {"bullets": rationale_bullets},
        "validations": validations,
        "metrics": {
            "total_capex_usd": int(round(total_capex)),
            "total_annual_margin_usd": int(round(total_margin)),
            "aggregated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
            "energy_required_mw": round(energy_required_mw, 2),
            "port_required_tpa": int(port_required_tpa),
            "estimated_total_months": estimated_total_months,
            "stress_tests": {
                "10pct_margin_drop": stress_10,
                "20pct_margin_drop": stress_20
            }
        },
        "em_summaries": {
            "steel_info": {"plant_distribution": breakdown},
            "ports_info": {"total_port_capacity_tpa": total_port_capacity, "used_port_tpa": int(used_port)},
            "energy_info": {"total_energy_capacity_mw": total_energy_capacity, "used_energy_mw": used_energy},
        },
        "infrastructure_analysis": {
            "ports": {
                "total_port_capacity_tpa": total_port_capacity,
                "used_port_tpa": int(used_port),
                "group_port_share_tpa": group_port_share,
                "spare_port_tpa": spare_port,
                "available_port_for_steel_tpa": available_port_for_steel,
                "port_throughput_required_tpa": port_required_tpa
            },
            "energy": {
                "total_energy_capacity_mw": total_energy_capacity,
                "used_energy_mw": used_energy,
                "group_energy_share_mw": group_energy_share,
                "spare_energy_mw": spare_energy,
                "available_energy_for_steel_mw": available_energy_for_steel,
                "energy_required_mw": energy_required_mw
            }
        },
        "confidence_pct": confidence,
        "notes": {"debug": debug, "operational_flow_doc": OPERATIONAL_FLOW_DOC}
    }

    return result

if __name__ == "__main__":
    q = "What is the recommended approach for increasing Group X’s steel production by approximately 2 MTPA, including the upgrades required across steel plants, the expected investment, the realistic implementation timeline, and the estimated period in which the investment can be recovered?"
    import pprint
    pprint.pprint(run_simulation(q))


# ------------------------------
# File: app.py
# ------------------------------
import streamlit as st
import pandas as pd
import json
from typing import Any, Dict
from decision_engine import run_simulation

st.set_page_config(page_title="Original Enterprise AI Concept Prototype", layout="wide")
st.title("Original Enterprise AI Concept Prototype")

# Compact intro: shorter spacing, includes EM simulation capability
st.markdown(
    """
**Group X** operates 4 ports, 4 steel plants and 3 power plants.  
All simulation results are based on assumed, simplified data for conceptual demonstration.

**Operating principles (compact)**  
LOCAL nodes collect and forward operational data. EMs (Ports EM, Steel EM, Energy EM) aggregate local data, connect to company-level systems (ERP/MES/SCADA) and can perform **company-level simulations and decision-making**. The Group Manager aggregates EM outputs and performs cross-company, enterprise-wide simulations and recommendations.

Purpose: illustrate how a multi-layer enterprise system answers strategic questions with simulated data.
"""
)

st.markdown("---")

def parse_hiring(x: Any) -> Dict[str, int]:
    base = {"engineers": 0, "maintenance": 0, "operators": 0, "project_managers": 0}
    if isinstance(x, dict):
        return {k: int(x.get(k, 0)) for k in base}
    if isinstance(x, str):
        try:
            j = json.loads(x)
            if isinstance(j, dict):
                return {k: int(j.get(k, 0)) for k in base}
        except:
            pass
    return base

def nice_number(v: Any):
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return round(v, 2)
    return v

def pretty_infra(data: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for section, vals in (data or {}).items():
        if isinstance(vals, dict):
            out[section] = {k: nice_number(v) for k, v in vals.items()}
        else:
            out[section] = vals
    return out

st.subheader("Strategic Query")
default_query = ("What is the recommended approach for increasing Group X’s steel production by approximately 2 MTPA, "
                 "including the upgrades required across steel plants, the expected investment, the realistic implementation timeline, "
                 "and the estimated period in which the investment can be recovered?")
query = st.text_area("Enter high-level strategic query", value=default_query, height=120)

if st.button("Run Simulation"):

    if not query.strip():
        st.error("Please enter a strategic query.")
        st.stop()

    with st.spinner("Running simulation..."):
        try:
            result = run_simulation(query)
        except Exception as exc:
            st.error(f"Simulation error: {exc}")
            st.stop()

    rec = result.get("recommendation", {})
    roadmap = result.get("roadmap", {})

    # Recommendation — compact, full width
    st.header("Recommendation")
    st.subheader(rec.get("headline", "Proposed action"))
    if rec.get("summary"):
        st.write(rec["summary"])

    metrics = rec.get("metrics", {})
    mcols = st.columns(4)
    mcols[0].metric("Added (MTPA)", metrics.get("added_mtpa", "—"))
    mcols[1].metric("Investment (USD)", f"${metrics.get('investment_usd',0):,}")
    mcols[2].metric("Est. Payback (months)", metrics.get("estimated_payback_months","—"))
    mcols[3].metric("Confidence", f"{result.get('confidence_pct','—')}%")

    if rec.get("actions"):
        st.subheader("Key recommended actions")
        for a in rec.get("actions", [])[:8]:
            st.write(f"- {a}")

    debug_lines = result.get("notes", {}).get("debug", [])
    if debug_lines:
        with st.expander("Debug / data-loading notes"):
            for d in debug_lines:
                st.write(f"- {d}")

    st.markdown("---")

    # Roadmap — below Recommendation (clean columns)
    st.header("Roadmap (Phases)")
    phases = roadmap.get("phases", [])
    if phases:
        cols = st.columns(len(phases))
        for col, ph in zip(cols, phases):
            html = f"""
            <div style="padding:10px; min-width:180px; box-sizing:border-box;">
                <div style="font-weight:700; font-size:14px; margin-bottom:6px; white-space:nowrap;">
                    {ph.get('phase','')}
                </div>
                <div style="margin-bottom:6px;">
                    <strong>Duration:</strong> {ph.get('months','—')} months
                </div>
                <div style="font-size:13px; color:#444; white-space:normal;">
                    {ph.get('notes','')}
                </div>
            </div>
            """
            col.markdown(html, unsafe_allow_html=True)
    else:
        st.write("No roadmap phases available.")

    st.markdown("---")

    # Per-Plant Schedule
    st.subheader("Per-Plant Schedule")
    p_sched = roadmap.get("per_plant_schedule", [])
    if p_sched:
        st.table(pd.DataFrame(p_sched))
    else:
        st.write("Schedule unavailable.")

    st.markdown("---")

    # Decision Rationale & Financials (compact)
    st.header("Decision Rationale & Financials")
    col_rat, col_fin = st.columns([2, 1])

    with col_rat:
        st.subheader("Decision Rationale")
        for b in result.get("rationale", {}).get("bullets", []):
            st.write(f"- {b}")

    with col_fin:
        st.subheader("Per-Plant Financials")
        plant_dist = result.get("em_summaries", {}).get("steel_info", {}).get("plant_distribution", [])
        if plant_dist:
            df = pd.DataFrame(plant_dist)
            if "hiring_estimate" in df.columns:
                hires = df["hiring_estimate"].apply(parse_hiring)
                hires_df = pd.DataFrame(list(hires))
                df = pd.concat([df.drop(columns=["hiring_estimate"]), hires_df], axis=1)
            if "capex_usd" in df.columns:
                df["capex_usd"] = df["capex_usd"].apply(lambda x: f"${x:,}")
            if "annual_margin_usd" in df.columns:
                df["annual_margin_usd"] = df["annual_margin_usd"].apply(lambda x: f"${x:,}")
            st.table(df[[c for c in df.columns if c in ["name","current_capacity_tpa","added_mtpa","capex_usd","annual_margin_usd","payback_months"]]])
        else:
            st.write("No plant distribution available.")

    st.markdown("---")

    # Infrastructure Analysis (Ports & Energy)
    st.header("Infrastructure Analysis")
    infra = pretty_infra(result.get("infrastructure_analysis", {}))
    ports = infra.get("ports", {})
    energy = infra.get("energy", {})

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Ports")
        if ports:
            preferred_order = [
                "total_port_capacity_tpa",
                "used_port_tpa",
                "group_port_share_tpa",
                "spare_port_tpa",
                "available_port_for_steel_tpa",
                "port_throughput_required_tpa",
            ]
            for key in preferred_order:
                if key in ports:
                    label = key.replace("_", " ").title()
                    st.write(f"- **{label}:** {ports[key]}")
            for k, v in ports.items():
                if k not in preferred_order:
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
        else:
            st.write("No port data.")

    with c2:
        st.subheader("Energy")
        if energy:
            preferred_energy_order = [
                "total_energy_capacity_mw",
                "used_energy_mw",
                "group_energy_share_mw",
                "spare_energy_mw",
                "available_energy_for_steel_mw",
                "energy_required_mw",
            ]
            for key in preferred_energy_order:
                if key in energy:
                    label = key.replace("_", " ").title()
                    st.write(f"- **{label}:** {energy[key]}")
            for k, v in energy.items():
                if k not in preferred_energy_order:
                    st.write(f"- **{k.replace('_',' ').title()}:** {v}")
        else:
            st.write("No energy data.")

    st.markdown("---")

# end of app.py
