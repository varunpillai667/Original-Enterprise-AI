"""
Enterprise Manager Logic:
Evaluates steel plants using deterministic scoring:
- spare capacity
- capex penalty
- ROI bonus
- energy score
Produces top-ranked plant options.
"""
from typing import Dict, Any, List

def evaluate_plants(data: Dict[str, Any], budget_usd: float = None) -> List[Dict[str, Any]]:
    plants = data["steel_plants"]
    energy_available = data["energy"]["available_mw"]

    results = []

    for p in plants:
        spare = p["capacity"] * (1 - p["utilization"])
        capex_penalty = 1_000_000 / (p["capex_estimate_usd"] + 1)
        roi_bonus = 12 / (p["roi_months"] + 1)
        energy_score = energy_available / (1 + p["capacity"]/1000)

        score = spare * 0.6 + capex_penalty * 0.25 + roi_bonus * 0.15 + energy_score * 0.1

        feasible_pct = min(25, (spare / p["capacity"]) * 100) if p["capacity"] > 0 else 0
        increase_units = p["capacity"] * feasible_pct / 100
        energy_required = round(increase_units * 0.004, 2)

        results.append({
            "plant_id": p["plant_id"],
            "capacity": p["capacity"],
            "utilization": p["utilization"],
            "capex_estimate_usd": p["capex_estimate_usd"],
            "roi_months": p["roi_months"],
            "spare_capacity_units": round(spare, 2),
            "feasible_increase_pct": round(feasible_pct, 2),
            "estimated_increase_units": round(increase_units, 2),
            "energy_required_mw": energy_required,
            "score": round(score, 3),
            "explainability": {
                "spare_capacity": round(spare, 2),
                "capex_penalty": round(capex_penalty, 3),
                "roi_bonus": round(roi_bonus, 3),
                "energy_score": round(energy_score, 3)
            }
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    if budget_usd is not None:
        results = [r for r in results if r["capex_estimate_usd"] <= budget_usd]

    return results
