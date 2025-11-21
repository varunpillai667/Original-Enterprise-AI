# =========================
# File: decision_engine.py
# =========================
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List, Optional

# -------------------------
# Config
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

USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]

CANDIDATE_MOCKS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

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

def _approx_equal(a: float, b: float, rel_tol: float = 0.01) -> bool:
    if b == 0:
        return abs(a) < 1e-6
    return abs(a - b) <= max(rel_tol * abs(b), 1e-6)

# -------------------------
# Load mock data
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
    debug.append("No mock_data.json found; using defaults.")
    defaults = {
        "steel": {"plants":[
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]},
        "ports":{"ports":[
            {"id":"P1","capacity_tpa":2_000_000},{"id":"P2","capacity_tpa":1_800_000},{"id":"P3","capacity_tpa":1_600_000},{"id":"P4","capacity_tpa":1_400_000}
        ]},
        "energy":{"plants":[
            {"id":"E1","capacity_mw":500},{"id":"E2","capacity_mw":450},{"id":"E3","capacity_mw":400}
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
# Run simulation
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query(query)
    debug = parsed.get("debug", [])

    loaded = _load_mock_data()
    data = loaded.get("data", {})
    debug += loaded.get("debug", [])
    if loaded.get("path"):
        debug.append(f"Using mock file: {loaded.get('path')}")

    plants = (data.get("steel") or {}).get("plants") or []
    if len(plants) < 4:
        debug.append("Insufficient steel plant data; applying defaults.")
        plants = [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]

    ports = (data.get("ports") or {}).get("ports") or []
    if not ports:
        debug.append("Ports missing; using defaults.")
        ports = [{"id":"P1","capacity_tpa":2_000_000},{"id":"P2","capacity_tpa":1_800_000},{"id":"P3","capacity_tpa":1_600_000},{"id":"P4","capacity_tpa":1_400_000}]

    energy_plants = (data.get("energy") or {}).get("plants") or []
    if not energy_plants:
        debug.append("Energy missing; using defaults.")
        energy_plants = [{"id":"E1","capacity_mw":500},{"id":"E2","capacity_mw":450},{"id":"E3","capacity_mw":400}]

    # compute availability
    total_port_capacity = sum(int(p.get("capacity_tpa",0)) for p in ports)
    used_port = PORT_UTILIZATION * total_port_capacity
    group_port_share = used_port * PORT_GROUP_SHARE_OF_USED
    spare_port = total_port_capacity - used_port
    available_port_for_steel = spare_port + group_port_share

    total_energy_capacity = sum(float(p.get("capacity_mw",0)) for p in energy_plants)
    used_energy = ENERGY_UTILIZATION * total_energy_capacity
    grid_energy_share = used_energy * ENERGY_GRID_SHARE_OF_USED
    group_energy_share = used_energy - grid_energy_share
    spare_energy = total_energy_capacity - used_energy
    available_energy_for_steel = spare_energy + group_energy_share

    # apply distribution
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
        payback_months = None if margin == 0 else (capex / margin) * 12.0
        hires_units = max(1, int(round(mtpa_added * 10)))
        breakdown.append({
            "id": p.get("id"),
            "name": p.get("name", p.get("id","")),
            "current_capacity_tpa": int(p.get("current_capacity_tpa",0)),
            "added_tpa": int(added),
            "added_mtpa": round(mtpa_added,3),
            "new_capacity_tpa": int(p.get("current_capacity_tpa",0) + added),
            "capex_usd": int(round(capex)),
            "annual_margin_usd": int(round(margin)),
            "payback_months": None if payback_months is None else round(payback_months,1),
            "hiring_estimate": {"operators": hires_units*5, "maintenance": hires_units*2, "engineers": hires_units*1, "project_managers":1}
        })
        total_added_tpa += added
        total_capex += capex
        total_margin += margin

    total_added_mtpa = total_added_tpa / 1_000_000.0
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)
    port_required_tpa = int(round(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE))

    aggregated_payback_months = None if total_margin == 0 else (total_capex / total_margin) * 12.0

    # timeline
    planning = 3
    procurement = max(2, int(round(2 + total_added_mtpa * 4)))
    implementation = max(3, int(round(4 + total_added_mtpa * 6)))
    commissioning = max(1, int(round(implementation * 0.25)))
    stabilization = max(1, int(round(commissioning * 0.5)))
    estimated_total_months = planning + procurement + implementation + commissioning + stabilization

    # validations
    validations = {"checks": [], "passed": True}
    target_mtpa = parsed["target_mtpa"]
    if _approx_equal(total_added_mtpa, target_mtpa, rel_tol=0.01):
        validations["checks"].append({"name":"Target MTPA","status":"pass","detail":f"Added {total_added_mtpa:.3f} MTPA meets target {target_mtpa} MTPA"})
    else:
        validations["checks"].append({"name":"Target MTPA","status":"fail","detail":f"Added {total_added_mtpa:.3f} MTPA does not match target {target_mtpa} MTPA"})
        validations["passed"] = False

    max_payback = parsed.get("max_payback_months",36)
    if aggregated_payback_months is not None and aggregated_payback_months <= max_payback:
        validations["checks"].append({"name":"Payback","status":"pass","detail":f"Aggregated payback {aggregated_payback_months:.1f} months <= {max_payback} months"})
    elif aggregated_payback_months is None:
        validations["checks"].append({"name":"Payback","status":"fail","detail":"Unable to compute aggregated payback (zero margin)."})
        validations["passed"] = False
    else:
        validations["checks"].append({"name":"Payback","status":"fail","detail":f"Aggregated payback {aggregated_payback_months:.1f} months exceeds {max_payback} months"})
        validations["passed"] = False

    if energy_required_mw <= available_energy_for_steel + 1e-6:
        validations["checks"].append({"name":"Energy","status":"pass","detail":f"Needs {energy_required_mw:.2f} MW; available {available_energy_for_steel:.2f} MW"})
    else:
        validations["checks"].append({"name":"Energy","status":"fail","detail":f"Needs {energy_required_mw:.2f} MW; available {available_energy_for_steel:.2f} MW"})
        validations["passed"] = False

    if port_required_tpa <= available_port_for_steel + 1e-6:
        validations["checks"].append({"name":"Ports","status":"pass","detail":f"Requires {port_required_tpa:,} tpa; available {int(available_port_for_steel):,} tpa"})
    else:
        validations["checks"].append({"name":"Ports","status":"fail","detail":f"Requires {port_required_tpa:,} tpa; available {int(available_port_for_steel):,} tpa"})
        validations["passed"] = False

    target_months = parsed.get("target_months",15)
    if estimated_total_months <= target_months:
        validations["checks"].append({"name":"Schedule","status":"pass","detail":f"Estimated {estimated_total_months} months <= target {target_months} months"})
    else:
        validations["checks"].append({"name":"Schedule","status":"fail","detail":f"Estimated {estimated_total_months} months exceeds target {target_months} months"})
        validations["passed"] = False

    # Build recommendation & rationale (richer)
    headline = f"Proposed Upgrade: +{total_added_mtpa:.3f} MTPA across {num_plants} plants"
    metrics = {
        "added_tpa": int(total_added_tpa),
        "added_mtpa": round(total_added_mtpa,3),
        "investment_usd": int(round(total_capex)),
        "estimated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months,1),
        "energy_required_mw": round(energy_required_mw,2),
        "port_throughput_required_tpa": int(port_required_tpa),
    }

    # core actions
    actions = [
        "Deploy MES & automation to reduce OEE losses and accelerate ramp.",
        "Upgrade / add modular EAF capacity or BOF interface for fast capacity add.",
        "Improve raw-material handling (pelletizing, automated feeders, stockyards).",
        "Install WHR and upgrade substations & VFDs to reduce energy cost and support extra MW.",
        "Coordinate with Ports EM to reserve berth windows and stagger shipments to protect commercial cargo.",
        "Arrange PPAs or temporary generation if energy gap detected; consider staged implementation for capex control."
    ]

    # rationale: explain *why* each recommendation
    rationale_bullets: List[str] = []
    rationale_bullets.append(f"MES & automation: reduces OEE losses, shortens commissioning time and improves yield — directly improves time-to-market and payback.")
    rationale_bullets.append(f"Modular EAF / BOF interface: chosen because modular EAFs can be installed faster than large greenfield expansions, enabling the +{total_added_mtpa:.3f} MTPA increase within the requested timeframe.")
    rationale_bullets.append("Raw-material handling upgrades: minimize logistics delays and berth dwell times at ports, protecting commercial cargo SLAs and reducing inventory days.")
    rationale_bullets.append("Waste-Heat-Recovery & substation upgrades: reduce incremental operating cost (fuel/electricity), thereby improving project payback and reducing required external energy.")
    rationale_bullets.append("Port coordination: staging shipments and reserving berth windows prevents interference with commercial cargo and ensures supply of imports/exports for the steel ramp.")
    rationale_bullets.append("Energy mitigations (PPA / rental gen): practical short-term levers for addressing any energy shortfall without delaying production.")
    for chk in validations["checks"]:
        status = chk["status"].upper()
        rationale_bullets.append(f"Validation - {chk['name']}: {status} — {chk['detail']}")

    mitigations: List[str] = []
    for chk in validations["checks"]:
        if chk["status"] == "fail":
            if chk["name"] == "Payback":
                mitigations.append("Mitigation: stage investments (highest ROI plants first), reduce scope, or pursue cost reductions on equipment.")
            if chk["name"] == "Energy":
                mitigations.append("Mitigation: secure PPAs, temporary generation or efficiency measures to reduce peak demand.")
            if chk["name"] == "Ports":
                mitigations.append("Mitigation: 3PL contracts, temporary berth leasing, and shipment staggering.")
            if chk["name"] == "Schedule":
                mitigations.append("Mitigation: add contractors, parallelize some procurement/installation tasks, or stage the program.")
            if chk["name"] == "Target MTPA":
                mitigations.append("Mitigation: redistribute target across plants or accept phased delivery to meet timeline.")

    if mitigations:
        rationale_bullets.append("Mitigations / Alternatives:")
        rationale_bullets += mitigations

    confidence = START_CONFIDENCE
    for chk in validations["checks"]:
        if chk["status"] == "fail":
            confidence -= 10
    confidence = max(confidence, MIN_CONFIDENCE)

    # per-plant schedule (staggered)
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

    result = {
        "recommendation": {
            "headline": headline,
            "summary": f"Add {total_added_mtpa:.3f} MTPA across {num_plants} plants focused on modular, fast-implementing upgrades.",
            "metrics": metrics,
            "actions": actions,
            "distribution": [{"plant": d["name"], "added_mtpa": d["added_mtpa"], "capex_usd": d["capex_usd"]} for d in breakdown]
        },
        "roadmap": {
            "phases": [
                {"phase":"Planning","months":planning,"notes":"Engineering & permits"},
                {"phase":"Procurement","months":procurement,"notes":"Order long-lead items"},
                {"phase":"Implementation","months":implementation,"notes":"Installation & integration"},
                {"phase":"Commissioning","months":commissioning,"notes":"Cold/hot commissioning"},
                {"phase":"Stabilization","months":stabilization,"notes":"Ramp & optimization"},
            ],
            "per_plant_schedule": per_plant_schedule
        },
        "rationale": {"bullets": rationale_bullets},
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
            "energy_info": {"total_energy_capacity_mw": total_energy_capacity, "used_energy_mw": used_energy}
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
    q = "Increase steel production by 2 MTPA in 15 months; payback less than 3 years"
    import pprint
    pprint.pprint(run_simulation(q))
