# decision_engine.py
"""
Robust decision engine (fixed)
- Resilient mock_data.json loading (module dir, /mnt/data repo root)
- Clear debug notes returned in result.notes.debug
- Always returns non-zero outputs (uses sensible defaults if data missing)
- Keeps the 3-section output: recommendation / roadmap / rationale
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Try to import enterprise evaluators (best-effort)
try:
    from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy  # type: ignore
except Exception:
    evaluate_steel = None  # type: ignore
    evaluate_ports = None  # type: ignore
    evaluate_energy = None  # type: ignore

# -------------------------
# Selected realistic assumptions
# -------------------------
CAPEX_PER_MTPA_USD = 420_000_000  # USD per 1 MTPA added capacity
MARGIN_PER_TON_USD = 120         # USD additional gross margin per tonne
MW_PER_MTPA = 2.5                # MW required per 1 MTPA
DEFAULT_CONFIDENCE_PCT = 78

# Candidate locations for mock_data.json (module folder, repo root under /mnt/data)
MODULE_MOCK = Path(__file__).parent / "mock_data.json"
CANDIDATE_MOCKS = [
    MODULE_MOCK,
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/Original-Enterprise-AI/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

# -------------------------
# Utilities: parsing & load
# -------------------------
def _parse_query_for_constraints(query: str) -> Dict[str, int]:
    q = (query or "").lower()
    result = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": 36, "debug": []}

    # parse MTPA
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            result["target_mtpa"] = float(m.group(1))
        except Exception:
            result["debug"].append("Failed to parse mtpa number; using default 2.0")
    else:
        # try loose pattern: look for "increase ... by 2"
        m2 = re.search(r'increase.*?by\s+(\d+(\.\d+)?)\s*(m[t]?pa|million)', q)
        if m2:
            try:
                result["target_mtpa"] = float(m2.group(1))
            except Exception:
                result["debug"].append("Loose parse for mtpa failed; default used")

    # months
    m3 = re.search(r'(\d{1,3})\s*(?:months|month)\b', q)
    if m3:
        try:
            result["target_months"] = int(m3.group(1))
        except Exception:
            result["debug"].append("Failed to parse months; using default 15")

    # payback
    m4 = re.search(r'payback.*?(?:less than|<|within)\s*(\d+)\s*(years|year)', q)
    if m4:
        try:
            result["max_payback_months"] = int(m4.group(1)) * 12
        except Exception:
            result["debug"].append("Failed to parse payback years; default 36 months")
    else:
        m5 = re.search(r'payback.*?(?:less than|<|within)\s*(\d{1,3})\s*(months|month)', q)
        if m5:
            try:
                result["max_payback_months"] = int(m5.group(1))
            except Exception:
                result["debug"].append("Failed to parse payback months; default 36")

    return result


def _load_mock_data() -> Dict[str, Any]:
    """Try multiple candidate paths; return dict and debug notes."""
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

    # No file found — return defaults
    debug.append("No mock_data.json found in candidate paths; using internal defaults.")
    defaults = {
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
    return {"data": defaults, "debug": debug, "path": None}


# -------------------------
# Helpers: distribution & estimates
# -------------------------
def _distribute_target(plants: List[Dict[str, Any]], target_tpa: int) -> List[Dict[str, Any]]:
    total = sum(p.get("current_capacity_tpa", 0) for p in plants)
    if total <= 0:
        # equal split fallback
        n = max(1, len(plants))
        base = target_tpa // n
        dist = []
        for i, p in enumerate(plants):
            add = base + (1 if i < (target_tpa % n) else 0)
            dist.append({**p, "added_tpa": add, "new_capacity_tpa": p.get("current_capacity_tpa", 0) + add})
        return dist

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
    return (added_tpa / 1_000_000.0) * CAPEX_PER_MTPA_USD


def _estimate_annual_margin_for_added_tpa(added_tpa: int) -> float:
    if added_tpa <= 0:
        return 0.0
    return added_tpa * MARGIN_PER_TON_USD


def _estimate_energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA


# -------------------------
# Section builders
# -------------------------
def _build_recommendation_section(recommended_str, total_added_tpa, total_investment, aggregated_payback_months, energy_required_mw, confidence):
    headline = recommended_str or "Increase capacity across plants"
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


def _build_roadmap_section(implementation_timeline, per_plant_breakdown):
    phases = [
        {"phase": "Planning", "months": implementation_timeline.get("planning_months", 2), "notes": "Engineering, permits, procurement."},
        {"phase": "Implementation", "months": implementation_timeline.get("implementation_months", 6), "notes": "Equipment install, commissioning."},
        {"phase": "Stabilization", "months": implementation_timeline.get("stabilization_months", 2), "notes": "Ramp-up & QA."},
    ]
    plant_actions = [f"{p['name']}: add {p['added_tpa']:,} tpa (CapEx ${int(p.get('capex_usd',0)):,})" for p in per_plant_breakdown]
    return {"phases": phases, "per_plant_actions": plant_actions}


def _build_rationale_section(notes_recommendations, key_assumptions, debug_lines):
    bullets = list(notes_recommendations)
    bullets.append("Assumptions listed below were used to derive payback and energy estimates.")
    return {"bullets": bullets, "assumptions": key_assumptions, "debug": debug_lines}


# -------------------------
# Main orchestration
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    # parse
    parsed = _parse_query_for_constraints(query)
    debug_lines: List[str] = parsed.get("debug", [])
    target_mtpa = float(parsed.get("target_mtpa", 2.0))
    target_months = int(parsed.get("target_months", 15))
    max_payback_months = int(parsed.get("max_payback_months", 36))
    target_tpa = int(round(max(0.0, target_mtpa) * 1_000_000.0))

    if target_tpa <= 0:
        debug_lines.append("Parsed target_tpa is 0; forcing default 2 MTPA.")
        target_tpa = 2_000_000
        target_mtpa = 2.0

    # load data (robust)
    loaded = _load_mock_data()
    data = loaded["data"]
    debug_lines.extend(loaded.get("debug", []))
    if loaded.get("path"):
        debug_lines.append(f"Using mock file: {loaded.get('path')}")

    steel_plants = data.get("steel", {}).get("plants", [])
    if not steel_plants:
        debug_lines.append("No steel plants found in mock data; inserting defaults.")
        steel_plants = [
            {"id": "SP1", "name": "Steel Plant 1", "current_capacity_tpa": 1_200_000},
            {"id": "SP2", "name": "Steel Plant 2", "current_capacity_tpa": 900_000},
            {"id": "SP3", "name": "Steel Plant 3", "current_capacity_tpa": 700_000},
            {"id": "SP4", "name": "Steel Plant 4", "current_capacity_tpa": 600_000},
        ]

    ports = data.get("ports", {}).get("ports", [])
    energy_plants = data.get("energy", {}).get("plants", [])

    # EM summaries best-effort
    em_summaries = {}
    try:
        em_summaries["steel_info"] = evaluate_steel({"plants": steel_plants}) if evaluate_steel else {"num_plants": len(steel_plants), "plant_summaries": steel_plants}
    except Exception as e:
        em_summaries["steel_info"] = {"error": str(e), "num_plants": len(steel_plants)}
        debug_lines.append(f"evaluate_steel failed: {e}")
    try:
        em_summaries["ports_info"] = evaluate_ports({"ports": ports}) if evaluate_ports else {"num_ports": len(ports)}
    except Exception as e:
        em_summaries["ports_info"] = {"error": str(e), "num_ports": len(ports)}
        debug_lines.append(f"evaluate_ports failed: {e}")
    try:
        em_summaries["energy_info"] = evaluate_energy({"energy_units_list": energy_plants}) if evaluate_energy else {"num_plants": len(energy_plants)}
    except Exception as e:
        em_summaries["energy_info"] = {"error": str(e), "num_plants": len(energy_plants)}
        debug_lines.append(f"evaluate_energy failed: {e}")

    # distribute
    distributed = _distribute_target(steel_plants, target_tpa)

    # per-plant financials
    per_plant_breakdown = []
    total_investment = 0.0
    total_annual_margin = 0.0
    for p in distributed:
        added = int(p.get("added_tpa", 0))
        capex = _estimate_capex_for_added_tpa(added)
        annual_margin = _estimate_annual_margin_for_added_tpa(added)
        payback_months = None
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

    total_added_tpa = sum(p["added_tpa"] for p in per_plant_breakdown)
    total_added_mtpa = total_added_tpa / 1_000_000.0
    energy_required_mw = _estimate_energy_mw_for_mtpa(total_added_mtpa)

    aggregated_payback_months = None
    if total_annual_margin > 0:
        aggregated_payback_months = (total_investment / total_annual_margin) * 12.0

    # timeline
    baseline_planning = 2
    implementation_months_est = max(1, int(round(4 + total_added_mtpa * 8)))
    stabilization_months = max(1, int(round(implementation_months_est * 0.2)))
    estimated_total_months = baseline_planning + implementation_months_est + stabilization_months

    # checks
    notes_recommendations = []
    confidence = DEFAULT_CONFIDENCE_PCT

    if aggregated_payback_months is None:
        notes_recommendations.append("Unable to compute aggregated payback (zero or negative margin).")
        confidence -= 30
    else:
        if aggregated_payback_months <= max_payback_months:
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months meets target {max_payback_months} months.")
        else:
            notes_recommendations.append(f"Aggregated payback {aggregated_payback_months:.1f} months exceeds target {max_payback_months} months.")
            confidence -= 25

    if target_months < estimated_total_months:
        notes_recommendations.append(f"Schedule risk: target {target_months} months vs estimate {estimated_total_months} months.")
        confidence -= 15
    else:
        notes_recommendations.append(f"Schedule feasible: estimate {estimated_total_months} months.")

    infra_analysis = {
        "port_capacity_analysis": [f"Estimated additional port throughput required: {total_added_mtpa:.2f} MTPA."],
        "energy_capacity_analysis": [f"Estimated incremental energy required: {energy_required_mw:.1f} MW."]
    }

    sorted_by_added = sorted(per_plant_breakdown, key=lambda x: x["added_tpa"], reverse=True)
    top_plants = [f"{p['name']} (+{p['added_tpa']:,} tpa)" for p in sorted_by_added[:2]] if sorted_by_added else []
    recommended_str = ", ".join(top_plants) if top_plants else "Increase capacity across plants"

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
    }, debug_lines + (loaded.get("debug") if isinstance(loaded, dict) else []))

    result = {
        "recommendation": recommendation_section,
        "roadmap": roadmap_section,
        "rationale": rationale_section,
        "expected_increase_tpa": int(total_added_tpa),
        "investment_usd": int(round(total_investment)),
        "roi_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(energy_required_mw, 2),
        "confidence_pct": recommendation_section["metrics"]["confidence_pct"],
        "em_summaries": {
            "steel_info": {"num_plants": len(per_plant_breakdown), "plant_distribution": per_plant_breakdown},
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
            "debug": debug_lines + (loaded.get("debug") if isinstance(loaded, dict) else []),
        },
    }

    return result
