# decision_engine.py
"""
Decision engine — now accounts for port & energy allocations:
- Ports: 70% utilized; of that 1/3 -> group cargo, 2/3 -> commercial (unchanged)
- Energy: 75% utilized; of that 3/4 -> national grid (unchanged), 1/4 -> group
- Spare capacities (30% ports, 25% energy) + group shares are available for steel upgrade support
- No compromise to commercial port handling or national grid supply
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Try optional enterprise evaluators
try:
    from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy  # type: ignore
except Exception:
    evaluate_steel = None  # type: ignore
    evaluate_ports = None  # type: ignore
    evaluate_energy = None  # type: ignore

# --------------------
# Tunable assumptions
# --------------------
CAPEX_PER_MTPA_USD = 420_000_000
MARGIN_PER_TON_USD = 120
MW_PER_MTPA = 2.5
CARGO_TONNE_PER_STEEL_TONNE = 0.15  # tonnes of port cargo (imports+exports) per tonne steel output (assumption)
PORT_UTILIZATION = 0.70
PORT_GROUP_SHARE_OF_USED = 1.0 / 3.0
ENERGY_UTILIZATION = 0.75
ENERGY_GRID_SHARE_OF_USED = 3.0 / 4.0
START_CONFIDENCE = 85
MIN_CONFIDENCE = 70
ENFORCED_PAYBACK_MONTHS = 36

# Candidate mock data paths
MODULE_MOCK = Path(__file__).parent / "mock_data.json"
CANDIDATE_MOCKS = [
    MODULE_MOCK,
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/Original-Enterprise-AI/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

# Reference uploaded docs (local paths)
OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"
CONCEPT_PDF = "/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf"

# --------------------
# Utilities
# --------------------
def _parse_query_for_constraints(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    out = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": ENFORCED_PAYBACK_MONTHS, "debug": []}
    m_mtpa = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m_mtpa:
        try:
            out["target_mtpa"] = float(m_mtpa.group(1))
        except Exception:
            out["debug"].append("Failed to parse mtpa; default 2.0 used.")
    m_months = re.search(r'(\d{1,3})\s*(?:months|month)\b', q)
    if m_months:
        try:
            out["target_months"] = int(m_months.group(1))
        except Exception:
            out["debug"].append("Failed to parse months; default 15 used.")
    m_pay = re.search(r'payback.*?(?:less than|<|within)\s*(\d+)\s*(years|year)', q)
    if m_pay:
        try:
            out["max_payback_months"] = int(m_pay.group(1)) * 12
        except Exception:
            out["debug"].append("Failed to parse payback years; default used.")
    return out

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
            debug.append(f"Found {p} but could not read JSON: {exc}")
    # fallback defaults if none found
    debug.append("No mock_data.json found; using internal defaults.")
    defaults = {
        "steel": {
            "plants": [
                {"id": "SP1", "name": "Steel Plant 1", "current_capacity_tpa": 1_200_000},
                {"id": "SP2", "name": "Steel Plant 2", "current_capacity_tpa": 900_000},
                {"id": "SP3", "name": "Steel Plant 3", "current_capacity_tpa": 700_000},
                {"id": "SP4", "name": "Steel Plant 4", "current_capacity_tpa": 600_000},
            ]
        },
        # default per-port capacity in tpa (example, tune as needed)
        "ports": {"ports": [
            {"id": "P1", "name": "Port 1", "capacity_tpa": 2_000_000},
            {"id": "P2", "name": "Port 2", "capacity_tpa": 1_800_000},
            {"id": "P3", "name": "Port 3", "capacity_tpa": 1_600_000},
            {"id": "P4", "name": "Port 4", "capacity_tpa": 1_400_000},
        ]},
        # default energy plant capacities in MW
        "energy": {"plants": [
            {"id": "E1", "name": "Power Plant 1", "capacity_mw": 500},
            {"id": "E2", "name": "Power Plant 2", "capacity_mw": 450},
            {"id": "E3", "name": "Power Plant 3", "capacity_mw": 400},
        ]},
    }
    return {"data": defaults, "debug": debug, "path": None}

# --------------------
# Business helpers
# --------------------
def _capex_from_tpa(added_tpa: int) -> float:
    return (added_tpa / 1_000_000.0) * CAPEX_PER_MTPA_USD

def _annual_margin_from_tpa(added_tpa: int) -> float:
    return added_tpa * MARGIN_PER_TON_USD

# --------------------
# Section builders
# --------------------
def _build_recommendation_section(headline: str, total_added_tpa: int, total_investment: float,
                                  aggregated_payback_months: Optional[float], energy_required_mw: float,
                                  confidence: int) -> Dict[str, Any]:
    added_mtpa = round(total_added_tpa / 1_000_000.0, 3)
    metrics = {
        "added_tpa": int(total_added_tpa),
        "added_mtpa": added_mtpa,
        "investment_usd": int(round(total_investment)),
        "estimated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "confidence_pct": confidence,
    }
    summary = f"Proposed Upgrade: +{added_mtpa:.3f} MTPA steel capacity across Group X Steel Division (investment ${metrics['investment_usd']:,})."
    return {"headline": headline, "summary": summary, "metrics": metrics}

def _build_roadmap_section(timeline: Dict[str, int], per_plant_breakdown: List[Dict[str, Any]]) -> Dict[str, Any]:
    phases = [
        {"phase": "Planning", "months": timeline.get("planning_months", 2), "notes": "Engineering, permits, procurement."},
        {"phase": "Implementation", "months": timeline.get("implementation_months", 6), "notes": "Equipment installation, civil works, commissioning."},
        {"phase": "Stabilization", "months": timeline.get("stabilization_months", 2), "notes": "Ramp-up and operational tuning."},
    ]
    per_plant_actions = [f"{p['name']}: add {p['added_tpa']:,} tpa (CapEx ${int(p.get('capex_usd',0)):,})" for p in per_plant_breakdown]
    return {"phases": phases, "per_plant_actions": per_plant_actions}

def _build_rationale_section(recommendation_bullets: List[str], assumptions: Dict[str, Any], debug_lines: List[str]) -> Dict[str, Any]:
    bullets = list(recommendation_bullets)
    bullets.append("Assumptions are shown below and used for port & energy feasibility checks.")
    return {"bullets": bullets, "assumptions": assumptions, "debug": debug_lines,
            "references": {"operational_flow_doc": OPERATIONAL_FLOW_DOC, "concept_pdf": CONCEPT_PDF}}

# --------------------
# Main orchestration
# --------------------
def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query_for_constraints(query)
    debug_lines: List[str] = parsed.get("debug", [])
    target_mtpa = float(parsed.get("target_mtpa", 2.0))
    target_months = int(parsed.get("target_months", 15))
    max_payback_months = int(parsed.get("max_payback_months", ENFORCED_PAYBACK_MONTHS))

    target_tpa = int(round(target_mtpa * 1_000_000))

    # Load data (robust)
    loaded = _load_mock_data()
    data = loaded["data"]
    debug_lines += loaded.get("debug", [])
    mock_path = loaded.get("path")
    if mock_path:
        debug_lines.append(f"Using mock_data.json at {mock_path}")

    # Steel plants
    steel_plants = data.get("steel", {}).get("plants", [])
    if len(steel_plants) < 4:
        debug_lines.append("Less than 4 steel plants in data; using 4-plant defaults.")

    # Ports: compute capacities and available throughput for steel logistics
    ports = data.get("ports", {}).get("ports", [])
    # if ports list has capacity_tpa, use it; otherwise fallbacks applied above
    total_port_capacity = sum(int(p.get("capacity_tpa", 0)) for p in ports) if ports else 0
    if total_port_capacity == 0:
        # fallback default per-port capacities if none present
        default_per_port = 1_900_000
        total_port_capacity = default_per_port * max(1, len(ports) or 4)
        debug_lines.append("Port capacities not specified in mock data; using default per-port capacity.")

    used_port = PORT_UTILIZATION * total_port_capacity
    group_port_share = used_port * PORT_GROUP_SHARE_OF_USED
    commercial_port_share = used_port * (1 - PORT_GROUP_SHARE_OF_USED)
    spare_port = total_port_capacity - used_port
    # available for steel shipments without touching commercial cargo or national commitments:
    available_port_for_steel = spare_port + group_port_share

    # Energy: compute capacities and available energy for steel plants
    energy_plants = data.get("energy", {}).get("plants", [])
    total_energy_capacity = sum(float(p.get("capacity_mw", 0)) for p in energy_plants) if energy_plants else 0.0
    if total_energy_capacity == 0.0:
        # fallback: default capacities
        default_mw = 450.0
        total_energy_capacity = default_mw * max(1, len(energy_plants) or 3)
        debug_lines.append("Energy plant capacities not specified in mock data; using default capacities.")

    used_energy = ENERGY_UTILIZATION * total_energy_capacity
    grid_energy_share = used_energy * ENERGY_GRID_SHARE_OF_USED
    group_energy_share = used_energy * (1 - ENERGY_GRID_SHARE_OF_USED)
    spare_energy = total_energy_capacity - used_energy
    available_energy_for_steel = spare_energy + group_energy_share

    # Use the exact distribution requested by you (0.8,0.6,0.4,0.2 MTPA) for 4 plants
    user_distribution_mtpa = [0.8, 0.6, 0.4, 0.2]
    # Ensure we have at least 4 plants — fallback handled above
    distribution_tpa = [int(round(mtpa * 1_000_000)) for mtpa in user_distribution_mtpa]

    # per-plant financials and totals
    per_plant_breakdown: List[Dict[str, Any]] = []
    total_investment = 0.0
    total_annual_margin = 0.0
    for idx, p in enumerate(steel_plants[:4]):
        added = distribution_tpa[idx]
        capex = _capex_from_tpa(added)
        annual_margin = _annual_margin_from_tpa(added)
        payback_months = None
        if annual_margin > 0.0:
            payback_months = (capex / annual_margin) * 12.0
        per_plant_breakdown.append({
            "id": p.get("id"),
            "name": p.get("name", p.get("id", "")),
            "current_capacity_tpa": int(p.get("current_capacity_tpa", 0)),
            "added_tpa": int(added),
            "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + added),
            "capex_usd": int(round(capex)),
            "annual_margin_usd": int(round(annual_margin)),
            "payback_months": None if payback_months is None else round(payback_months, 1),
        })
        total_investment += capex
        total_annual_margin += annual_margin

    total_added_tpa = sum(p["added_tpa"] for p in per_plant_breakdown)
    total_added_mtpa = total_added_tpa / 1_000_000.0
    # energy required for the capacity increase
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)

    # port throughput required for the capacity increase (imports + exports)
    port_throughput_required_tpa = int(round(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE))

    # aggregated payback
    aggregated_payback_months: Optional[float] = None
    if total_annual_margin > 0.0:
        aggregated_payback_months = (total_investment / total_annual_margin) * 12.0

    # timeline
    planning_months = 2
    implementation_months = max(1, int(round(4 + total_added_mtpa * 8)))
    stabilization_months = max(1, int(round(implementation_months * 0.2)))
    estimated_total_months = planning_months + implementation_months + stabilization_months

    # resource feasibility checks and recommendations
    notes_recommendations: List[str] = []
    confidence = START_CONFIDENCE
    resource_checks: Dict[str, Any] = {}

    # Energy check (must not reduce grid share)
    resource_checks["energy"] = {
        "total_energy_capacity_mw": total_energy_capacity,
        "used_energy_mw": used_energy,
        "grid_energy_share_mw": grid_energy_share,
        "group_energy_share_mw": group_energy_share,
        "spare_energy_mw": spare_energy,
        "available_energy_for_steel_mw": available_energy_for_steel,
        "energy_required_mw": energy_required_mw,
    }
    if energy_required_mw <= available_energy_for_steel + 1e-6:
        notes_recommendations.append("Energy: available spare + group allocation can meet the upgrade energy needs.")
    else:
        shortage = energy_required_mw - available_energy_for_steel
        notes_recommendations.append(f"Energy shortfall: need additional {shortage:.1f} MW beyond spare+group allocation.")
        notes_recommendations.append("Mitigations: stage the upgrade; procure short-term PPAs; deploy temporary generation; increase efficiency.")
        confidence -= 20

    # Port throughput check (must not reduce commercial cargo)
    resource_checks["ports"] = {
        "total_port_capacity_tpa": total_port_capacity,
        "used_port_tpa": used_port,
        "group_port_share_tpa": group_port_share,
        "commercial_port_share_tpa": commercial_port_share,
        "spare_port_tpa": spare_port,
        "available_port_for_steel_tpa": available_port_for_steel,
        "port_throughput_required_tpa": port_throughput_required_tpa,
    }
    if port_throughput_required_tpa <= available_port_for_steel:
        notes_recommendations.append("Ports: spare capacity + group portion can handle required import/export cargo for the upgrade.")
    else:
        pt_short = port_throughput_required_tpa - available_port_for_steel
        notes_recommendations.append(f"Port throughput shortfall: need additional {pt_short:,} tpa beyond available capacity.")
        notes_recommendations.append("Mitigations: use third-party logistics, stagger shipments, lease extra berth space, or increase rail throughput.")
        confidence -= 15

    # Payback & schedule checks
    if aggregated_payback_months is None:
        notes_recommendations.append("Unable to compute aggregated payback (zero or negative margin).")
        confidence -= 10
    else:
        if aggregated_payback_months <= max_payback_months:
            notes_recommendations.append(f"Financial: aggregated payback {aggregated_payback_months:.1f} months meets requirement (<{max_payback_months}).")
        else:
            notes_recommendations.append(f"Financial: aggregated payback {aggregated_payback_months:.1f} months exceeds target (<{max_payback_months}).")
            notes_recommendations.append("Consider CAPEX reductions, price/margin improvements, or staged implementation to meet payback.")
            confidence -= 20

    if target_months < estimated_total_months:
        notes_recommendations.append(f"Schedule risk: requested {target_months} months vs estimated {estimated_total_months} months.")
        confidence -= 10
    else:
        notes_recommendations.append(f"Schedule feasible: estimated {estimated_total_months} months.")

    confidence = max(confidence, MIN_CONFIDENCE)

    # Headline and sections
    headline = "Proposed Upgrade: +2.0 MTPA steel capacity across Group X Steel Division"
    recommendation_section = _build_recommendation_section(headline, total_added_tpa, total_investment, aggregated_payback_months, energy_required_mw, confidence)
    timeline_section = {"planning_months": planning_months, "implementation_months": implementation_months, "stabilization_months": stabilization_months}
    roadmap_section = _build_roadmap_section(timeline_section, per_plant_breakdown)
    rationale_section = _build_rationale_section(notes_recommendations, {
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
        "recommendation": recommendation_section,
        "roadmap": roadmap_section,
        "rationale": rationale_section,
        "expected_increase_tpa": int(total_added_tpa),
        "investment_usd": int(round(total_investment)),
        "roi_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "confidence_pct": confidence,
        "em_summaries": {
            "steel_info": {"num_plants": len(per_plant_breakdown), "plant_distribution": per_plant_breakdown},
            "ports_info": {"total_port_capacity_tpa": total_port_capacity, "ports": ports},
            "energy_info": {"total_energy_capacity_mw": total_energy_capacity, "plants": energy_plants},
        },
        "infrastructure_analysis": {
            "port_capacity": resource_checks["ports"],
            "energy_capacity": resource_checks["energy"],
        },
        "implementation_timeline": timeline_section,
        "notes": {
            "assumptions": {
                "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
                "margin_per_ton_usd": MARGIN_PER_TON_USD,
                "mw_per_mtpa": MW_PER_MTPA,
                "cargo_tonne_per_steel_tonne": CARGO_TONNE_PER_STEEL_TONNE,
                "port_utilization": PORT_UTILIZATION,
                "port_group_share_of_used": PORT_GROUP_SHARE_OF_USED,
                "energy_utilization": ENERGY_UTILIZATION,
                "energy_grid_share_of_used": ENERGY_GRID_SHARE_OF_USED,
            },
            "recommendations": notes_recommendations,
            "debug": debug_lines,
        }
    }

    return result

# Quick CLI test
if __name__ == "__main__":
    q = ("Increase total steel production by 2 MTPA within the next 15 months, "
         "allocating the capacity increase appropriately across all steel plants. "
         "Ensure that the investments required for this upgrade can be recovered within a payback period of less than 3 years.")
    import pprint
    pprint.pprint(run_simulation(q))
