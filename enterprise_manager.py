"""
enterprise_manager.py
Implements Enterprise Manager logic for the Steel company.
Responsibilities:
- Receive preprocessed data from LOCAL Node(s)
- Evaluate candidate plants using deterministic scoring (capacity, utilization, capex, roi)
- Provide recommended actions (production increase %, estimated capex, energy required)
- Provide explainability metadata (feature contributions)
This is a simplified, deterministic stand-in for the EM decision engine described in the whitepaper.
"""
from typing import Dict, Any, List, Tuple

def evaluate_plants(data: Dict[str, Any], budget_usd: float = None) -> List[Dict[str, Any]]:
    """
    Score plants and produce candidate recommendations.
    Scoring heuristics (simple, explainable):
      - SpareCapacity = capacity * (1 - utilization)
      - CapEx penalty (lower capex -> higher score)
      - ROI preference (lower roi_months -> higher score)
    """
    plants = data["steel_plants"]
    energy_available = data["energy"]["available_mw"]
    results = []
    for p in plants:
        spare = p["capacity"] * (1 - p["utilization"])
        # Normalized heuristics
        capex_penalty = 1_000_000 / (p["capex_estimate_usd"] + 1)  # higher when capex low
        roi_bonus = 12 / (p["roi_months"] + 1)  # higher when ROI months low
        energy_score = energy_available / (1 + p["capacity"]/1000)  # preference for smaller plants wrt available energy
        score = spare * 0.6 + capex_penalty * 0.25 + roi_bonus * 0.15 + energy_score * 0.1
        # Estimate feasible increase as a percent of spare capacity (capped at 25% to be conservative)
        if p["capacity"] > 0:
            feasible_pct = min(25, (spare / p["capacity"]) * 100)
        else:
            feasible_pct = 0
        estimated_increase_units = p["capacity"] * (feasible_pct / 100)
        # Estimate required MW (assume 0.004 MW per unit capacity as a simple conversion)
        energy_required_mw = round(estimated_increase_units * 0.004, 2)
        candidate = {
            "plant_id": p["plant_id"],
            "capacity": p["capacity"],
            "utilization": p["utilization"],
            "capex_estimate_usd": p["capex_estimate_usd"],
            "roi_months": p["roi_months"],
            "spare_capacity_units": round(spare, 2),
            "feasible_increase_pct": round(feasible_pct, 2),
            "estimated_increase_units": round(estimated_increase_units, 2),
            "energy_required_mw": energy_required_mw,
            "score": round(score, 3),
            "explainability": {
                "spare_capacity": round(spare, 2),
                "capex_penalty": round(capex_penalty, 3),
                "roi_bonus": round(roi_bonus, 3),
                "energy_score": round(energy_score, 3)
            }
        }
        results.append(candidate)
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    # If budget provided, filter out candidates exceeding budget (capex_estimate_usd)
    if budget_usd is not None:
        results = [r for r in results if r["capex_estimate_usd"] <= budget_usd]
    return results
