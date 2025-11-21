# decision_engine.py
"""
Robust decision engine (defensive against missing keys/files).

- Uses safe .get(...) access for all uploaded/mock data.
- Falls back to deterministic 4-plant defaults if steel data missing.
- Writes helpful debug notes into result["notes"]["debug"] for UI visibility.
- Maintains Recommendation / Roadmap / Rationale output shape.
"""

from __future__ import annotations
import json
import re
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

USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]  # exactly as requested

# Candidate mock paths (module dir then common locations)
CANDIDATE_MOCKS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/Original-Enterprise-AI/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"
CONCEPT_PDF = "/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf"

# -------------------------
# Helpers
# -------------------------
def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

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

    # fallback defaults when no mock found or invalid structure
    debug.append("No mock_data.json found or readable; using internal defaults.")
    defaults = {
        "steel": {
            "plants": [
                {"id": "SP1", "name": "Steel Plant 1", "current_capacity_tpa": 1_200_000},
                {"id": "SP2", "name": "Steel Plant 2", "current_capacity_tpa": 900_000},
                {"id": "SP3", "name": "Steel Plant 3", "current_capacity_tpa": 700_000},
                {"id": "SP4", "name": "Steel Plant 4", "current_capacity_tpa": 600_000},
            ]
        },
        "ports": {
            "ports": [
                {"id": "P1", "name": "Port 1", "capacity_tpa": 2_000_000},
                {"id": "P2", "name": "Port 2", "capacity_tpa": 1_800_000},
                {"id": "P3", "name": "Port 3", "capacity_tpa": 1_600_000},
                {"id": "P4", "name": "Port 4", "capacity_tpa": 1_400_000},
            ]
        },
        "energy": {
            "plants": [
                {"id": "E1", "name": "Power Plant 1", "capacity_mw": 500},
                {"id": "E2", "name": "Power Plant 2", "capacity_mw": 450},
                {"id": "E3", "name": "Power Plant 3", "capacity_mw": 400},
            ]
        }
    }
    return {"data": defaults, "debug": debug, "path": None}

# -------------------------
# Query parsing (safe)
# -------------------------
def _parse_query(query: str) -> Dict[str, Any]:
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
# Section builders
# -------------------------
def _build_recommendation_section(headline: str, added_tpa: int, investment: float, payback_m: Optional[float], energy_mw: float, confidence: int) -> Dict[str, Any]:
    added_mtpa = round(added_tpa / 1_000_000.0, 3)
    metrics = {
        "added_tpa": int(added_tpa),
        "added_mtpa": added_mtpa,
        "investment_usd": int(round(investment)),
        "estimated_payback_months": None if payback_m is None else round(payback_m, 1),
        "energy_required_mw": round(energy_mw, 2),
        "confidence_pct": confidence,
    }
    summary = f"Proposed Upgrade: +{added_mtpa:.3f} MTPA steel capacity across Group X Steel Division (investment ${metrics['investment_usd']:,})."
    return {"headline": headline, "summary": summary, "metrics": metrics}

def _build_roadmap_section(timeline: Dict[str, int], per_plant_breakdown: List[Dict[str, Any]]) -> Dict[str, Any]:
    phases = [
        {"phase": "Planning", "months": timeline.get("planning_months", 2), "notes": "Engineering, permits, procurement."},
        {"phase": "Implementation", "months": timeline.get("implementation_months", 6), "notes": "Equipment install, civil works, commissioning."},
        {"phase": "Stabilization", "months": timeline.get("stabilization_months", 2), "notes": "Ramp-up and tuning."},
    ]
    actions = [f"{p['name']}: add {p['added_tpa']:,} tpa (CapEx ${int(p.get('capex_usd',0)):,})" for p in per_plant_breakdown]
    return {"phases": phases, "per_plant_actions": actions}

def _build_rationale_section(bullets: List[str], assumptions: Dict[str, Any], debug_lines: List[str]) -> Dict[str, Any]:
    b = list(bullets)
    b.append("Assumptions are listed below and used for resource feasibility checks.")
    return {"bullets": b, "assumptions": assumptions, "debug": debug_lines, "references": {"operational_flow_doc": OPERATIONAL_FLOW_DOC, "concept_pdf": CONCEPT_PDF}}

