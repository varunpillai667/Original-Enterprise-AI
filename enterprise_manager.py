# enterprise_manager.py
"""
Simple evaluation functions for each Enterprise Manager (steel, ports, energy).
"""

from typing import List, Dict, Any

def evaluate_steel(steel_plants: List[Dict[str, Any]], target_increase_tpa: int) -> List[Dict[str, Any]]:
    """
    For each plant, compute a candidate object describing a realistic uplift,
    its capex, ROI, energy need and explainability dict.
    """
    candidates = []
    for p in steel_plants:
        capacity = p.get("capacity_tpa", 0)
        util = p.get("utilization", 0.7)
        spare_tpa = int(max(0, capacity * (1 - util)))  # rough spare capacity in tpa

        # Conservative operational uplift: up to 20% of capacity, but cannot exceed spare capacity
        feasible = min(spare_tpa, int(0.20 * capacity))
        if util < 0.65:
            feasible = min(spare_tpa, int(0.30 * capacity))

        # energy scales with feasible uplift relative to a baseline factor
        base_energy_per_10pct = p.get("energy_required_mw", 0.5)  # baseline number in mock is per ~10% uplift
        if capacity > 0:
            # normalize: assume base energy corresponds to ~10% capacity uplift
            energy_required_mw = base_energy_per_10pct * (feasible / max(1, 0.10 * capacity))
        else:
            energy_required_mw = base_energy_per_10pct

        capex = p.get("capex_estimate_usd", 500000)
        # simple incremental monthly income estimate => used for ROI
        incr_monthly_income = max(1000, (feasible / max(1, capacity)) * 200000)
        roi_months = max(1, round(capex / incr_monthly_income, 1))

        candidate = {
            "plant_id": p.get("plant_id"),
            "capacity_tpa": capacity,
            "utilization": util,
            "feasible_increase_tpa": feasible,
            "energy_required_mw": round(max(0.1, energy_required_mw), 3),
            "capex_estimate_usd": capex,
            "roi_months": roi_months,
            "explainability": {
                "spare_capacity_tpa": spare_tpa,
                "utilization": util
            }
        }
        candidates.append(candidate)

    # sort by feasible increase desc then ROI asc
    candidates = sorted(candidates, key=lambda x: (-x["feasible_increase_tpa"], x["roi_months"]))
    return candidates

def evaluate_ports(ports_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert port capacities in Mtpa to tonnes and compute headroom (tpa).
    ports_payload contains ports_list entries with:
      - annual_capacity_mt (million tonnes per annum)
      - current_throughput_mt (million tonnes per annum)
    Returns aggregate headroom in tonnes (tpa) and per-port details.
    """
    ports_list = ports_payload.get("ports_list", [])
    total_capacity_tpa = 0
    total_throughput_tpa = 0
    for p in ports_list:
        cap_mt = p.get("annual_capacity_mt", 0.0)
        thr_mt = p.get("current_throughput_mt", 0.0)
        total_capacity_tpa += int(cap_mt * 1_000_000)
        total_throughput_tpa += int(thr_mt * 1_000_000)

    headroom_tpa = max(0, total_capacity_tpa - total_throughput_tpa)
    explain = {"port_headroom_tpa": headroom_tpa}
    return {"port_headroom_tpa": headroom_tpa, "ports_list": ports_list, "explainability": explain}

def evaluate_energy(energy_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate energy availability across plants.
    energy_units_list entries have:
      - plant_id
      - capacity_mw
      - available_mw
    """
    units = energy_payload.get("energy_units_list", [])
    total_available = 0
    total_capacity = 0
    for u in units:
        total_available += u.get("available_mw", 0)
        total_capacity += u.get("capacity_mw", 0)
    explain = {"energy_headroom_mw": total_available, "energy_available_mw": total_available}
    return {"energy_headroom_mw": total_available, "energy_available_mw": total_available, "energy_units_list": units, "explainability": explain}
