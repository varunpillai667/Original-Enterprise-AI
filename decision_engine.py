# decision_engine.py
"""
Decision engine (updated for the steel +2 MTPA strategic query)

Produces clear assumptions and a polished, actionable simulation result.
Reads mock_data.json from the same folder as this file.

Key outputs (all returned in the dict):
- recommended_plant (string)
- expected_increase_tpa (int)
- investment_usd (int)
- roi_months (float or None)
- energy_required_mw (float)
- confidence_pct (int)
- em_summaries -> steel_info contains per-plant breakdown with capex & payback
- infrastructure_analysis (list)
- implementation_timeline
- notes.assumptions and notes.recommendations
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Try importing enterprise evaluators (best-effort)
try:
    from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy  # type: ignore
except Exception:
    evaluate_steel = None  # type: ignore
    evaluate_ports = None  # type: ignore
    evaluate_energy = None  # type: ignore

# -------------------------
# Configurable assumptions
# (Tweak these if you want different financials)
# -------------------------
CAPEX_PER_MTPA_USD = 450_000_000  # USD per 1 MTPA added capacity (conservative mid-range)
MARGIN_PER_TON_USD = 120  # USD additional gross margin per tonne of incremental output
MW_PER_MTPA = 2.2  # MW required per 1 MTPA incremental capacity
DEFAULT_CONFIDENCE_PCT = 75

# Path to mock data (next to this file)
MOCK_PATH = Path(__file__).parent / "mock_data.json"


# -------------------------
# Helpers: parse query
# -------------------------
def _parse_query_for_constraints(query: str) -> Dict[str, int]:
    q = (query or "").lower()
    result = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": 36}

    # find MTPA number (e.g., "2 MTPA")
    m = re.search(r'(\d+(\.\d+)?)\s*m\s*t\s*p\s*a|\b(\d+(\.\d+)?)\s*mtpa\b', q.replace(" ", ""))
    if not m:
        # fallback simpler pattern: "<number> mtpa" or "<number> mpta"
        m = re.search(r'(\d+(\.\d+)?)\s*mtpa|\b(\d+(\.\d+)?)\s*m?t?p?a\b', q)
    if m:
        # pick first numeric group that is not None
        for g in m.groups():
            if g:
                try:
                    result["target_mtpa"] = float(g)
                    break
                except Exception:
                    pass

    # timeframe in months (e.g., "15 months")
    m2 = re.search(r'(\d{1,3})\s*(?:months|month)\b', q)
    if m2:
        try:
            result["target_months"] = int(m2.group(1))
        except Exception:
            pass

    # payback: "less than 3 years" or "payback < 3 years" or "within 36 months"
    m3 = re.search(r'payback.*?(?:less than|<|within)\s*(\d+)\s*(years|year)\b', q)
    if m3:
        try:
            years = int(m3.group(1))
            result["max_payback_months"] = years * 12
        except Exception:
            pass
    else:
        m4 = re.search(r'payback.*?(?:less than|<|within)\s*(\d{1,3})\s*(months|month)\b', q)
        if m4:
            try:
                result["max_payback_months"] = int(m4.group(1))
            except Exception:
                pass

    return result


# -------------------------
# Helpers: load data
# -------------------------
def _load_mock_data() -> Dict[str, Any]:
    try:
        with open(MOCK_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        # sensible defaults if file not found
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
# Helpers: distribution & estimates
# -------------------------
def _distribute_target(plants: List[Dict[str, Any]], target_tpa: int) -> List[Dict[str, Any]]:
    """Proportional distribution by current capacity; returns list with added_tpa & new_capacity."""
    total = sum(p.get("current_capacity_tpa", 0) for p in plants)
    if total <= 0:
        # equal split if no capacity metadata
        n = max(1, len(plants))
        base = target_tpa // n
        distributed = []
        for i, p in enumerate(plants):
            add = base + (1 if i < (target_tpa % n) else 0)
            distributed.append({**p, "added_tpa": add, "new_capacity_tpa": p.get("current_capacity_tpa", 0) + add})
        return distributed

    distributed: List[Dict[str, Any]] = []
    for p in plants:
        share = p.get("current_capacity_tpa", 0) / total
        added = int(round(share * target_tpa))
        distributed.append({**p, "added_tpa": max(0, added), "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + max(0, added))})

    # correct rounding difference
    diff = target_tpa - sum(p["added_tpa"] for p in distributed)
    idx = 0
    while diff != 0 and distributed:
        distributed[idx % len(distributed)]["added_tpa"] += 1 if diff > 0 else -1
        distributed[idx % len(distributed)]["new_capacity_tpa"] += 1 if diff > 0 else -1
        diff = target_tpa - sum(p["added_tpa"] for p in distributed)
        idx += 1

    return distributed


def _estimate_capex_for_added_tpa(added_tpa: int) -> float:
    """Estimate capex (USD) for added TPA. CAPEX_PER_MTPA_USD is per 1,000,000 tpa."""
    if added_tpa <= 0:
        return 0.0
    added_mtpa = added_tpa / 1_000_000.0
    return added_mtpa * CAPEX_PER_MTPA_USD


def _estimate_annual_margin_for_added_tpa(added_tpa: int) -> float:
    """Estimate incremental annual gross margin from added tpa (USD)."""
    if added_tpa <= 0:
        return 0.0
    return added_tpa * MARGIN_PER_TON_USD


def _estimate_energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA


# -------------------------
# Main orchestration
# -------------------------
def run_simulation(query: str) -> Dict[str, Any]:
    constraints = _parse_query_for_constraints(query)
    target_mtpa = float(constraints["target_mtpa"])
    target_months = int(constraints["target_months"])
    max_payback_months = int(constraints["max_payback_months"])

    target_tpa = int(round(target_mtpa * 1_000_000))

    # load data
    data = _load_mock_data()
    steel_plants = data.get("steel", {}).get("plants", [])
    ports = data.get("ports", {}).get("ports", [])
    energy_plants = data.get("energy", {}).get("plants", [])

    # call enterprise manager evaluators best-effort (non-fatal)
    em_summaries: Dict[str, Any] = {}
    try:
        em_summaries["steel_info"] = evaluate_steel({"plants": steel_plants}) if evaluate_steel else {"num_plants": len(steel_plants)}
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

    # distribute target across steel plants
    distributed = _distribute_target(steel_plants, target_tpa)

    # per-plant financials
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
        else:
            payback_months = None

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

    # totals
    total_added_tpa = sum(p["added_tpa"] for p in per_plant_breakdown)
    total_added_mtpa = total_added_tpa / 1_000_000.0
    total_energy_mw = _estimate_energy_mw_for_mtpa(total_added_mtpa)

    # aggregated payback
    aggregated_payback_months: Optional[float] = None
    if total_annual_margin > 0:
        aggregated_payback_months = (total_investment / total_annual_margin) * 12.0

    # simple timeline model
    # baseline months = 6 for planning & approvals + implementation proportional to scale
    baseline_planning = 2
    implementation_months_est = max(1, int(round(4 + total_added_mtpa * 8)))  # e.g., 0.5 MTPA -> ~8 months scaling
    stabilization_months = max(1, int(round(implementation_months_est * 0.2)))
    estimated_total_months = baseline_planning + implementation_months_est + stabilization_months

    # feasibility checks and recommendations
    notes_recommendations: List[str] = []
    confidence = DEFAULT_CONFIDENCE_PCT

    # payback feasibility
    if aggregated_payback_months is None:
        notes_recommendations.append("Unable to compute aggregated payback: zero or negative incremental margin. Review margin assumptions.")
        confidence -= 30
    else:
        if aggregated_payback_months <= max_payback_months:
            notes_recommendations.append(f"Aggregated estimated payback is {aggregated_payback_months:.1f} months — within target ({max_payback_months} months).")
        else:
            notes_recommendations.append(f"Aggregated estimated payback is {aggregated_payback_months:.1f} months — exceeds target ({max_payback_months} months). Consider staging, price improvements, or lower-CAPEX options.")
            confidence -= 25

    # schedule feasibility
    if target_months < estimated_total_months:
        notes_recommendations.append(f"Target timeframe ({target_months} months) is tighter than estimated schedule ({estimated_total_months} months). Consider phased rollout.")
        confidence -= 15
    else:
        notes_recommendations.append(f"Target timeframe ({target_months} months) is feasible based on high-level schedule estimate ({estimated_total_months} months).")

    # infrastructure checks
    infra_analysis = {
        "port_capacity_analysis": [
            f"Estimated additional port throughput required: {total_added_mtpa:.2f} MTPA. Ports EM should validate container/berth constraints."
        ],
        "energy_capacity_analysis": [
            f"Estimated incremental energy required: {total_energy_mw:.1f} MW. Energy EM should confirm availability and marginal cost."
        ]
    }

    # choose recommended plant(s): priority to largest added_tpa plants (top 2)
    sorted_by_added = sorted(per_plant_breakdown, key=lambda x: x["added_tpa"], reverse=True)
    top_plants = [f"{p['name']} (+{p['added_tpa']:,} tpa)" for p in sorted_by_added[:2]] if sorted_by_added else []
    recommended_str = ", ".join(top_plants) if top_plants else "—"

    result: Dict[str, Any] = {
        "recommended_plant": recommended_str,
        "expected_increase_tpa": int(total_added_tpa),
        "investment_usd": int(round(total_investment)),
        "roi_months": None if aggregated_payback_months is None else round(aggregated_payback_months, 1),
        "energy_required_mw": round(total_energy_mw, 2),
        "confidence_pct": max(10, min(95, confidence)),
        "em_summaries": {
            "steel_info": {
                "num_plants": len(per_plant_breakdown),
                "plant_recommendations": [f"{p['name']}: add {p['added_tpa']:,} tpa" for p in per_plant_breakdown],
                "plant_distribution": per_plant_breakdown,
            },
            "ports_info": em_summaries.get("ports_info", {}),
            "energy_info": em_summaries.get("energy_info", {}),
        },
        "infrastructure_analysis": infra_analysis,
        "implementation_timeline": {
            "planning_months": baseline_planning,
            "implementation_months": implementation_months_est,
            "stabilization_months": stabilization_months,
        },
        "notes": {
            "assumptions": {
                "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
                "margin_per_ton_usd": MARGIN_PER_TON_USD,
                "mw_per_mtpa": MW_PER_MTPA,
            },
            "recommendations": notes_recommendations,
        },
    }

    return result


# Quick CLI for debugging
if __name__ == "__main__":
    q = (
        "Increase total steel production by 2 MTPA within the next 15 months, "
        "allocating the capacity increase appropriately across all steel plants. "
        "Ensure that the investments required for this upgrade can be recovered within a payback period of less than 3 years."
    )
    import pprint
    pprint.pprint(run_simulation(q))
