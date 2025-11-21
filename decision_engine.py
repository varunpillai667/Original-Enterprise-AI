# decision_engine.py
"""
Decision Engine for Original Enterprise AI (updated)

This module provides a focused `run_simulation(query: str) -> dict` function
that understands the new strategic constraint:
  - Increase total steel production by X MTPA in Y months
  - Payback must be less than Z months

It parses the query, loads local mock data (mock_data.json in same folder),
calls enterprise-evaluator helpers when available, computes a capacity
distribution across steel plants, estimates CAPEX and ROI, checks feasibility,
and returns a structured result suitable for the Streamlit UI.

Assumptions and configurable parameters are declared at the top of the file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Try to import enterprise-level evaluators; if missing, we will still run.
try:
    from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
except Exception:
    evaluate_steel = None  # type: ignore
    evaluate_ports = None  # type: ignore
    evaluate_energy = None  # type: ignore

# Configurable assumptions (tweak these to match domain knowledge)
CAPEX_PER_MTPA_USD = 600_000_000  # USD per 1 MTPA of added annual capacity (example)
MARGIN_PER_TON_USD = 100  # incremental gross margin per ton (USD/ton)
MW_PER_MTPA = 2.5  # MW required per 1 MTPA incremental capacity (example)
DEFAULT_CONFIDENCE_PCT = 65

# File path to mock data (located next to this file)
MOCK_PATH = Path(__file__).parent / "mock_data.json"


# -------------------------
# Parsing utilities
# -------------------------
def _parse_query_for_constraints(query: str) -> Dict[str, int]:
    """
    Parse the strategic query string for:
      - target_mtpa (float, in MTPA)
      - target_months (int)
      - max_payback_months (int)

    Returns defaults if not found:
      - target_mtpa = 2
      - target_months = 15
      - max_payback_months = 36 (3 years)
    """
    q = query.lower()
    result = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": 36}

    # find MTPA or mtpa
    m = re.search(r'(\d+(\.\d+)?)\s*\s*m?t?p?a\b', q)
    if m:
        try:
            val = float(m.group(1))
            # If the phrase contains "steel production by 2 MTPA" this is fine.
            result["target_mtpa"] = val
        except Exception:
            pass

    # alternative: look for "2 mtpa" or "2 mpa" not reliable; fallback handled above

    # find months timeframe like "within the next 15 months" or "in 15 months"
    m2 = re.search(r'(\d{1,3})\s*(?:months|month)\b', q)
    if m2:
        try:
            result["target_months"] = int(m2.group(1))
        except Exception:
            pass

    # find payback constraint e.g. "less than 3 years" or "< 3 years"
    # convert years to months if found
    m3 = re.search(r'payback.*?(?:less than|<|within)\s*(\d+)\s*(years|year)\b', q)
    if m3:
        years = int(m3.group(1))
        result["max_payback_months"] = years * 12
    else:
        m4 = re.search(r'payback.*?(?:less than|<|within)\s*(\d{1,3})\s*(months|month)\b', q)
        if m4:
            result["max_payback_months"] = int(m4.group(1))

    return result


# -------------------------
# Data loading
# -------------------------
def _load_mock_data() -> Dict[str, Any]:
    """Load mock_data.json from same directory as this file; return dict."""
    try:
        with open(MOCK_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        # Return minimal fallback structure
        return {
            "steel": {
                "plants": [
                    {"id": "SP1", "name": "Steel Plant 1", "current_capacity_tpa": 1_000_000},
                    {"id": "SP2", "name": "Steel Plant 2", "current_capacity_tpa": 800_000},
                    {"id": "SP3", "name": "Steel Plant 3", "current_capacity_tpa": 700_000},
                    {"id": "SP4", "name": "Steel Plant 4", "current_capacity_tpa": 500_000},
                ]
            },
            "ports": {"ports": [{"id": "P1"}, {"id": "P2"}, {"id": "P3"}, {"id": "P4"}]},
            "energy": {"plants": [{"id": "E1"}, {"id": "E2"}, {"id": "E3"}]},
        }


# -------------------------
# Business logic
# -------------------------
def _distribute_target_among_plants(
    plants: List[Dict[str, Any]], target_tpa: int
) -> List[Dict[str, Any]]:
    """
    Distribute target_tpa (tonnes per annum) across plants.
    Prefer proportional to current_capacity_tpa; fall back to equal split.
    Returns list of plants with added_tpa and new_capacity_tpa.
    """
    total_current = sum(p.get("current_capacity_tpa", 0) for p in plants)
    if total_current > 0:
        distributed = []
        for p in plants:
            share = p.get("current_capacity_tpa", 0) / total_current
            added = int(round(share * target_tpa))
            distributed.append(
                {
                    **p,
                    "added_tpa": added,
                    "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + added),
                }
            )
        # Adjust rounding difference
        diff = target_tpa - sum(p["added_tpa"] for p in distributed)
        i = 0
        while diff != 0:
            distributed[i % len(distributed)]["added_tpa"] += 1 if diff > 0 else -1
            distributed[i % len(distributed)]["new_capacity_tpa"] += 1 if diff > 0 else -1
            diff = target_tpa - sum(p["added_tpa"] for p in distributed)
            i += 1
        return distributed
    else:
        # equal split
        n = max(1, len(plants))
        base = target_tpa // n
        distributed = []
        for i, p in enumerate(plants):
            added = base + (1 if i < (target_tpa % n) else 0)
            distributed.append(
                {
                    **p,
                    "added_tpa": added,
                    "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + added),
                }
            )
        return distributed


def _estimate_investment_for_distribution(distributed: List[Dict[str, Any]]) -> float:
    """
    Estimate CAPEX given distribution.
    Uses CAPEX_PER_MTPA_USD per 1 MTPA. Input added_tpa is in tonnes (not MTPA units).
    CAPEX_PER_MTPA_USD is per 1 MTPA (1,000,000 tpa), so scale accordingly.
    """
    total_added_tpa = sum(p.get("added_tpa", 0) for p in distributed)
    if total_added_tpa <= 0:
        return 0.0
    total_mtpas = total_added_tpa / 1_000_000.0
    estimated_capex = total_mtpas * CAPEX_PER_MTPA_USD
    return estimated_capex


def _estimate_annual_margin(distributed: List[Dict[str, Any]]) -> float:
    """Estimate additional annual gross margin from added capacity."""
    total_added_tpa = sum(p.get("added_tpa", 0) for p in distributed)
    if total_added_tpa <= 0:
        return 0.0
    # margin per ton
    return total_added_tpa * MARGIN_PER_TON_USD


def _estimate_energy_need_mw(total_added_mtpas: float) -> float:
    """Estimate incremental energy (MW) required for added MTPA."""
    return total_added_mtpas * MW_PER_MTPA


# -------------------------
# High level orchestration
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    """
    Main entry: simulate response to a strategic query.
    Returns a structured dict consumed by the Streamlit UI.
    """
    constraints = _parse_query_for_constraints(query)
    target_mtpa = float(constraints["target_mtpa"])
    target_months = int(constraints["target_months"])
    max_payback_months = int(constraints["max_payback_months"])

    # convert to tonnes per annum
    target_tpa = int(round(target_mtpa * 1_000_000))

    # Load data
    data = _load_mock_data()
    steel_plants = data.get("steel", {}).get("plants", [])
    ports = data.get("ports", {}).get("ports", [])
    energy_plants = data.get("energy", {}).get("plants", [])

    # Try to enrich via enterprise_manager evaluators (best-effort)
    em_summaries: Dict[str, Any] = {}
    try:
        if evaluate_steel:
            em_summaries["steel_info"] = evaluate_steel({"plants": steel_plants})
        else:
            em_summaries["steel_info"] = {
                "num_plants": len(steel_plants),
                "plant_summaries": steel_plants,
            }
    except Exception as exc:
        em_summaries["steel_info"] = {"error": str(exc), "num_plants": len(steel_plants)}

    try:
        if evaluate_ports:
            em_summaries["ports_info"] = evaluate_ports({"ports": ports})
        else:
            em_summaries["ports_info"] = {"num_ports": len(ports)}
    except Exception as exc:
        em_summaries["ports_info"] = {"error": str(exc), "num_ports": len(ports)}

    try:
        if evaluate_energy:
            em_summaries["energy_info"] = evaluate_energy({"energy_units_list": energy_plants})
        else:
            em_summaries["energy_info"] = {"num_plants": len(energy_plants)}
    except Exception as exc:
        em_summaries["energy_info"] = {"error": str(exc), "num_plants": len(energy_plants)}

    # Distribute target across plants
    distributed = _distribute_target_among_plants(steel_plants, target_tpa)

    # Estimate CAPEX and margins
    estimated_investment = _estimate_investment_for_distribution(distributed)
    annual_margin = _estimate_annual_margin(distributed)

    # Compute payback in months safely
    if annual_margin <= 0:
        payback_months: Optional[float] = None
    else:
        payback_years = estimated_investment / annual_margin
        payback_months = payback_years * 12

    # Energy needed
    total_added_mtpas = sum(p["added_tpa"] for p in distributed) / 1_000_000.0
    energy_required_mw = _estimate_energy_need_mw(total_added_mtpas)

    # Basic feasibility checks & recommendations
    infra_analysis: Dict[str, Any] = {}
    recommendations: List[str] = []
    confidence = DEFAULT_CONFIDENCE_PCT

    # Payback check
    feasible_payback = False
    if payback_months is None:
        recommendations.append("Unable to compute payback (zero or negative margin). Review margin assumptions.")
        confidence -= 20
    else:
        if payback_months <= max_payback_months:
            feasible_payback = True
            recommendations.append(f"Estimated payback: {payback_months:.1f} months — within target.")
        else:
            recommendations.append(f"Estimated payback: {payback_months:.1f} months — exceeds target of {max_payback_months} months.")
            # suggest alternatives to improve payback
            recommendations.append("Consider: increasing price/margin, staging capacity addition, or partial automation to reduce CAPEX.")
            confidence -= 25

    # Schedule check (rough)
    # naive assumption: new capacity per plant needs ~6 months baseline + incremental 2 months per 0.5 MTPA added
    complexity_factor_months = 6 + int(max(0, (total_added_mtpas / 0.5)) * 2)
    if target_months < complexity_factor_months:
        recommendations.append(
            f"Implementation risk: target timeframe ({target_months} months) is tight vs estimated baseline {complexity_factor_months} months."
        )
        confidence -= 15
    else:
        recommendations.append(f"Implementation timeframe ({target_months} months) is feasible based on high-level estimate.")

    # Port and energy analysis summary (very high-level)
    infra_analysis["port_capacity_analysis"] = [
        "Ports EM should validate export logistics for the incremental output.",
        f"Estimated additional port throughput required: {total_added_mtpas:.2f} MTPA."
    ]
    infra_analysis["energy_capacity_analysis"] = [
        f"Estimated incremental energy required: {energy_required_mw:.1f} MW across power plants.",
        "Energy EM should confirm availability and marginal cost."
    ]

    # Prepare per-plant recommendation text
    plant_recs = []
    for p in distributed:
        added_mtpa = p["added_tpa"] / 1_000_000.0
        plant_recs.append(
            f"{p.get('name', p.get('id',''))}: add {added_mtpa:.3f} MTPA (new capacity {p['new_capacity_tpa']/1_000_000.0:.3f} MTPA)"
        )

    # Implementation timeline (simple)
    implementation_timeline = {
        "planning_months": 2,
        "implementation_months": max(1, int(round(target_months * 0.7))),
        "stabilization_months": max(1, int(round(target_months * 0.2))),
    }

    # Select recommended plant/action: choose the plant with largest added_tpa (string)
    recommended_plant_id = max(distributed, key=lambda x: x.get("added_tpa", 0)) if distributed else None
    recommended_plant_str = (
        f"{recommended_plant_id.get('name', recommended_plant_id.get('id'))} (add {recommended_plant_id.get('added_tpa',0)} tpa)"
        if recommended_plant_id
        else "—"
    )

    result = {
        # top-level metrics
        "recommended_plant": recommended_plant_str,
        "expected_increase_tpa": sum(p["added_tpa"] for p in distributed),
        "investment_usd": int(round(estimated_investment)),
        "roi_months": None if payback_months is None else float(round(payback_months, 1)),
        "energy_required_mw": float(round(energy_required_mw, 2)),
        "confidence_pct": max(10, min(95, confidence)),
        # details for UI
        "em_summaries": {
            "steel_info": {
                "num_plants": len(steel_plants),
                "plant_recommendations": plant_recs,
                "plant_distribution": distributed,
            },
            "ports_info": em_summaries.get("ports_info", {}),
            "energy_info": em_summaries.get("energy_info", {}),
        },
        "infrastructure_analysis": infra_analysis,
        "implementation_timeline": implementation_timeline,
        # explainability / notes
        "notes": {
            "assumptions": {
                "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
                "margin_per_ton_usd": MARGIN_PER_TON_USD,
                "mw_per_mtpa": MW_PER_MTPA,
            },
            "recommendations": recommendations,
        },
    }

    return result


# For quick CLI debugging
if __name__ == "__main__":
    test_query = (
        "Increase total steel production by 2 MTPA within the next 15 months, "
        "allocating the capacity increase appropriately across all steel plants. "
        "Ensure that the investments required for this upgrade can be recovered within a payback period of less than 3 years."
    )
    import pprint

    r = run_simulation(test_query)
    pprint.pprint(r)
