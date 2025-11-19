"""
enterprise_manager.py

Provides separate Enterprise Manager evaluations for:
- Steel (manufacturing)
- Ports (logistics)
- Energy (power plants)

Each EM returns structured, explainable outputs that the Group Manager can consume.
"""
from typing import Dict, Any, List

def evaluate_steel(data: Dict[str, Any], budget_usd: float = None) -> List[Dict[str, Any]]:
    """
    Evaluate steel plants and return ranked candidates.
    Same deterministic scoring as before, but clearly identified as Steel-EM output.
    """
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

        candidate = {
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
        }
        results.append(candidate)

    results.sort(key=lambda x: x["score"], reverse=True)
    if budget_usd is not None:
        results = [r for r in results if r["capex_estimate_usd"] <= budget_usd]
    return results


def evaluate_ports(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate port capacity and provide an operational headroom metric.
    Returns a small struct describing port headroom and a simple 'throughput_score'.
    """
    port_capacity = data["ports"]["port2_capacity"]
    util = data["ports"]["current_utilization"]
    headroom_units = max(0.0, (1.0 - util)) * port_capacity
    # Throughput score (higher is better)
    throughput_score = headroom_units / (port_capacity + 1)  # normalized 0..1
    return {
        "port_id": "Port2",
        "port_capacity": port_capacity,
        "current_utilization": util,
        "port_headroom_units": round(headroom_units, 2),
        "throughput_score": round(throughput_score, 3),
        "explainability": {
            "port_headroom_units": round(headroom_units, 2),
            "current_utilization": util
        }
    }


def evaluate_energy(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate energy availability and incremental cost.
    Returns available MW and a conservative headroom (reserving a buffer).
    """
    avail = data["energy"]["available_mw"]
    cost = data["energy"]["cost_per_mw_usd"]
    reserve_buffer = 2.0  # MW reserve to avoid full-commit at plant level
    headroom_mw = max(0.0, avail - reserve_buffer)
    return {
        "energy_available_mw": avail,
        "energy_cost_per_mw_usd": cost,
        "energy_headroom_mw": round(headroom_mw, 2),
        "explainability": {
            "available_mw": avail,
            "reserve_buffer_mw": reserve_buffer
        }
    }