# -------------------------
# Main orchestration
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query(query)
    debug_lines: List[str] = parsed.get("debug", [])

    # load mock data (defensive)
    loaded = _load_mock_data()
    data = loaded.get("data", {})
    debug_lines += loaded.get("debug", [])
    if loaded.get("path"):
        debug_lines.append(f"Using mock_data.json from: {loaded.get('path')}")

    # steel plants (defensive access)
    steel_section = data.get("steel") or {}
    plants = steel_section.get("plants") or []
    if not plants:
        # fallback deterministic 4 plants
        debug_lines.append("Steel plants missing in data; applying 4-plant defaults.")
        plants = [
            {"id": "SP1", "name": "Steel Plant 1", "current_capacity_tpa": 1_200_000},
            {"id": "SP2", "name": "Steel Plant 2", "current_capacity_tpa": 900_000},
            {"id": "SP3", "name": "Steel Plant 3", "current_capacity_tpa": 700_000},
            {"id": "SP4", "name": "Steel Plant 4", "current_capacity_tpa": 600_000},
        ]

    # ports (defensive)
    ports_section = data.get("ports") or {}
    ports_list = ports_section.get("ports") or []
    if not ports_list:
        debug_lines.append("Ports data missing; applying default port capacities.")
        ports_list = [
            {"id": "P1", "name": "Port 1", "capacity_tpa": 2_000_000},
            {"id": "P2", "name": "Port 2", "capacity_tpa": 1_800_000},
            {"id": "P3", "name": "Port 3", "capacity_tpa": 1_600_000},
            {"id": "P4", "name": "Port 4", "capacity_tpa": 1_400_000},
        ]

    # energy (defensive)
    energy_section = data.get("energy") or {}
    energy_list = energy_section.get("plants") or []
    if not energy_list:
        debug_lines.append("Energy plant data missing; applying default capacities.")
        energy_list = [
            {"id": "E1", "name": "Power Plant 1", "capacity_mw": 500},
            {"id": "E2", "name": "Power Plant 2", "capacity_mw": 450},
            {"id": "E3", "name": "Power Plant 3", "capacity_mw": 400},
        ]

    # compute port availabilities
    total_port_capacity = sum(int(p.get("capacity_tpa", 0)) for p in ports_list)
    used_port = PORT_UTILIZATION * total_port_capacity
    group_port_share = used_port * PORT_GROUP_SHARE_OF_USED
    spare_port = total_port_capacity - used_port
    available_port_for_steel = spare_port + group_port_share

    # compute energy availabilities
    total_energy_capacity = sum(float(p.get("capacity_mw", 0)) for p in energy_list)
    used_energy = ENERGY_UTILIZATION * total_energy_capacity
    grid_energy_share = used_energy * ENERGY_GRID_SHARE_OF_USED
    group_energy_share = used_energy - grid_energy_share
    spare_energy = total_energy_capacity - used_energy
    available_energy_for_steel = spare_energy + group_energy_share

    # apply exact user distribution (defensive: ensure len <= plants)
    num_plants = min(len(plants), 4)
    dist_mtpa = USER_DISTRIBUTION_MTPA[:num_plants]
    added_tpa_list = [int(round(m * 1_000_000)) for m in dist_mtpa]

    # per-plant breakdown
    per_plant_breakdown: List[Dict[str, Any]] = []
    total_investment = 0.0
    total_annual_margin = 0.0

    for idx in range(num_plants):
        p = plants[idx]
        added = int(added_tpa_list[idx])
        mtpa_added = added / 1_000_000.0
        capex = _capex_for_mtpa(mtpa_added)
        annual_margin = _annual_margin_for_tpa(added)
        payback_months = None if annual_margin == 0 else (capex / annual_margin) * 12.0

        per_plant_breakdown.append({
            "id": p.get("id"),
            "name": p.get("name", p.get("id", "")),
            "current_capacity_tpa": int(p.get("current_capacity_tpa", 0)),
            "added_tpa": added,
            "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + added),
            "capex_usd": int(round(capex)),
            "annual_margin_usd": int(round(annual_margin)),
            "payback_months": None if payback_months is None else round(payback_months, 1),
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

    # timeline model
    planning_months = 2
    implementation_months = max(1, int(round(4 + total_added_mtpa * 8)))
    stabilization_months = max(1, int(round(implementation_months * 0.2)))
    estimated_total_months = planning_months + implementation_months + stabilization_months

    # checks, recommendations and confidence
    notes_recommendations: List[str] = []
    confidence = START_CONFIDENCE

    # energy check
    if energy_required_mw <= available_energy_for_steel + 1e-6:
        notes_recommendations.append("Energy: spare + group allocation can meet upgrade energy needs.")
    else:
        shortage = energy_required_mw - available_energy_for_steel
        notes_recommendations.append(f"Energy shortfall: {shortage:.1f} MW beyond spare+group allocation.")
        notes_recommendations.append("Mitigations: procure PPA, temporary generation, or stage upgrade.")
        confidence -= 20

    # port check
    if port_throughput_required_tpa <= available_port_for_steel + 1e-6:
        notes_recommendations.append("Ports: spare + group portion can handle required import/export cargo.")
    else:
        short = port_throughput_required_tpa - available_port_for_steel
        notes_recommendations.append(f"Port throughput shortfall: {short:,} tpa.")
        notes_recommendations.append("Mitigations: stagger shipments, lease berth capacity, use third-party logistics.")
        confidence -= 15

    # payback check
    if aggregated_payback_months is None:
        notes_recommendations.append("Unable to compute aggregated payback (zero or negative margin).")
        confidence -= 10
    else:
        if aggregated_payback_months <= parsed.get("max_payback_months", ENFORCED_PAYBACK_MONTHS):
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months meets target.")
        else:
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months exceeds target.")
            notes_recommendations.append("Consider CAPEX reductions, margin uplift, or staged implementation.")
            confidence -= 20

    # schedule check
    if parsed.get("target_months", 15) < estimated_total_months:
        notes_recommendations.append(f"Schedule risk: target {parsed.get('target_months')} months vs estimate {estimated_total_months} months.")
        confidence -= 10
    else:
        notes_recommendations.append(f"Schedule: estimated {estimated_total_months} months.")

    confidence = max(confidence, MIN_CONFIDENCE)

    # build output sections
    headline = "Proposed Upgrade: +2.0 MTPA steel capacity across Group X Steel Division"
    recommendation = _build_recommendation_section(headline, total_added_tpa, total_investment, aggregated_payback_months, energy_required_mw, confidence)
    timeline = {"planning_months": planning_months, "implementation_months": implementation_months, "stabilization_months": stabilization_months}
    roadmap = _build_roadmap_section(timeline, per_plant_breakdown)
    rationale = _build_rationale_section(notes_recommendations, {
        "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
        "margin_per_ton_usd": MARGIN_PER_TON_USD,
        "mw_per_mtpa": MW_PER_MTPA,
        "port_utilization": PORT_UTILIZATION,
        "port_group_share_of_used": PORT_GROUP_SHARE_OF_USED,
        "energy_utilization": ENERGY_UTILIZATION,
        "energy_grid_share_of_used": ENERGY_GRID_SHARE_OF_USED,
        "cargo_tonne_per_steel_tonne": CARGO_TONNE_PER_STEEL_TONNE,
    }, debug_lines)

    result: Dict[str, Any] = {
        "recommendation": recommendation,
        "roadmap": roadmap,
        "rationale": rationale,
        "expected_increase_tpa": int(total_added_tpa),
        "investment_usd": int(round(total_investment)),
        "roi_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "confidence_pct": confidence,
        "em_summaries": {
            "steel_info": {"num_plants": len(per_plant_breakdown), "plant_distribution": per_plant_breakdown},
            "ports_info": {"total_port_capacity_tpa": total_port_capacity, "ports": ports_list},
            "energy_info": {"total_energy_capacity_mw": total_energy_capacity, "plants": energy_list},
        },
        "infrastructure_analysis": {
            "port_capacity": {
                "total_port_capacity_tpa": total_port_capacity,
                "used_port_tpa": used_port,
                "group_port_share_tpa": group_port_share,
                "spare_port_tpa": spare_port,
                "available_port_for_steel_tpa": available_port_for_steel,
                "port_throughput_required_tpa": port_throughput_required_tpa,
            },
            "energy_capacity": {
                "total_energy_capacity_mw": total_energy_capacity,
                "used_energy_mw": used_energy,
                "group_energy_share_mw": group_energy_share,
                "spare_energy_mw": spare_energy,
                "available_energy_for_steel_mw": available_energy_for_steel,
                "energy_required_mw": energy_required_mw,
            }
        },
        "implementation_timeline": timeline,
        "notes": {
            "assumptions": {
                "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
                "margin_per_ton_usd": MARGIN_PER_TON_USD,
                "mw_per_mtpa": MW_PER_MTPA,
            },
            "recommendations": notes_recommendations,
            "debug": debug_lines,
        },
    }

    return result
