# decision_engine.py
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List

# Executive consulting-grade decision engine
# Documentation prioritized over inline comments.

# -------------------------
# Config / constants
# -------------------------
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

# -------------------------
# Small helpers
# -------------------------
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

# -------------------------
# Load mock data (defensive)
# -------------------------
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

# -------------------------
# Parse strategic query
# -------------------------
def _parse_query(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    out = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": 36, "debug": []}
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
            out["debug"].append("Failed parsing months; using 15")
    pp = re.search(r'payback.*?(?:less than|within|<)\s*(\d+)\s*(years|year)', q)
    if pp:
        try:
            out["max_payback_months"] = int(pp.group(1)) * 12
        except:
            out["debug"].append("Failed parsing payback; using 36 months")
    return out

# -------------------------
# Executive analysis helpers
# -------------------------
def _rank_by_roi(breakdown: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # ROI proxy = annual_margin / capex
    for p in breakdown:
        capex = float(p.get("capex_usd", 0)) or 1.0
        margin = float(p.get("annual_margin_usd", 0))
        p["roi_proxy"] = (margin / capex) if capex else 0.0
    return sorted(breakdown, key=lambda x: x["roi_proxy"], reverse=True)

def _stress_test_margin(margin_drop_pct: float, total_margin: float) -> Dict[str, Any]:
    stressed_margin = total_margin * (1 - margin_drop_pct)
    return {"stress_pct": margin_drop_pct, "stressed_margin": stressed_margin}

# -------------------------
# Main run_simulation (executive)
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query(query)
    debug: List[str] = parsed.get("debug", [])

    loaded = _load_mock_data()
    data = loaded.get("data", {})
    debug += loaded.get("debug", [])
    if loaded.get("path"):
        debug.append(f"Using mock file: {loaded.get('path')}")

    # retrieve site lists with safe defaults
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

    # infrastructure availability (group-level rules)
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

    # apply requested distribution
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

    # timeline estimate (executive-level durations)
    planning = 3
    procurement = max(2, int(round(2 + total_added_mtpa * 4)))
    implementation = max(3, int(round(4 + total_added_mtpa * 6)))
    commissioning = max(1, int(round(implementation * 0.25)))
    stabilization = max(1, int(round(commissioning * 0.5)))
    estimated_total_months = planning + procurement + implementation + commissioning + stabilization

    # validations against strategic query
    validations = {"checks": [], "passed": True}
    target_mtpa = parsed["target_mtpa"]
    if _approx_equal(total_added_mtpa, target_mtpa, rel_tol=0.01):
        validations["checks"].append({"name": "Target MTPA", "status": "pass", "detail": f"Added {total_added_mtpa:.3f} MTPA meets target {target_mtpa} MTPA"})
    else:
        validations["checks"].append({"name": "Target MTPA", "status": "fail", "detail": f"Added {total_added_mtpa:.3f} MTPA does not match target {target_mtpa} MTPA"})
        validations["passed"] = False

    max_payback = parsed.get("max_payback_months", 36)
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

    target_months = parsed.get("target_months", 15)
    if estimated_total_months <= target_months:
        validations["checks"].append({"name": "Schedule", "status": "pass", "detail": f"Estimated {estimated_total_months} months <= target {target_months} months"})
    else:
        validations["checks"].append({"name": "Schedule", "status": "fail", "detail": f"Estimated {estimated_total_months} months exceeds target {target_months} months"})
        validations["passed"] = False

    # executive analysis: rank plants by ROI (proxy), suggest Phase A (highest ROI)
    ranked = _rank_by_roi(breakdown)
    phase_a = [p["name"] for p in ranked[:2]]  # highest ROI plants for phase A
    phase_b = [p["name"] for p in ranked[2:]] if len(ranked) > 2 else []

    # stress-test margins (10% and 20% downside)
    stress_10 = _stress_test_margin(0.10, total_margin)
    stress_20 = _stress_test_margin(0.20, total_margin)

    # build executive recommendation (concise, prioritized)
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
        # ordered by priority and executive phrasing
        "Phase A (0–9 months): Deploy MES + targeted automation and modular EAF cells at highest-ROI plants (immediate OEE uplift).",
        "Parallel: Secure long-lead equipment purchase agreements (frame contracts) and pre-qualify suppliers to compress procurement.",
        "Phase B (6–15 months): Execute raw-material handling upgrades, stockyard automation and port corridor arrangements to protect commercial cargo throughput.",
        "Energy program: negotiate short-term PPAs + implement WHR & substation uprates; include battery buffering where marginal cost permits.",
        "Finance: Stage CAPEX by ROI (Phase A first). Create a project-level PMO with weekly gates and KPI dashboards (delivery, cost, energy, port throughput).",
        "Risk & Mitigation: Pre-negotiated 3PL and temporary berth leases; contingency PPA tranche; supplier SLAs with penalties for key long-lead items."
    ]

    # rationales in executive tone; explicitly explain why each recommendation
    rationale_bullets: List[str] = []
    rationale_bullets.append("MES + targeted automation: Rapidly improves OEE and reduces commissioning ramp time — shortest path to cash flow improvement and payback acceleration.")
    rationale_bullets.append("Modular EAF approach: Faster installation, modular commissioning, better capital efficiency vs full greenfield expansion.")
    rationale_bullets.append("Supplier & procurement controls: Compresses critical path by aligning lead times and de-risking long-lead items via frame contracts.")
    rationale_bullets.append("Port corridor & logistics orchestration: Ensures commercial cargo SLAs are protected while supporting increased raw-material flow.")
    rationale_bullets.append("Energy program (PPA + WHR + buffering): Reduces exposure to grid deficits and improves operating margins, directly shortening payback.")
    rationale_bullets.append(f"Staging recommendation: Phase A targets {', '.join(phase_a)} to maximize early ROI; Phase B handles remaining plants to smooth capex and schedule risk.")

    # append validations (evidence statements) — show pass/fail
    for chk in validations["checks"]:
        status = chk["status"].upper()
        rationale_bullets.append(f"Validation — {chk['name']}: {status} — {chk['detail']}")

    # targeted mitigations when fails occur
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

    # confidence scoring (penalize failures and stress)
    confidence = START_CONFIDENCE
    for chk in validations["checks"]:
        if chk["status"] == "fail":
            confidence -= 10
    # penalize stressed downside risk (10% margin drop)
    if stress_10["stressed_margin"] <= 0:
        confidence -= 5
    confidence = max(confidence, MIN_CONFIDENCE)

    # roadmap phases and per-plant schedule (staggered)
    per_plant_schedule = []
    sorted_breakdown = _rank_by_roi(breakdown)
    offset = 0
    for p in sorted_breakdown:
        share = p["added_tpa"] / (total_added_tpa or 1)
        proc = max(1, int(round(procurement * share)))
        impl = max(1, int(round(implementation * share)))
        comm = max(1, int(round(commissioning * share)))
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

    # assemble result
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

# quick smoke run
if __name__ == "__main__":
    q = "Increase steel production by 2 MTPA in 15 months; payback less than 3 years"
    import pprint
    pprint.pprint(run_simulation(q))
