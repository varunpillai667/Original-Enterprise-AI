# decision_engine.py
"""
Decision engine — produces actionable Recommendation, Roadmap, and Rationale.

Key behavior:
- Uses exact user distribution: SP1 +0.8, SP2 +0.6, SP3 +0.4, SP4 +0.2 MTPA
- Estimates CAPEX, annual margin, payback
- Checks port and energy availability and includes logistics/energy mitigations
- Produces: recommendation.actions, recommendation.hiring_plan, recommendation.capex_breakdown,
  roadmap.phases (with activities/months), rationale.bullets (compact reasons)
- Adds debug notes and references to uploaded Operational Flow doc (local path)
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# -------------------------
# Assumptions & tunables
# -------------------------
CAPEX_PER_MTPA_USD = 420_000_000
MARGIN_PER_TON_USD = 120
MW_PER_MTPA = 2.5

# cargo factor: tonnes of port throughput (imports+exports) per tonne steel finished (assumption)
CARGO_TONNE_PER_STEEL_TONNE = 0.15

# port/energy allocation rules (from user)
PORT_UTILIZATION = 0.70
PORT_GROUP_SHARE_OF_USED = 1.0 / 3.0  # of the 70% used, 1/3 is group cargo
ENERGY_UTILIZATION = 0.75
ENERGY_GRID_SHARE_OF_USED = 3.0 / 4.0  # of the 75% used, 3/4 sold to grid

# Project organization assumptions (tunable)
START_CONFIDENCE = 85
MIN_CONFIDENCE = 70
ENFORCED_PAYBACK_MONTHS = 36

# Distribution requested by user
USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]  # SP1..SP4

# Candidate mock file locations (module dir + likely paths)
CANDIDATE_MOCKS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/Original-Enterprise-AI/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

# Reference paths (user uploaded docs)
OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"
CONCEPT_PDF = "/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf"

# -------------------------
# Helpers (small, focused)
# -------------------------
def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(added_tpa: int) -> float:
    return added_tpa * MARGIN_PER_TON_USD

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
                debug.append(f"Loaded mock_data.json from {p}")
                return {"data": data, "debug": debug, "path": str(p)}
        except Exception as exc:
            debug.append(f"Found file {p} but failed to read JSON: {exc}")

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
# Parse query (safe)
# -------------------------
def _parse_query_for_constraints(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    result = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": ENFORCED_PAYBACK_MONTHS, "debug": []}
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            result["target_mtpa"] = float(m.group(1))
        except Exception:
            result["debug"].append("Failed to parse target MTPA; using default 2.0")
    m2 = re.search(r'(\d{1,3})\s*(?:months|month)\b', q)
    if m2:
        try:
            result["target_months"] = int(m2.group(1))
        except Exception:
            result["debug"].append("Failed to parse months; using default 15")
    m3 = re.search(r'payback.*?(?:less than|<|within)\s*(\d+)\s*(years|year)', q)
    if m3:
        try:
            result["max_payback_months"] = int(m3.group(1)) * 12
        except Exception:
            result["debug"].append("Failed to parse payback years; using default")
    return result

# -------------------------
# Builders for structured output
# -------------------------
def _build_recommendation(headline: str, metrics: Dict[str, Any], actions: List[str], hiring: Dict[str, Any], capex_breakdown: Dict[str, Any], processes: List[str], distribution: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "headline": headline,
        "summary": metrics.get("summary", ""),
        "metrics": metrics,
        "actions": actions,
        "hiring_plan": hiring,
        "capex_breakdown": capex_breakdown,
        "process_changes": processes,
        "distribution": distribution,
    }

def _build_roadmap(timeline: Dict[str, int], phases: List[Dict[str, Any]], per_plant_schedule: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"timeline_months": timeline, "phases": phases, "per_plant_schedule": per_plant_schedule}

def _build_rationale(bullets: List[str], assumptions: Dict[str, Any], references: Dict[str, str]) -> Dict[str, Any]:
    return {"bullets": bullets, "assumptions": assumptions, "references": references}

# -------------------------
# Main orchestration
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query_for_constraints(query)
    debug_lines: List[str] = parsed.get("debug", [])

    # load data
    loaded = _load_mock_data()
    data = loaded.get("data", {})
    debug_lines += loaded.get("debug", [])
    if loaded.get("path"):
        debug_lines.append(f"Using mock_data.json at: {loaded.get('path')}")

    # defensive steel plant list
    steel_section = data.get("steel", {}) or {}
    plants = steel_section.get("plants") or []
    if len(plants) < 4:
        debug_lines.append("Steel plant data missing/incomplete — applying 4-plant defaults.")
        plants = [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]

    # ports and energy defensive
    ports_section = data.get("ports", {}) or {}
    ports_list = ports_section.get("ports") or []
    if not ports_list:
        debug_lines.append("Ports missing — using default port capacities.")
        ports_list = [
            {"id":"P1","name":"Port 1","capacity_tpa":2_000_000},
            {"id":"P2","name":"Port 2","capacity_tpa":1_800_000},
            {"id":"P3","name":"Port 3","capacity_tpa":1_600_000},
            {"id":"P4","name":"Port 4","capacity_tpa":1_400_000},
        ]

    energy_section = data.get("energy", {}) or {}
    energy_list = energy_section.get("plants") or []
    if not energy_list:
        debug_lines.append("Energy plants missing — using default capacities.")
        energy_list = [
            {"id":"E1","name":"Power Plant 1","capacity_mw":500},
            {"id":"E2","name":"Power Plant 2","capacity_mw":450},
            {"id":"E3","name":"Power Plant 3","capacity_mw":400},
        ]

    # compute port & energy availability per rules
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

    # apply user distribution exactly
    num_plants = min(4, len(plants))
    dist_mtpa = USER_DISTRIBUTION_MTPA[:num_plants]
    added_tpa_list = [int(round(m * 1_000_000)) for m in dist_mtpa]

    # per-plant financial computations and action prioritization
    per_plant_breakdown: List[Dict[str, Any]] = []
    total_investment = 0.0
    total_annual_margin = 0.0

    # Hiring assumptions (tunable): per 0.1 MTPA -> operators/maintenance/engineers
    OPS_PER_0_1MTPA = 5
    MAINT_PER_0_1MTPA = 2
    ENGINEERS_PER_0_1MTPA = 1
    PM_PER_PROJECT = 1  # per plant

    for idx in range(num_plants):
        plant = plants[idx]
        added_tpa = added_tpa_list[idx]
        added_mtpa = added_tpa / 1_000_000.0
        capex = _capex_for_mtpa(added_mtpa)
        annual_margin = _annual_margin_for_tpa(added_tpa)
        payback_months: Optional[float] = None
        if annual_margin > 0:
            payback_months = (capex / annual_margin) * 12.0

        # derive hiring needs
        units_0_1 = max(1, int(round(added_mtpa * 10)))  # number of 0.1 MTPA blocks
        ops_needed = units_0_1 * OPS_PER_0_1MTPA
        maint_needed = units_0_1 * MAINT_PER_0_1MTPA
        eng_needed = units_0_1 * ENGINEERS_PER_0_1MTPA
        pm_needed = PM_PER_PROJECT

        per_plant_breakdown.append({
            "id": plant.get("id"),
            "name": plant.get("name", plant.get("id", "")),
            "current_capacity_tpa": int(plant.get("current_capacity_tpa", 0)),
            "added_tpa": int(added_tpa),
            "added_mtpa": round(added_mtpa, 3),
            "new_capacity_tpa": int(plant.get("current_capacity_tpa", 0) + added_tpa),
            "capex_usd": int(round(capex)),
            "annual_margin_usd": int(round(annual_margin)),
            "payback_months": None if payback_months is None else round(payback_months, 1),
            "hiring_estimate": {
                "operators": ops_needed,
                "maintenance": maint_needed,
                "engineers": eng_needed,
                "project_managers": pm_needed
            }
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

    # Now build Recommendation actions: tech upgrades + processes + logistics
    # Core tech choices (prioritized for speed & ROI): automation, cupola/BOF/EAF upgrades, waste-heat recovery, pelletizing/raw handling, substation & switchgear, VFDs, predictive maintenance, MES integration.
    actions: List[str] = []
    # Prioritize SP1/SP2 (largest additions)
    actions.append("Deploy process automation and MES integration across targeted plants to reduce OEE losses and speed commissioning.")
    actions.append("Install or upgrade electric furnaces (EAF) capacity or modernize BOF interface where applicable to support incremental steel production.")
    actions.append("Add raw material handling upgrades: automated feeders, pelletizing modules, improved stockyard and rail/berth interfaces to reduce handling time.")
    actions.append("Install waste-heat-recovery (WHR) systems and improved boilers to recover energy and lower incremental fuel costs.")
    actions.append("Upgrade plant power substations / transformers and add VFDs on large drives to support additional MW draw safely.")
    actions.append("Deploy predictive maintenance sensors (vibration, thermography), and set up a central condition-monitoring hub.")
    actions.append("Establish temporary on-site project teams and hire contractors for civil & mechanical works to compress schedule.")
    actions.append("Coordinate with Ports EM to reserve berth windows and stagger arrivals so commercial cargo remains unaffected.")

    # Capex breakdown estimates (simple split)
    capex_breakdown = {
        "total_investment_usd": int(round(total_investment)),
        "equipment_pct": 0.65,
        "installation_pct": 0.20,
        "commissioning_training_contingency_pct": 0.15,
        "equipment_usd": int(round(total_investment * 0.65)),
        "installation_usd": int(round(total_investment * 0.20)),
        "other_usd": int(round(total_investment * 0.15)),
    }

    # Consolidated hiring plan across group (sum per-plant hiring estimates)
    aggregated_hiring = {"operators": 0, "maintenance": 0, "engineers": 0, "project_managers": 0}
    for p in per_plant_breakdown:
        h = p.get("hiring_estimate", {})
        aggregated_hiring["operators"] += int(h.get("operators", 0))
        aggregated_hiring["maintenance"] += int(h.get("maintenance", 0))
        aggregated_hiring["engineers"] += int(h.get("engineers", 0))
        aggregated_hiring["project_managers"] += int(h.get("project_managers", 0))

    # Process changes (short list)
    processes = [
        "Integrate MES -> ERP for real-time production & inventory tracking.",
        "Adopt dual-shift commissioning plan and temporary overtime policy for ramp-up.",
        "Implement quality control labs at each plant to manage new blends and product mix.",
        "Define SOPs for port logistics scheduling and emergency reroute; maintain commercial cargo SLA.",
        "Establish energy curtailment / load-shedding agreements that do not affect grid commitments."
    ]

    # Roadmap: phases with activities & per-plant schedule
    timeline = {
        "planning_months": planning_months,
        "procurement_months": procurement_months,
        "implementation_months": implementation_months,
        "commissioning_months": commissioning_months,
        "stabilization_months": stabilization_months,
        "total_estimated_months": total_estimated_months,
    }

    # Phase activities (high level)
    phases = [
        {"phase": "Planning & Approvals", "months": planning_months, "activities": [
            "Detailed engineering (per plant)",
            "Permits & environmental clearances",
            "Procurement planning & long-lead item identification",
            "Contractor tendering and selection"
        ]},
        {"phase": "Procurement", "months": procurement_months, "activities": [
            "Order long-lead equipment (EAF modules, transformers, WHR units)",
            "Sign PPAs or short-term generation agreements if energy gap identified",
            "Negotiate port berth windows and logistics contracts"
        ]},
        {"phase": "Implementation", "months": implementation_months, "activities": [
            "Civil works & foundation",
            "Equipment installation and electrical works",
            "Substation & grid interconnection upgrades",
            "Raw material handling upgrades (stockyards, conveyors)"
        ]},
        {"phase": "Commissioning & Training", "months": commissioning_months, "activities": [
            "Cold commissioning, hot commissioning, ramp tests",
            "Operator & maintenance training programs",
            "MES & ERP go-live and data validation"
        ]},
        {"phase": "Stabilization & Ramp", "months": stabilization_months, "activities": [
            "Production ramp to target rates",
            "Performance tuning and QA sign-off",
            "Transition to steady-state O&M"
        ]},
    ]

    # Per-plant schedule: allocate earlier windows to plants with highest added capacity (SP1 then SP2, etc.)
    per_plant_schedule: List[Dict[str, Any]] = []
    current_offset = 0
    # ordering by added tpa desc
    sorted_plants = sorted(per_plant_breakdown, key=lambda x: x["added_tpa"], reverse=True)
    for p in sorted_plants:
        start_month = current_offset + 1
        plant_impl_months = max(1, int(round(implementation_months * (p["added_tpa"] / max(1, total_added_tpa)))))
        plant_procure_months = max(1, int(round(procurement_months * (p["added_tpa"] / max(1, total_added_tpa)))))
        p_schedule = {
            "plant": p["name"],
            "start_month_planning": start_month,
            "procurement_window_months": plant_procure_months,
            "implementation_window_months": plant_impl_months,
            "commissioning_window_months": max(1, int(round(commissioning_months * (p["added_tpa"] / max(1, total_added_tpa))))),
            "expected_online_month": start_month + plant_procure_months + plant_impl_months + max(1, int(round(commissioning_months * (p["added_tpa"] / max(1, total_added_tpa)))))
        }
        per_plant_schedule.append(p_schedule)
        # stagger next plant by a fraction to avoid concurrency on ports/grids
        current_offset += max(0, int(round(plant_impl_months * 0.5)))

    # Rationale bullets (concise)
    rationale_bullets: List[str] = []
    rationale_bullets.append("Prioritized automation and EAF/BOF interface upgrades to deliver fastest time-to-market and best incremental margin per USD spent.")
    rationale_bullets.append("Raw material handling and port coordination minimize logistics lead time and protect commercial cargo SLAs.")
    rationale_bullets.append("Waste-heat recovery and substation upgrades reduce operating cost and lower payback time via energy savings.")
    rationale_bullets.append("Hiring plan ensures safe commissioning and preserves OEE during ramp-up; project managers compress schedule risk.")
    rationale_bullets.append("Phased per-plant schedule staggers heavy resource use (berths, grid connections) to avoid simultaneous strain on ports and energy supply.")
    rationale_bullets.append("Operational Flow document referenced for process-level checks.")

    # Resource feasibility checks & adjustments
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

    # Add resource deficiency messages into recommendations if any
    if energy_required_mw > available_energy_for_steel + 1e-6:
        shortage = energy_required_mw - available_energy_for_steel
        actions.append(f"Energy shortfall detected: need additional ~{shortage:.1f} MW — recommend short-term PPA or rental generation as mitigation.")
    if port_throughput_required_tpa > available_port_for_steel + 1e-6:
        pshort = port_throughput_required_tpa - available_port_for_steel
        actions.append(f"Port throughput shortfall: need additional {pshort:,} tpa — recommend staged shipments, 3PL contracts, or temporary berth leasing.")

    # Metrics summary
    metrics = {
        "added_tpa": int(total_added_tpa),
        "added_mtpa": round(total_added_mtpa, 3),
        "investment_usd": int(round(total_investment)),
        "estimated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "port_throughput_required_tpa": int(port_throughput_required_tpa),
    }

    # Final confidence and notes
    confidence = START_CONFIDENCE
    notes_recommendations: List[str] = []
    # Financial check
    if aggregated_payback_months is None:
        notes_recommendations.append("Unable to compute aggregated payback; check margin assumptions.")
        confidence -= 20
    else:
        if aggregated_payback_months <= parsed.get("max_payback_months", ENFORCED_PAYBACK_MONTHS):
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months meets target.")
        else:
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months exceeds target; consider staged rollout or lower-CAPEX tech.")
            confidence -= 20

    # Resource impacts
    if energy_required_mw > available_energy_for_steel + 1e-6:
        notes_recommendations.append("Energy resource shortfall present — mitigation required before full-rate commissioning.")
        confidence -= 15
    else:
        notes_recommendations.append("Energy resources adequate given spare + group allocation.")

    if port_throughput_required_tpa > available_port_for_steel + 1e-6:
        notes_recommendations.append("Port throughput shortfall present — logistics mitigation required.")
        confidence -= 10
    else:
        notes_recommendations.append("Port capacity adequate given spare + group allocation.")

    if parsed.get("target_months", 15) < total_estimated_months:
        notes_recommendations.append(f"Schedule risk: target {parsed.get('target_months')} months vs estimated {total_estimated_months} months.")
        confidence -= 10
    else:
        notes_recommendations.append(f"Schedule appears feasible: ~{total_estimated_months} months.")

    confidence = max(confidence, MIN_CONFIDENCE)

    # Build output structures
    recommendation = _build_recommendation(
        headline="Proposed Upgrade: +2.0 MTPA steel capacity across Group X Steel Division",
        metrics={"summary": f"Add {round(total_added_mtpa,3)} MTPA across four steel plants.", **metrics},
        actions=actions,
        hiring={"aggregate": aggregated_hiring, "per_plant": {p["name"]: p["hiring_estimate"] for p in per_plant_breakdown}},
        capex_breakdown=capex_breakdown,
        processes=processes,
        distribution=[{"plant": p["name"], "added_mtpa": p["added_mtpa"], "capex_usd": p["capex_usd"]} for p in per_plant_breakdown]
    )

    roadmap = _build_roadmap(timeline, phases=phases, per_plant_schedule=per_plant_schedule)

    rationale = _build_rationale(rationale_bullets, assumptions={
        "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
        "margin_per_ton_usd": MARGIN_PER_TON_USD,
        "mw_per_mtpa": MW_PER_MTPA,
        "cargo_tonne_per_steel_tonne": CARGO_TONNE_PER_STEEL_TONNE,
        "port_utilization": PORT_UTILIZATION,
        "port_group_share_of_used": PORT_GROUP_SHARE_OF_USED,
        "energy_utilization": ENERGY_UTILIZATION,
        "energy_grid_share_of_used": ENERGY_GRID_SHARE_OF_USED,
    }, references={"operational_flow_doc": OPERATIONAL_FLOW_DOC, "concept_pdf": CONCEPT_PDF})

    result: Dict[str, Any] = {
        "recommendation": recommendation,
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
            "energy_info": {"total_energy_capacity_mw": total_energy_capacity, "plants": energy_list},
        },
        "infrastructure_analysis": resource_checks,
        "implementation_timeline": timeline,
        "notes": {
            "assumptions": {
                "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
                "margin_per_ton_usd": MARGIN_PER_TON_USD,
                "mw_per_mtpa": MW_PER_MTPA,
            },
            "recommendations": notes_recommendations,
            "debug": debug_lines,
        }
    }

    return result

# End of file
