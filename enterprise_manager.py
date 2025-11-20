# enterprise_manager.py
from typing import List, Dict, Any

def evaluate_steel(steel_plants: List[Dict[str, Any]], target_increase_tpa: int) -> List[Dict[str, Any]]:
    """
    For each plant, compute a candidate describing short-term operational uplift (feasible_increase_tpa),
    short-term energy need, capex estimate for operational uplift, and an estimate of expansion cost per tpa
    (used when we need to add capacity via investment).
    """
    candidates = []
    for p in steel_plants:
        capacity = p.get("capacity_tpa", 0)
        util = p.get("utilization", 0.7)
        spare_tpa = int(max(0, capacity * (1 - util)))

        # Operational uplift conservative: up to 20% of capacity limited by spare
        feasible = min(spare_tpa, int(0.20 * capacity))
        if util < 0.65:
            feasible = min(spare_tpa, int(0.30 * capacity))

        # energy estimate for operational uplift (proxy)
        base_energy_per_10pct = p.get("energy_required_mw", 0.5)
        if capacity > 0:
            energy_required_mw = base_energy_per_10pct * (feasible / max(1, 0.10 * capacity))
        else:
            energy_required_mw = base_energy_per_10pct

        # Operational uplift capex (assume much lower than expansion capex)
        op_capex = max(50_000, int(0.1 * p.get("capex_estimate_usd", 500_000)))  # proxy for small changes

        # Expansion cost estimate per tpa (this is the key addition)
        # Proxy: $ per annual tonne. Tuneable for your demo.
        # Example: $3000 per tonne/year cost to add sustained annual capacity (this is demo param)
        expansion_cost_per_tpa = p.get("expansion_cost_per_tpa_usd", 3_000)

        # Capex for a full feasible expansion of X tpa would be expansion_cost_per_tpa * desired tpa
        capex = p.get("capex_estimate_usd", 500_000)

        # incremental revenue proxy (more generous to allow combined ROI)
        annual_incremental_revenue = max(50_000, (feasible / max(1, capacity)) * 3_000_000)
        incr_monthly_income = max(500, round(annual_incremental_revenue / 12, 2))
        # initial ROI based on op_capex only
        roi_months = max(1, round(op_capex / incr_monthly_income, 1))

        candidate = {
            "plant_id": p.get("plant_id"),
            "capacity_tpa": capacity,
            "utilization": util,
            "feasible_increase_tpa": feasible,
            "energy_required_mw": round(max(0.1, energy_required_mw), 3),
            "op_capex_estimate_usd": op_capex,
            "capex_estimate_usd": capex,
            "expansion_cost_per_tpa_usd": expansion_cost_per_tpa,
            "roi_months": roi_months,
            "incr_monthly_income": incr_monthly_income,
            "explainability": {
                "spare_capacity_tpa": spare_tpa,
                "utilization": util
            }
        }
        candidates.append(candidate)

    candidates = sorted(candidates, key=lambda x: (-x["feasible_increase_tpa"], x["roi_months"]))
    return candidates

def evaluate_ports(ports_payload: Dict[str, Any]) -> Dict[str, Any]:
    ports_list = ports_payload.get("ports_list", [])
    total_capacity_tpa = 0
    total_throughput_tpa = 0
    for p in ports_list:
        cap_mt = p.get("annual_capacity_mt", 0.0)
        thr_mt = p.get("current_throughput_mt", 0.0)
        total_capacity_tpa += int(cap_mt * 1_000_000)
        total_throughput_tpa += int(thr_mt * 1_000_000)
    headroom_tpa = max(0, total_capacity_tpa - total_throughput_tpa)
    return {"port_headroom_tpa": headroom_tpa, "ports_list": ports_list, "explainability": {"port_headroom_tpa": headroom_tpa}}

def evaluate_energy(energy_payload: Dict[str, Any]) -> Dict[str, Any]:
    units = energy_payload.get("energy_units_list", [])
    total_available = 0
    for u in units:
        total_available += u.get("available_mw", 0)
    return {"energy_headroom_mw": total_available, "energy_available_mw": total_available, "energy_units_list": units, "explainability": {"energy_headroom_mw": total_available}}
