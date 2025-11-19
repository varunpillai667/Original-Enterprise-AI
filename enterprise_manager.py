# enterprise_manager.py
"""
Provides simple evaluation functions for each Enterprise Manager (steel, ports, energy).
These are intentionally straightforward and deterministic so the prototype is explainable.
"""

from typing import List, Dict, Any

def evaluate_steel(steel_plants: List[Dict[str, Any]], target_increase_tpa: int) -> List[Dict[str, Any]]:
    """
    For each plant, compute a candidate object describing a realistic uplift,
    its capex, ROI, energy need and an explainability dict.
    - feasible_increase_tpa: estimated additional annual tonnes plant can add with operational measures
    """
    candidates = []
    for p in steel_plants:
        capacity = p.get("capacity_tpa", 0)
        util = p.get("utilization", 0.7)
        spare_tpa = int(max(0, capacity * (1 - util)))  # rough spare capacity
        # Estimate feasible increase: min(spare, 20% of capacity) as conservative operational uplift
        feasible = min(spare_tpa, int(0.20 * capacity))
        # If plant is underutilised <0.65, allow slightly larger operational uplift
        if util < 0.65:
            feasible = min(spare_tpa, int(0.30 * capacity))

        # energy and shipments scale roughly with feasible uplift
        energy_required_mw = p.get("energy_required_mw", 0.5) * (feasible / max(1, int(capacity*0.1)))
        # estimate ROI roughly as capex / (annual incremental margin) -> convert to months
        capex = p.get("capex_estimate_usd", 500000)
        # assume incremental monthly profit from uplift: (feasible tpa / capacity_tpa)*100000 USD (simple)
        incr_monthly_income = max(1000, (feasible / max(1, capacity)) * 100000)
        roi_months = max(1, round(capex / incr_monthly_income, 1))

        candidate = {
            "plant_id": p.get("plant_id"),
            "capacity_tpa": capacity,
            "utilization": util,
            "feasible_increase_tpa": feasible,
            "energy_required_mw": round(max(0.1, energy_required_mw), 3),
            "estimated_increase_units": feasible,  # reuse
            "capex_estimate_usd": capex,
            "roi_months": roi_months,
            "explainability": {
                "spare_capacity_tpa": spare_tpa,
                "utilization": util
            }
        }
        candidates.append(candidate)

    # sort by best combination: feasible increase desc, roi asc
    candidates = sorted(candidates, key=lambda x: (-x["feasible_increase_tpa"], x["roi_months"]))
    return candidates

def evaluate_ports(ports_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return aggregate port headroom and per-port info.
    """
    headroom = ports_payload.get("port_headroom_units", 0)
    avg_util = ports_payload.get("current_utilization", 0.85)
    ports_list = ports_payload.get("ports_list", [])
    explain = {"port_headroom_units": headroom, "current_utilization": avg_util}
    return {"port_headroom_units": headroom, "current_utilization": avg_util, "ports_list": ports_list, "explainability": explain}

def evaluate_energy(energy_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return energy headroom and per-plant availability.
    """
    headroom = energy_payload.get("energy_headroom_mw", 0)
    avail = energy_payload.get("energy_available_mw", 0)
    units = energy_payload.get("energy_units_list", [])
    explain = {"energy_headroom_mw": headroom, "energy_available_mw": avail}
    return {"energy_headroom_mw": headroom, "energy_available_mw": avail, "energy_units_list": units, "explainability": explain}
