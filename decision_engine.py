# File: decision_engine.py
# Replace your existing decision_engine.py with this file.

from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List, Optional

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

START_CONFIDENCE = 85
MIN_CONFIDENCE = 50

USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]  # SP1..SP4

# Candidate mock locations
CANDIDATE_MOCKS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

# Uploaded doc path (user file)
OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"

# -------------------------
# Helpers
# -------------------------
def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

# -------------------------
# Mock loader (defensive)
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
        "steel": {"plants":[
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]},
        "ports":{"ports":[
            {"id":"P1","capacity_tpa":2_000_000},
            {"id":"P2","capacity_tpa":1_800_000},
            {"id":"P3","capacity_tpa":1_600_000},
            {"id":"P4","capacity_tpa":1_400_000},
        ]},
        "energy":{"plants":[
            {"id":"E1","capacity_mw":500},
            {"id":"E2","capacity_mw":450},
            {"id":"E3","capacity_mw":400},
        ]}
    }
    return {"data": defaults, "debug": debug, "path": None}

# -------------------------
# Parse query
# -------------------------
def _parse_query(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    out = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": 36, "debug": []}
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            out["target_mtpa"] = float(m.group(1))
        except:
            out["debug"].append("Could not parse target MTPA; using default 2.0")
    mm = re.search(r'(\d{1,3})\s*(?:months|month)', q)
    if mm:
        try:
            out["target_months"] = int(mm.group(1))
        except:
            out["debug"].append("Could not parse target months; using default 15")
    pp = re.search(r'payback.*?(?:less than|within|<)\s*(\d+)\s*(years|year)', q)
    if pp:
        try:
            out["max_payback_months"] = int(pp.group(1)) * 12
        except:
            out["debug"].append("Could not parse payback years; using default 36 months")
    return out

# -------------------------
# Validation helpers
# -------------------------
def _approx_equal(a: float, b: float, rel_tol: float = 0.05) -> bool:
    """Return True if a approx equals b within relative tolerance (5% default)"""
    if b == 0:
        return abs(a) < 1e-6
    return abs(a - b) <= max(rel_tol * abs(b), 1e-6)

# -------------------------
# Main simulation & decision logic
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query(query)
    debug = parsed.get("debug", [])

    # load data
    loaded = _load_mock_data()
    data = loaded.get("data", {})
    debug += loaded.get("debug", [])
    if loaded.get("path"):
        debug.append(f"Using mock file: {loaded.get('path')}")

    # steel plants
    plants = (data.get("steel") or {}).get("plants") or []
    if len(plants) < 4:
        debug.append("Steel plant data missing/incomplete; applying 4-plant defaults.")
        plants = [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]

    # ports and energy
    ports = (data.get("ports") or {}).get("ports") or []
    if not ports:
        debug.append("Ports data missing; using defaults.")
        ports = [{"id":"P1","capacity_tpa":2_000_000},{"id":"P2","capacity_tpa":1_800_000},{"id":"P3","capacity_tpa":1_600_000},{"id":"P4","capacity_tpa":1_400_000}]
    energy_plants = (data.get("energy") or {}).get("plants") or []
    if not energy_plants:
        debug.append("Energy data missing; using defaults.")
        energy_plants = [{"id":"E1","capacity_mw":500},{"id":"E2","capacity_mw":450},{"id":"E3","capacity_mw":400}]

    # compute port & energy availability
    total_port_capacity = sum(int(p.get("capacity_tpa", 0)) for p in ports)
    used_port = PORT_UTILIZATION * total_port_capacity
    group_port = used_port * PORT_GROUP_SHARE_OF_USED
    spare_port = total_port_capacity - used_port
    available_port_for_steel = spare_port + group_port

    total_energy_capacity = sum(float(p.get("capacity_mw", 0)) for p in energy_plants)
    used_energy = ENERGY_UTILIZATION * total_energy_capacity
    grid_energy = used_energy * ENERGY_GRID_SHARE_OF_USED
    group_energy = used_energy - grid_energy
    spare_energy = total_energy_capacity - used_energy
    available_energy_for_steel = spare_energy + group_energy

    # apply distribution exactly
    num_plants = min(4, len(plants))
    dist_mtpa = USER_DISTRIBUTION_MTPA[:num_plants]
    added_tpa_list = [int(round(m * 1_000_000)) for m in dist_mtpa]

    breakdown = []
    total_added_tpa = 0
    total_capex = 0
    total_margin = 0

    for idx in range(num_plants):
        p = plants[idx]
        added = added_tpa_list[idx]
        mtpa_added = added / 1_000_000.0
        capex = _capex_for_mtpa(mtpa_added)
        margin = _annual_margin_for_tpa(added)
        payback_months = None
        if margin > 0:
            payback_months = (capex / margin) * 12.0

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
            # hiring estimate kept for UI (same heuristic)
            "hiring_estimate": {
                "operators": int(max(1, round(mtpa_added * 10)) * 5),
                "maintenance": int(max(1, round(mtpa_added * 10)) * 2),
                "engineers": int(max(1, round(mtpa_added * 10)) * 1),
                "project_managers": 1
            }
        })
        total_added_tpa += added
        total_capex += capex
        total_margin += margin

    total_added_mtpa = total_added_tpa / 1_000_000.0
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)
    port_required_tpa = int(round(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE))

    aggregated_payback_months = None
    if total_margin > 0:
        aggregated_payback_months = (total_capex / total_margin) * 12.0

    # timeline estimate
    planning = 3
    procurement = max(2, int(round(2 + total_added_mtpa * 4)))
    implementation = max(3, int(round(4 + total_added_mtpa * 6)))
    commissioning = max(1, int(round(implementation * 0.25)))
    stabilization = max(1, int(round(commissioning * 0.5)))
    estimated_total_months = planning + procurement + implementation + commissioning + stabilization

    # -------------------------
    # Validation: check alignment with strategic query
    # -------------------------
    validations = {"checks": [], "passed": True}
    # 1) Target MTPA
    target_mtpa = parsed["target_mtpa"]
    if _approx_equal(total_added_mtpa, target_mtpa, rel_tol=0.01):
        validations["checks"].append({"name":"Target MTPA","status":"pass","detail":f"Added {total_added_mtpa:.3f} MTPA meets target {target_mtpa} MTPA"})
    else:
        validations["checks"].append({"name":"Target MTPA","status":"fail","detail":f"Added {total_added_mtpa:.3f} MTPA does not match target {target_mtpa} MTPA"})
        validations["passed"] = False

    # 2) Payback
    max_payback = parsed.get("max_payback_months", 36)
    if aggregated_payback_months is not None and aggregated_payback_months <= max_payback:
        validations["checks"].append({"name":"Payback","status":"pass","detail":f"Aggregated payback {aggregated_payback_months:.1f} months <= requested {max_payback} months"})
    elif aggregated_payback_months is None:
        validations["checks"].append({"name":"Payback","status":"fail","detail":"Unable to compute aggregated payback (zero margin)."})
        validations["passed"] = False
    else:
        validations["checks"].append({"name":"Payback","status":"fail","detail":f"Aggregated payback {aggregated_payback_months:.1f} months exceeds requested {max_payback} months"})
        validations["passed"] = False

    # 3) Energy
    if energy_required_mw <= available_energy_for_steel + 1e-6:
        validations["checks"].append({"name":"Energy","status":"pass","detail":f"Needs {energy_required_mw:.2f} MW; available {available_energy_for_steel:.2f} MW"})
    else:
        validations["checks"].append({"name":"Energy","status":"fail","detail":f"Needs {energy_required_mw:.2f} MW; available {available_energy_for_steel:.2f} MW"})
        validations["passed"] = False

    # 4) Ports
    if port_required_tpa <= available_port_for_steel + 1e-6:
        validations["checks"].append({"name":"Ports","status":"pass","detail":f"Requires {port_required_tpa:,} tpa; available {int(available_port_for_steel):,} tpa"})
    else:
        validations["checks"].append({"name":"Ports","status":"fail","detail":f"Requires {port_required_tpa:,} tpa; available {int(available_port_for_steel):,} tpa"})
        validations["passed"] = False

    # 5) Schedule
    target_months = parsed.get("target_months", 15)
    if estimated_total_months <= target_months:
        validations["checks"].append({"name":"Schedule","status":"pass","detail":f"Estimated {estimated_total_months} months <= target {target_months} months"})
    else:
        validations["checks"].append({"name":"Schedule","status":"fail","detail":f"Estimated {estimated_total_months} months exceeds target {target_months} months"})
        validations["passed"] = False

    # -------------------------
    # Build recommendation and richer rationale (evidence-based)
    # -------------------------
    headline = f"Proposed Upgrade: +{total_added_mtpa:.3f} MTPA across {num_plants} plants"
    metrics = {
        "added_tpa": int(total_added_tpa),
        "added_mtpa": round(total_added_mtpa, 3),
        "investment_usd": int(round(total_capex)),
        "estimated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months,1),
        "energy_required_mw": round(energy_required_mw,2),
        "port_throughput_required_tpa": int(port_required_tpa),
    }

    # Actions (same core set, but ordered by validations)
    actions = [
        "Deploy MES & automation (improve OEE, reduce ramp risk).",
        "Upgrade/add modular EAF or BOF interface as needed (fastest capacity add).",
        "Upgrade raw material handling (pelletizing, conveyors, stockyard automation).",
        "Install WHR, substation upgrades and VFDs to support additional MW demand.",
        "Coordinate ports schedule; stagger shipments and reserve berth windows.",
        "Negotiate short-term PPAs or temporary generation if energy gap detected.",
        "Consider staged rollout (phase 1: highest ROI plants) to meet payback constraints."
    ]

    # Rationale: richer, evidence-based — NOTE: remove final assumptions line as requested
    rationale_bullets: List[str] = []
    # Explain checks and why recommendation chosen
    rationale_bullets.append(f"Target check: added {total_added_mtpa:.3f} MTPA — {'meets' if _approx_equal(total_added_mtpa, target_mtpa,0.01) else 'does NOT meet'} requested {target_mtpa} MTPA.")
    rationale_bullets.append(f"Payback check: aggregated payback is {aggregated_payback_months:.1f} months; this {'meets' if aggregated_payback_months and aggregated_payback_months <= max_payback else 'exceeds'} the requested payback of {max_payback} months.")
    rationale_bullets.append(f"Energy: requires {energy_required_mw:.2f} MW; available (spare + group share) = {available_energy_for_steel:.2f} MW — {'sufficient' if energy_required_mw <= available_energy_for_steel else 'shortfall detected'}; recommend PPA or staged work if short.")
    rationale_bullets.append(f"Ports: requires {port_required_tpa:,} tpa throughput; available (spare + group share) = {int(available_port_for_steel):,} tpa — {'sufficient' if port_required_tpa <= available_port_for_steel else 'shortfall detected'}; recommend staging shipments or 3PL if short.")
    rationale_bullets.append(f"Schedule: estimated {estimated_total_months} months vs target {target_months} months — {'feasible' if estimated_total_months <= target_months else 'schedule risk; consider overlap/compression or staged approach'}")
    rationale_bullets.append("Recommendation favors modular upgrades and MES first to minimize time-to-benefit and protect commercial operations (ports & grid commitments).")

    # Enrich with explicit mitigations when checks fail
    mitigations: List[str] = []
    for check in validations["checks"]:
        if check["status"] == "fail":
            if check["name"] == "Payback":
                mitigations.append("Mitigation: stage investment (target highest ROI plants first), renegotiate equipment prices, or seek margin uplift via product mix.")
            if check["name"] == "Energy":
                mitigations.append("Mitigation: sign short-term PPA, rent peak generation, or reduce peak load through process efficiency.")
            if check["name"] == "Ports":
                mitigations.append("Mitigation: contract 3PL, lease temporary berth, or stagger import/export windows.")
            if check["name"] == "Schedule":
                mitigations.append("Mitigation: add contractors, compress procurement by pre-negotiating long-lead items, or stage implementation.")
            if check["name"] == "Target MTPA":
                mitigations.append("Mitigation: re-distribute increases among plants or accept staged delivery to reach target in phases.")

    if mitigations:
        rationale_bullets.append("Mitigations / alternatives:")
        rationale_bullets += mitigations

    # Confidence scoring: penalize for each failed validation
    confidence = START_CONFIDENCE
    for check in validations["checks"]:
        if check["status"] == "fail":
            confidence -= 10
    confidence = max(confidence, MIN_CONFIDENCE)

    # Build roadmap per-plant schedule (same approach as earlier)
    per_plant_schedule = []
    sorted_breakdown = sorted(breakdown, key=lambda x: x["added_tpa"], reverse=True)
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

    # Construct final structured result
    result = {
        "recommendation": {
            "headline": headline,
            "summary": f"Add {total_added_mtpa:.3f} MTPA across {num_plants} plants with actions focused on MES, modular EAF, WHR and logistics.",
            "metrics": metrics,
            "actions": actions,
            "distribution": [{"plant": d["name"], "added_mtpa": d["added_mtpa"], "capex_usd": d["capex_usd"]} for d in breakdown]
        },
        "roadmap": {
            "phases": [
                {"phase":"Planning","months":planning,"notes":"Engineering & permits"},
                {"phase":"Procurement","months":procurement,"notes":"Long-lead orders"},
                {"phase":"Implementation","months":implementation,"notes":"Installation & integration"},
                {"phase":"Commissioning","months":commissioning,"notes":"Cold/hot commissioning"},
                {"phase":"Stabilization","months":stabilization,"notes":"Ramp & optimization"},
            ],
            "per_plant_schedule": per_plant_schedule
        },
        "rationale": {
            "bullets": rationale_bullets
            # NOTE: intentionally removed final "assumptions" line per request
        },
        "validations": validations,
        "metrics": {
            "total_capex_usd": int(round(total_capex)),
            "total_annual_margin_usd": int(round(total_margin)),
            "aggregated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months,1),
            "energy_required_mw": round(energy_required_mw,2),
            "port_required_tpa": int(port_required_tpa),
            "estimated_total_months": estimated_total_months
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
                "group_port_share_tpa": group_port,
                "spare_port_tpa": spare_port,
                "available_port_for_steel_tpa": available_port_for_steel,
                "port_throughput_required_tpa": port_required_tpa
            },
            "energy": {
                "total_energy_capacity_mw": total_energy_capacity,
                "used_energy_mw": used_energy,
                "group_energy_share_mw": group_energy,
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
    # quick smoke test
    query = "Increase steel production by 2 MTPA in 15 months; payback less than 3 years"
    import pprint
    pprint.pprint(run_simulation(query))
