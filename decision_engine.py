# decision_engine.py
"""
Decision engine — produces actionable Recommendation, Roadmap, and Rationale.
Handles exact distribution, port & energy constraints, capex/margin/payback,
hiring estimates, roadmap, rationale and debug notes.
"""

from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List, Optional

# -------------------------
# Tunable constants
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
MIN_CONFIDENCE = 70
ENFORCED_PAYBACK_MONTHS = 36

USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]  # SP1..SP4

CANDIDATE_MOCKS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/Original-Enterprise-AI/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"
CONCEPT_PDF = "/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf"

# -------------------------
# Small helpers
# -------------------------
def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

# -------------------------
# Robust mock loader
# -------------------------
def _load_mock_data() -> Dict[str, Any]:
    debug: List[str] = []
    for p in CANDIDATE_MOCKS:
        try:
            if p.exists():
                with open(p, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                debug.append(f"Loaded mock_data.json from: {str(p)}")
                return {"data": data, "debug": debug, "path": str(p)}
        except Exception as exc:
            debug.append(f"Found file {str(p)} but failed to read JSON: {exc}")
    # fallback defaults
    debug.append("No mock_data.json found; using internal defaults.")
    defaults = {
        "steel": {
            "plants": [
                {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
                {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
                {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
                {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
            ]
        },
        "ports": {
            "ports": [
                {"id":"P1","name":"Port 1","capacity_tpa":2_000_000},
                {"id":"P2","name":"Port 2","capacity_tpa":1_800_000},
                {"id":"P3","name":"Port 3","capacity_tpa":1_600_000},
                {"id":"P4","name":"Port 4","capacity_tpa":1_400_000},
            ]
        },
        "energy": {
            "plants": [
                {"id":"E1","name":"Power Plant 1","capacity_mw":500},
                {"id":"E2","name":"Power Plant 2","capacity_mw":450},
                {"id":"E3","name":"Power Plant 3","capacity_mw":400},
            ]
        }
    }
    return {"data": defaults, "debug": debug, "path": None}

# -------------------------
# Parse query safely
# -------------------------
def _parse_query_for_constraints(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    result = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": ENFORCED_PAYBACK_MONTHS, "debug": []}
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            result["target_mtpa"] = float(m.group(1))
        except Exception:
            result["debug"].append("Failed to parse target MTPA; default used (2.0).")
    m2 = re.search(r'(\d{1,3})\s*(?:months|month)\b', q)
    if m2:
        try:
            result["target_months"] = int(m2.group(1))
        except Exception:
            result["debug"].append("Failed to parse months; default used (15).")
    m3 = re.search(r'payback.*?(?:less than|<|within)\s*(\d+)\s*(years|year)', q)
    if m3:
        try:
            result["max_payback_months"] = int(m3.group(1)) * 12
        except Exception:
            result["debug"].append("Failed to parse payback; default used.")
    return result

# -------------------------
# Section builders
# -------------------------
def _build_recommendation_section(headline: str, added_tpa: int, investment: float, payback: Optional[float], energy_mw: float, confidence: int) -> Dict[str, Any]:
    added_mtpa = round(added_tpa / 1_000_000.0, 3)
    metrics = {
        "added_tpa": int(added_tpa),
        "added_mtpa": added_mtpa,
        "investment_usd": int(round(investment)),
        "estimated_payback_months": None if payback is None else round(payback, 1),
        "energy_required_mw": round(energy_mw, 2),
        "confidence_pct": confidence,
    }
    summary = f"Proposed Upgrade: +{added_mtpa:.3f} MTPA steel capacity across Group X Steel Division (investment ${metrics['investment_usd']:,})."
    return {"headline": headline, "summary": summary, "metrics": metrics}

def _build_roadmap_section(timeline: Dict[str, int], per_plant_breakdown: List[Dict[str, Any]]) -> Dict[str, Any]:
    phases = [
        {"phase":"Planning","months":timeline.get("planning_months",2),"notes":"Engineering, permits, procurement."},
        {"phase":"Procurement","months":timeline.get("procurement_months",3),"notes":"Long-lead orders, vendor contracts."},
        {"phase":"Implementation","months":timeline.get("implementation_months",6),"notes":"Installation, civil works, electrical."},
        {"phase":"Commissioning","months":timeline.get("commissioning_months",2),"notes":"Cold/hot commissioning, training."},
        {"phase":"Stabilization","months":timeline.get("stabilization_months",2),"notes":"Ramp-up, QA, steady-state operations."},
    ]
    actions = [f"{p['name']}: add {p['added_tpa']:,} tpa (CapEx ${int(p.get('capex_usd',0)):,})" for p in per_plant_breakdown]
    return {"phases":phases, "per_plant_actions":actions}

def _build_rationale_section(bullets: List[str], assumptions: Dict[str, Any], debug_lines: List[str]) -> Dict[str, Any]:
    b = list(bullets)
    b.append("Assumptions are listed below and used for resource feasibility and payback calculations.")
    return {"bullets": b, "assumptions": assumptions, "debug": debug_lines, "references":{"operational_flow_doc":OPERATIONAL_FLOW_DOC, "concept_pdf":CONCEPT_PDF}}

# -------------------------
# Main: run_simulation
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query_for_constraints(query)
    debug_lines: List[str] = parsed.get("debug", [])

    # load mock data (defensive)
    loaded = _load_mock_data()
    data = loaded.get("data", {})
    debug_lines += loaded.get("debug", [])
    if loaded.get("path"):
        debug_lines.append(f"Using mock_data.json at: {loaded.get('path')}")

    # steel plants (defensive)
    steel_section = data.get("steel") or {}
    plants = steel_section.get("plants") or []
    if not plants or len(plants) < 4:
        debug_lines.append("Steel plants missing or incomplete; applying 4-plant defaults.")
        plants = [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]

    # ports (defensive)
    ports_section = data.get("ports") or {}
    ports_list = ports_section.get("ports") or []
    if not ports_list:
        debug_lines.append("Ports data missing; using default port capacities.")
        ports_list = [
            {"id":"P1","name":"Port 1","capacity_tpa":2_000_000},
            {"id":"P2","name":"Port 2","capacity_tpa":1_800_000},
            {"id":"P3","name":"Port 3","capacity_tpa":1_600_000},
            {"id":"P4","name":"Port 4","capacity_tpa":1_400_000},
        ]

    # energy (defensive)
    energy_section = data.get("energy") or {}
    energy_list = energy_section.get("plants") or []
    if not energy_list:
        debug_lines.append("Energy plant data missing; using default capacities.")
        energy_list = [
            {"id":"E1","name":"Power Plant 1","capacity_mw":500},
            {"id":"E2","name":"Power Plant 2","capacity_mw":450},
            {"id":"E3","name":"Power Plant 3","capacity_mw":400},
        ]

    # compute port & energy availability
    total_port_capacity = sum(int(p.get("capacity_tpa", 0)) for p in ports_list)
    used_port = PORT_UTILIZATION * total_port_capacity
    group_port_share = used_port * PORT_GROUP_SHARE_OF_USED
    spare_port = total_port_capacity - used_port
    available_port_for_steel = spare_port + group_port_share

    total_energy_capacity = sum(float(p.get("capacity_mw", 0)) for p in energy_list)
    used_energy = ENERGY_UTILIZATION * total_energy_capacity
    grid_energy_share = used_energy * ENERGY_GRID_SHARE_OF_USED
    group_energy_share = used_energy - grid_energy_share
    spare_energy = total_energy_capacity - used_energy
    available_energy_for_steel = spare_energy + group_energy_share

    # apply exact distribution
    num_plants = min(4, len(plants))
    dist_mtpa = USER_DISTRIBUTION_MTPA[:num_plants]
    added_tpa_list = [int(round(m * 1_000_000)) for m in dist_mtpa]

    per_plant_breakdown: List[Dict[str, Any]] = []
    total_investment = 0.0
    total_annual_margin = 0.0

    # hiring ratios per 0.1 MTPA
    OPS_PER_0_1 = 5
    MAINT_PER_0_1 = 2
    ENG_PER_0_1 = 1
    PM_PER_PROJECT = 1

    for idx in range(num_plants):
        p = plants[idx]
        added = added_tpa_list[idx]
        added_mtpa = added / 1_000_000.0
        capex = _capex_for_mtpa(added_mtpa)
        annual_margin = _annual_margin_for_tpa(added)
        payback_months = None if annual_margin == 0 else (capex / annual_margin) * 12.0

        units_0_1 = max(1, int(round(added_mtpa * 10)))
        ops_needed = units_0_1 * OPS_PER_0_1
        maint_needed = units_0_1 * MAINT_PER_0_1
        eng_needed = units_0_1 * ENG_PER_0_1
        pm_needed = PM_PER_PROJECT

        per_plant_breakdown.append({
            "id": p.get("id"),
            "name": p.get("name", p.get("id", "")),
            "current_capacity_tpa": int(p.get("current_capacity_tpa", 0)),
            "added_tpa": added,
            "added_mtpa": round(added_mtpa, 3),
            "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + added),
            "capex_usd": int(round(capex)),
            "annual_margin_usd": int(round(annual_margin)),
            "payback_months": None if payback_months is None else round(payback_months, 1),
            "hiring_estimate": {"operators": ops_needed, "maintenance": maint_needed, "engineers": eng_needed, "project_managers": pm_needed}
        })
        total_investment += capex
        total_annual_margin += annual_margin

    total_added_tpa = sum(p["added_tpa"] for p in per_plant_breakdown)
    total_added_mtpa = total_added_tpa / 1_000_000.0
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)
    port_throughput_required_tpa = int(round(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE))

    aggregated_payback_months: Optional[float] = None
    if total_annual_margin > 0:
        aggregated_payback_months = (total_investment / total_annual_margin) * 12.0

    # timeline estimates
    planning_months = 3
    procurement_months = max(2, int(round(2 + total_added_mtpa * 4)))
    implementation_months = max(3, int(round(4 + total_added_mtpa * 6)))
    commissioning_months = max(1, int(round(implementation_months * 0.25)))
    stabilization_months = max(1, int(round(commissioning_months * 0.5)))
    total_estimated_months = planning_months + procurement_months + implementation_months + commissioning_months + stabilization_months

    # actions (tech/process/logistics)
    actions: List[str] = []
    actions.append("Deploy MES & automation to reduce OEE loss and accelerate ramp.")
    actions.append("Upgrade/add EAF/BOF interfaces or modular EAF capacity as needed.")
    actions.append("Improve raw-material handling (pelletizing, feeders, stockyard automation).")
    actions.append("Install WHR and substation upgrades (transformers, VFDs) to support extra MW.")
    actions.append("Implement predictive maintenance sensors and central monitoring.")
    actions.append("Coordinate ports schedule: reserve berth windows; stagger shipments to avoid impacting commercial cargo.")
    actions.append("Arrange short-term PPAs or temporary generation if energy shortfall exists.")
    actions.append("Hire contractors for civil & mechanical work to compress schedule; internal training for operators.")

    # capex breakdown
    capex_breakdown = {
        "total_investment_usd": int(round(total_investment)),
        "equipment_pct": 0.65,
        "installation_pct": 0.20,
        "commissioning_training_contingency_pct": 0.15,
        "equipment_usd": int(round(total_investment * 0.65)),
        "installation_usd": int(round(total_investment * 0.20)),
        "other_usd": int(round(total_investment * 0.15)),
    }

    # aggregated hiring
    aggregated_hiring = {"operators": 0, "maintenance": 0, "engineers": 0, "project_managers": 0}
    for p in per_plant_breakdown:
        h = p.get("hiring_estimate", {})
        aggregated_hiring["operators"] += int(h.get("operators", 0))
        aggregated_hiring["maintenance"] += int(h.get("maintenance", 0))
        aggregated_hiring["engineers"] += int(h.get("engineers", 0))
        aggregated_hiring["project_managers"] += int(h.get("project_managers", 0))

    processes = [
        "Integrate MES -> ERP for production & inventory tracking.",
        "Dual-shift commissioning and temporary overtime policy for ramp-up.",
        "Quality control labs for new blends and product mix.",
        "SOPs for port logistics scheduling to preserve commercial cargo SLAs.",
        "Energy curtailment agreements that protect grid commitments."
    ]

    # per-plant schedule (staggered)
    per_plant_schedule: List[Dict[str, Any]] = []
    current_offset = 0
    sorted_plants = sorted(per_plant_breakdown, key=lambda x: x["added_tpa"], reverse=True)
    for p in sorted_plants:
        start_month = current_offset + 1
        share = p["added_tpa"] / max(1, total_added_tpa)
        plant_procure = max(1, int(round(procurement_months * share)))
        plant_impl = max(1, int(round(implementation_months * share)))
        plant_comm = max(1, int(round(commissioning_months * share)))
        p_schedule = {
            "plant": p["name"],
            "start_month_planning": start_month,
            "procurement_window_months": plant_procure,
            "implementation_window_months": plant_impl,
            "commissioning_window_months": plant_comm,
            "expected_online_month": start_month + plant_procure + plant_impl + plant_comm
        }
        per_plant_schedule.append(p_schedule)
        current_offset += max(0, int(round(plant_impl * 0.5)))

    # resource checks
    resource_checks = {
        "ports": {
            "total_port_capacity_tpa": total_port_capacity,
            "used_port_tpa": used_port,
            "group_port_share_tpa": group_port_share,
            "spare_port_tpa": spare_port,
            "available_port_for_steel_tpa": available_port_for_steel,
            "port_throughput_required_tpa": port_throughput_required_tpa,
        },
        "energy": {
            "total_energy_capacity_mw": total_energy_capacity,
            "used_energy_mw": used_energy,
            "group_energy_share_mw": group_energy_share,
            "spare_energy_mw": spare_energy,
            "available_energy_for_steel_mw": available_energy_for_steel,
            "energy_required_mw": energy_required_mw,
        }
    }

    # append actions for shortages
    if energy_required_mw > available_energy_for_steel + 1e-6:
        shortage = energy_required_mw - available_energy_for_steel
        actions.append(f"Energy shortfall (~{shortage:.1f} MW): arrange PPA, rental gen, or stage works.")
    if port_throughput_required_tpa > available_port_for_steel + 1e-6:
        pshort = port_throughput_required_tpa - available_port_for_steel
        actions.append(f"Port shortfall ({pshort:,} tpa): stage shipments, engage 3PL, lease berth slots.")

    # metrics & checks for final notes
    metrics = {
        "added_tpa": int(total_added_tpa),
        "added_mtpa": round(total_added_mtpa, 3),
        "investment_usd": int(round(total_investment)),
        "estimated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "port_throughput_required_tpa": int(port_throughput_required_tpa),
    }

    # rationale bullets
    rationale_bullets: List[str] = [
        "Automation & MES chosen to reduce operational losses and accelerate reliable ramp-up.",
        "EAF/BOF interface or modular EAF selected for speed of capacity addition vs greenfield.",
        "WHR and substation upgrades to reduce operating cost and shorten payback.",
        "Port and logistics actions protect commercial cargo SLA while enabling project shipments.",
        "Staged per-plant schedule reduces simultaneous demand on ports and grid, lowering risk."
    ]

    # final confidence & notes
    confidence = START_CONFIDENCE
    notes_recommendations: List[str] = []
    if aggregated_payback_months is None:
        notes_recommendations.append("Unable to compute aggregated payback (zero/negative margin).")
        confidence -= 20
    else:
        if aggregated_payback_months <= parsed.get("max_payback_months", ENFORCED_PAYBACK_MONTHS):
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months meets target.")
        else:
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months exceeds target; consider staged or lower-CAPEX tech.")
            confidence -= 20

    if energy_required_mw > available_energy_for_steel + 1e-6:
        notes_recommendations.append("Energy resource shortfall present — mitigation required.")
        confidence -= 15
    else:
        notes_recommendations.append("Energy resources adequate for upgrade (spare + group allocation).")

    if port_throughput_required_tpa > available_port_for_steel + 1e-6:
        notes_recommendations.append("Port throughput shortfall present — logistics mitigation required.")
        confidence -= 10
    else:
        notes_recommendations.append("Ports capacity adequate (spare + group allocation).")

    if parsed.get("target_months", 15) < total_estimated_months:
        notes_recommendations.append(f"Schedule risk: target {parsed.get('target_months')} months vs estimate {total_estimated_months} months.")
        confidence -= 10
    else:
        notes_recommendations.append(f"Schedule estimate: ~{total_estimated_months} months.")

    confidence = max(confidence, MIN_CONFIDENCE)

    # build final structures
    recommendation = _build_recommendation_section("Proposed Upgrade: +2.0 MTPA steel capacity across Group X Steel Division", total_added_tpa, total_investment, aggregated_payback_months, energy_required_mw, confidence)
    roadmap = _build_roadmap_section({
        "planning_months": planning_months,
        "procurement_months": procurement_months,
        "implementation_months": implementation_months,
        "commissioning_months": commissioning_months,
        "stabilization_months": stabilization_months,
        "total_estimated_months": total_estimated_months
    }, per_plant_breakdown)
    rationale = _build_rationale_section(rationale_bullets, {
        "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
        "margin_per_ton_usd": MARGIN_PER_TON_USD,
        "mw_per_mtpa": MW_PER_MTPA,
        "cargo_tonne_per_steel_tonne": CARGO_TONNE_PER_STEEL_TONNE,
        "port_utilization": PORT_UTILIZATION,
        "port_group_share_of_used": PORT_GROUP_SHARE_OF_USED,
        "energy_utilization": ENERGY_UTILIZATION,
        "energy_grid_share_of_used": ENERGY_GRID_SHARE_OF_USED,
    }, debug_lines)

    result: Dict[str, Any] = {
        "recommendation": {
            **recommendation,
            "actions": actions,
            "capex_breakdown": capex_breakdown,
            "hiring_plan": {"aggregate": aggregated_hiring, "per_plant": {p["name"]: p["hiring_estimate"] for p in per_plant_breakdown}},
            "process_changes": processes,
            "distribution": [{"plant": p["name"], "added_mtpa": p["added_mtpa"], "capex_usd": p["capex_usd"]} for p in per_plant_breakdown]
        },
        "roadmap": roadmap,
        "rationale": rationale,
        "expected_increase_tpa": int(total_added_tpa),
        "investment_usd": int(round(total_investment)),
        "roi_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "port_throughput_required_tpa": port_throughput_required_tpa,
        "confidence_pct": confidence,
        "em_summaries": {
            "steel_info": {"num_plants": len(per_plant_breakdown), "plant_distribution": per_plant_breakdown},
            "ports_info": {"total_port_capacity_tpa": total_port_capacity, "ports": ports_list},
            "energy_info": {"total_energy_capacity_mw": total_energy_capacity, "plants": energy_list}
        },
        "infrastructure_analysis": resource_checks,
        "implementation_timeline": {"planning_months": planning_months, "procurement_months": procurement_months, "implementation_months": implementation_months, "commissioning_months": commissioning_months, "stabilization_months": stabilization_months},
        "notes": {"assumptions": {"capex_per_mtpa_usd": CAPEX_PER_MTPA_USD, "margin_per_ton_usd": MARGIN_PER_TON_USD, "mw_per_mtpa": MW_PER_MTPA}, "recommendations": notes_recommendations, "debug": debug_lines}
    }

    return result

# CLI quick test
if __name__ == "__main__":
    q = ("Increase total steel production by 2 MTPA within the next 15 months, "
         "allocating the capacity increase appropriately across all steel plants. "
         "Ensure that the investments required for this upgrade can be recovered within a payback period of less than 3 years.")
    import pprint
    pprint.pprint(run_simulation(q))
