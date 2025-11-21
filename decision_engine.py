# decision_engine.py
"""
Decision engine (updated output structure)

Returns a result dict with three main sections:
- recommendation
- roadmap
- rationale

Also includes em_summaries, per-plant breakdown, infra checks and notes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Try importing enterprise evaluators
try:
    from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy  # type: ignore
except Exception:
    evaluate_steel = None  # type: ignore
    evaluate_ports = None  # type: ignore
    evaluate_energy = None  # type: ignore

# Assumptions (tunable)
CAPEX_PER_MTPA_USD = 420_000_000  # USD per 1 MTPA added capacity
MARGIN_PER_TON_USD = 120         # USD additional gross margin per tonne
MW_PER_MTPA = 2.5                # MW required per 1 MTPA
DEFAULT_CONFIDENCE_PCT = 78

# Path to mock data and reference docs
MOCK_PATH = Path(__file__).parent / "mock_data.json"
# Reference to uploaded doc for traceability (local path)
OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"
CONCEPT_PDF = "/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf"


# -------------------------
# Parsing utilities
# -------------------------
def _parse_query_for_constraints(query: str) -> Dict[str, int]:
    q = (query or "").lower()
    result = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": 36}

    # find numeric MTPA (flexible)
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            result["target_mtpa"] = float(m.group(1))
        except Exception:
            pass

    # timeframe in months
    m2 = re.search(r'(\d{1,3})\s*(?:months|month)\b', q)
    if m2:
        try:
            result["target_months"] = int(m2.group(1))
        except Exception:
            pass

    # payback constraint (years -> months)
    m3 = re.search(r'payback.*?(?:less than|<|within)\s*(\d+)\s*(years|year)', q)
    if m3:
        try:
            years = int(m3.group(1))
            result["max_payback_months"] = years * 12
        except Exception:
            pass
    else:
        m4 = re.search(r'payback.*?(?:less than|<|within)\s*(\d{1,3})\s*(months|month)', q)
        if m4:
            try:
                result["max_payback_months"] = int(m4.group(1))
            except Exception:
                pass

    return result


# -------------------------
# Data loading
# -------------------------
def _load_mock_data() -> Dict[str, Any]:
    try:
        with open(MOCK_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        # fallback defaults
        return {
            "steel": {
                "plants": [
                    {"id": "SP1", "name": "Steel Plant 1", "current_capacity_tpa": 1_200_000},
                    {"id": "SP2", "name": "Steel Plant 2", "current_capacity_tpa": 900_000},
                    {"id": "SP3", "name": "Steel Plant 3", "current_capacity_tpa": 700_000},
                    {"id": "SP4", "name": "Steel Plant 4", "current_capacity_tpa": 600_000},
                ]
            },
            "ports": {"ports": [{"id": "P1"}, {"id": "P2"}, {"id": "P3"}, {"id": "P4"}]},
            "energy": {"plants": [{"id": "E1"}, {"id": "E2"}, {"id": "E3"}]},
        }


# -------------------------
# Distribution & estimates
# -------------------------
def _distribute_target(plants: List[Dict[str, Any]], target_tpa: int) -> List[Dict[str, Any]]:
    total = sum(p.get("current_capacity_tpa", 0) for p in plants)
    if total <= 0:
        n = max(1, len(plants))
        base = target_tpa // n
        distributed = []
        for i, p in enumerate(plants):
            add = base + (1 if i < (target_tpa % n) else 0)
            distributed.append({**p, "added_tpa": add, "new_capacity_tpa": p.get("current_capacity_tpa", 0) + add})
        return distributed

    distributed = []
    for p in plants:
        share = p.get("current_capacity_tpa", 0) / total
        added = int(round(share * target_tpa))
        distributed.append({**p, "added_tpa": max(0, added), "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + max(0, added))})

    diff = target_tpa - sum(p["added_tpa"] for p in distributed)
    idx = 0
    while diff != 0 and distributed:
        distributed[idx % len(distributed)]["added_tpa"] += 1 if diff > 0 else -1
        distributed[idx % len(distributed)]["new_capacity_tpa"] += 1 if diff > 0 else -1
        diff = target_tpa - sum(p["added_tpa"] for p in distributed)
        idx += 1

    return distributed


def _estimate_capex_for_added_tpa(added_tpa: int) -> float:
    if added_tpa <= 0:
        return 0.0
    added_mtpa = added_tpa / 1_000_000.0
    return added_mtpa * CAPEX_PER_MTPA_USD


def _estimate_annual_margin_for_added_tpa(added_tpa: int) -> float:
    if added_tpa <= 0:
        return 0.0
    return added_tpa * MARGIN_PER_TON_USD


def _estimate_energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA


# -------------------------
# Build sections
# -------------------------
def _build_recommendation_section(
    recommended_str: str,
    total_added_tpa: int,
    total_investment: float,
    aggregated_payback_months: Optional[float],
    energy_required_mw: float,
    confidence: int,
) -> Dict[str, Any]:
    headline = recommended_str
    metrics = {
        "added_tpa": int(total_added_tpa),
        "added_mtpa": round(total_added_tpa / 1_000_000.0, 3),
        "investment_usd": int(round(total_investment)),
        "estimated_payback_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "confidence_pct": confidence,
    }
    summary = f"Recommend incremental steel capacity of {metrics['added_mtpa']:.3f} MTPA with estimated investment ${metrics['investment_usd']:,}."
    return {"headline": headline, "summary": summary, "metrics": metrics}


def _build_roadmap_section(implementation_timeline: Dict[str, int], per_plant_breakdown: List[Dict[str, Any]]) -> Dict[str, Any]:
    phases = [
        {"phase": "Planning", "months": implementation_timeline.get("planning_months", 2), "notes": "Detailed engineering, permits, procurement planning."},
        {"phase": "Implementation", "months": implementation_timeline.get("implementation_months", 6), "notes": "Equipment installation, civil works, commissioning."},
        {"phase": "Stabilization", "months": implementation_timeline.get("stabilization_months", 2), "notes": "Ramp-up, QA, and operational tuning."},
    ]
    # short per-plant action bullets
    plant_actions = [f"{p['name']}: add {p['added_tpa']:,} tpa (CapEx ${int(p.get('capex_usd',0)):,})" for p in per_plant_breakdown]
    return {"phases": phases, "per_plant_actions": plant_actions}


def _build_rationale_section(notes_recommendations: List[str], key_assumptions: Dict[str, Any]) -> Dict[str, Any]:
    rationale_bullets = list(notes_recommendations)  # copy
    rationale_bullets.append("Assumptions shown below were used to derive payback and energy estimates.")
    return {"bullets": rationale_bullets, "assumptions": key_assumptions, "references": {"operational_flow_doc": OPERATIONAL_FLOW_DOC, "concept_pdf": CONCEPT_PDF}}


# -------------------------
# Main orchestration
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    # Parse constraints
    constraints = _parse_query_for_constraints(query)
    target_mtpa = float(constraints["target_mtpa"])
    target_months = int(constraints["target_months"])
    max_payback_months = int(constraints["max_payback_months"])
    target_tpa = int(round(target_mtpa * 1_000_000))

    # Load data
    data = _load_mock_data()
    steel_plants = data.get("steel", {}).get("plants", [])
    ports = data.get("ports", {}).get("ports", [])
    energy_plants = data.get("energy", {}).get("plants", [])

    # EM summaries (best-effort)
    em_summaries: Dict[str, Any] = {}
    try:
        em_summaries["steel_info"] = evaluate_steel({"plants": steel_plants}) if evaluate_steel else {"num_plants": len(steel_plants), "plant_summaries": steel_plants}
    except Exception as e:
        em_summaries["steel_info"] = {"error": str(e), "num_plants": len(steel_plants)}
    try:
        em_summaries["ports_info"] = evaluate_ports({"ports": ports}) if evaluate_ports else {"num_ports": len(ports)}
    except Exception as e:
        em_summaries["ports_info"] = {"error": str(e), "num_ports": len(ports)}
    try:
        em_summaries["energy_info"] = evaluate_energy({"energy_units_list": energy_plants}) if evaluate_energy else {"num_plants": len(energy_plants)}
    except Exception as e:
        em_summaries["energy_info"] = {"error": str(e), "num_plants": len(energy_plants)}

    # Distribute the target among plants
    distributed = _distribute_target(steel_plants, target_tpa)

    # Compute per-plant financials
    per_plant_breakdown: List[Dict[str, Any]] = []
    total_investment = 0.0
    total_annual_margin = 0.0
    for p in distributed:
        added = int(p.get("added_tpa", 0))
        capex = _estimate_capex_for_added_tpa(added)
        annual_margin = _estimate_annual_margin_for_added_tpa(added)
        payback_months: Optional[float] = None
        if annual_margin > 0:
            payback_months = (capex / annual_margin) * 12.0
        per_plant_breakdown.append({
            "id": p.get("id"),
            "name": p.get("name", p.get("id", "")),
            "current_capacity_tpa": int(p.get("current_capacity_tpa", 0)),
            "added_tpa": added,
            "new_capacity_tpa": int(p.get("new_capacity_tpa", 0)),
            "capex_usd": round(capex),
            "annual_margin_usd": round(annual_margin),
            "payback_months": None if payback_months is None else round(payback_months, 1),
        })
        total_investment += capex
        total_annual_margin += annual_margin

    # Totals and aggregates
    total_added_tpa = sum(p["added_tpa"] for p in per_plant_breakdown)
    total_added_mtpa = total_added_tpa / 1_000_000.0
    energy_required_mw = _estimate_energy_mw_for_mtpa(total_added_mtpa)

    aggregated_payback_months: Optional[float] = None
    if total_annual_margin > 0:
        aggregated_payback_months = (total_investment / total_annual_margin) * 12.0

    # Timeline model (conservative)
    baseline_planning = 2
    implementation_months_est = max(1, int(round(4 + total_added_mtpa * 8)))
    stabilization_months = max(1, int(round(implementation_months_est * 0.2)))
    estimated_total_months = baseline_planning + implementation_months_est + stabilization_months

    # Feasibility checks
    notes_recommendations: List[str] = []
    confidence = DEFAULT_CONFIDENCE_PCT

    if aggregated_payback_months is None:
        notes_recommendations.append("Cannot compute aggregated payback (zero or negative margin). Review margin assumption.")
        confidence -= 30
    else:
        if aggregated_payback_months <= max_payback_months:
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months meets target ({max_payback_months} months).")
        else:
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months exceeds target ({max_payback_months} months). Consider staged rollout or cost-reduction.")
            confidence -= 25

    if target_months < estimated_total_months:
        notes_recommendations.append(f"Schedule risk: target {target_months} months likely tight vs estimated {estimated_total_months} months.")
        confidence -= 15
    else:
        notes_recommendations.append(f"Schedule looks feasible: estimated {estimated_total_months} months.")

    infra_analysis = {
        "port_capacity_analysis": [
            f"Estimated additional port throughput required: {total_added_mtpa:.2f} MTPA."
        ],
        "energy_capacity_analysis": [
            f"Estimated incremental energy required: {energy_required_mw:.1f} MW."
        ]
    }

    # Pick recommended plants (top contributors)
    sorted_by_added = sorted(per_plant_breakdown, key=lambda x: x["added_tpa"], reverse=True)
    top_plants = [f"{p['name']} (+{p['added_tpa']:,} tpa)" for p in sorted_by_added[:2]] if sorted_by_added else []
    recommended_str = ", ".join(top_plants) if top_plants else "Increase capacity across plants"

    # Build structured sections
    recommendation_section = _build_recommendation_section(
        recommended_str,
        total_added_tpa,
        total_investment,
        aggregated_payback_months,
        energy_required_mw,
        max(10, min(95, confidence)),
    )

    implementation_timeline = {
        "planning_months": baseline_planning,
        "implementation_months": implementation_months_est,
        "stabilization_months": stabilization_months,
    }

    roadmap_section = _build_roadmap_section(implementation_timeline, per_plant_breakdown)
    rationale_section = _build_rationale_section(notes_recommendations, {
        "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
        "margin_per_ton_usd": MARGIN_PER_TON_USD,
        "mw_per_mtpa": MW_PER_MTPA,
        "mock_data_path": str(MOCK_PATH),
    })

    # Final result
    result: Dict[str, Any] = {
        "recommendation": recommendation_section,
        "roadmap": roadmap_section,
        "rationale": rationale_section,
        # keep other details for UI transparency
        "expected_increase_tpa": int(total_added_tpa),
        "investment_usd": int(round(total_investment)),
        "roi_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "confidence_pct": recommendation_section["metrics"]["confidence_pct"],
        "em_summaries": {
            "steel_info": {
                "num_plants": len(per_plant_breakdown),
                "plant_distribution": per_plant_breakdown,
            },
            "ports_info": em_summaries.get("ports_info", {}),
            "energy_info": em_summaries.get("energy_info", {}),
        },
        "infrastructure_analysis": infra_analysis,
        "implementation_timeline": implementation_timeline,
        "notes": {
            "assumptions": {
                "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
                "margin_per_ton_usd": MARGIN_PER_TON_USD,
                "mw_per_mtpa": MW_PER_MTPA,
            },
            "recommendations": notes_recommendations,
            "references": {
                "operational_flow_doc": OPERATIONAL_FLOW_DOC,
                "concept_pdf": CONCEPT_PDF,
            },
        },
    }

    return result


# CLI debug
if __name__ == "__main__":
    q = "Increase total steel production by 2 MTPA within the next 15 months, allocating appropriately; payback < 3 years."
    import pprint
    pprint.pprint(run_simulation(q))
