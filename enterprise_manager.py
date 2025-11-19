"""
enterprise_manager.py

Three Enterprise Managers:
- evaluate_steel()
- evaluate_ports()
- evaluate_energy()

Each EM consumes company HQ inputs (simulated) and Local Node payloads.
Now returns both aggregated metrics and detailed unit lists for UI.
"""
from typing import Dict, Any, List
import random

def evaluate_steel(company_hq: Dict[str, Any], local_node_payload: Dict[str, Any], budget_usd: float = None) -> List[Dict[str, Any]]:
    plants = local_node_payload.get("steel_plants", [])
    energy_avail = local_node_payload.get("energy", {}).get("available_mw", 0)

    results = []
    for p in plants:
        spare = p["capacity"] * (1 - p["utilization"])
        capex_penalty = 1_000_000 / (p["capex_estimate_usd"] + 1)
        roi_bonus = 12 / (p["roi_months"] + 1)
        energy_score = energy_avail / (1 + p["capacity"]/1000)
        score = spare * 0.6 + capex_penalty * 0.25 + roi_bonus * 0.15 + energy_score * 0.1
        feasible_pct = min(25, (spare / p["capacity"]) * 100) if p["capacity"] > 0 else 0
        increase_units = p["capacity"] * feasible_pct / 100
        energy_required = round(increase_units * 0.004, 2)

        results.append({
            "plant_id": p["plant_id"],
            "score": round(score, 3),
            "feasible_increase_pct": round(feasible_pct, 2),
            "estimated_increase_units": round(increase_units, 2),
            "energy_required_mw": energy_required,
            "capex_estimate_usd": p["capex_estimate_usd"],
            "roi_months": p["roi_months"],
            "explainability": {"spare_capacity": round(spare,2), "capex_penalty": round(capex_penalty,3)}
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    if budget_usd is not None:
        results = [r for r in results if r["capex_estimate_usd"] <= budget_usd]
    return results

def evaluate_ports(company_hq: Dict[str, Any], local_node_payload: Dict[str, Any]) -> Dict[str, Any]:
    # Build a detailed list of 4 ports (per your docs). Use the single port capacity as baseline.
    ports_raw = local_node_payload.get("ports", {})
    base_capacity = ports_raw.get("port2_capacity", 15000)
    base_util = ports_raw.get("current_utilization", 0.84)

    ports_list = []
    for i in range(4):
        cap = int(base_capacity * (0.9 + 0.05 * i))  # vary capacities slightly
        util = round(min(0.95, base_util + (i * 0.01)), 2)
        ports_list.append({
            "port_id": f"Port {i+1}",
            "capacity": cap,
            "utilization": util
        })

    # Aggregate headroom computed from all ports
    total_headroom = sum([p["capacity"] * (1 - p["utilization"]) for p in ports_list])
    return {
        "port_headroom_units": round(total_headroom, 2),
        "current_utilization": round(sum([p["utilization"] for p in ports_list]) / len(ports_list), 2),
        "throughput_score": round(total_headroom / (sum([p["capacity"] for p in ports_list]) + 1), 3),
        "ports_list": ports_list,
        "explainability": {"port_headroom_units": round(total_headroom,2)}
    }

def evaluate_energy(company_hq: Dict[str, Any], local_node_payload: Dict[str, Any]) -> Dict[str, Any]:
    # Build 3 power plant units (per your docs). Distribute available MW across them.
    energy_raw = local_node_payload.get("energy", {})
    avail = energy_raw.get("available_mw", 20)
    cost = energy_raw.get("cost_per_mw_usd", 1100)

    # create 3 plants with capacities and utilization
    energy_units = []
    shares = [0.4, 0.35, 0.25]
    for i, s in enumerate(shares):
        cap = round(max(5, avail / s), 2)  # approximate nominal capacity
        util = round(min(0.98, 0.6 + i * 0.1), 2)
        energy_units.append({
            "plant_id": f"PP{i+1}",
            "capacity_mw": cap,
            "utilization": util,
            "available_mw": round(avail * s, 2)
        })

    # conservative headroom (reserve 2 MW)
    headroom = max(0.0, avail - 2.0)
    return {
        "energy_available_mw": avail,
        "energy_headroom_mw": round(headroom, 2),
        "energy_units_list": energy_units,
        "energy_cost_per_mw_usd": cost,
        "explainability": {"available_mw": avail, "reserve_buffer_mw": 2.0}
    }
