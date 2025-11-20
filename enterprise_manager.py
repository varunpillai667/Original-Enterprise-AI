# enterprise_manager.py
from typing import List, Dict, Any

def evaluate_steel(steel_plants: List[Dict[str, Any]], target_increase_tpa: int) -> List[Dict[str, Any]]:
    """
    Steel Enterprise Manager: Analyzes steel plant capacity for expansion.
    
    Processes data from LOCAL Nodes at each steel plant and provides
    capacity analysis to Group Manager.
    """
    candidates = []
    for p in steel_plants:
        capacity = p.get("capacity_tpa", 0)
        util = p.get("utilization", 0.7)
        
        # Capacity addition analysis
        if util < 0.70:
            feasible = int(0.30 * capacity)  # Lower utilization = more expansion potential
        elif util < 0.80:
            feasible = int(0.20 * capacity)  
        else:
            feasible = int(0.15 * capacity)  # High utilization = limited expansion
        
        # Energy requirements for new capacity
        energy_per_100k_tpa = 0.08
        energy_required_mw = (feasible / 100000) * energy_per_100k_tpa
        
        # Investment requirements
        capex_per_tonne = 400
        capex = int(feasible * capex_per_tonne)
        
        # Revenue projection
        revenue_per_tonne = 150
        annual_incremental_revenue = feasible * revenue_per_tonne
        incr_monthly_income = max(1000, round(annual_incremental_revenue / 12, 2))
        roi_months = max(1, round(capex / incr_monthly_income, 1))

        candidate = {
            "plant_id": p.get("plant_id"),
            "capacity_tpa": capacity,
            "utilization": util,
            "feasible_increase_tpa": feasible,
            "energy_required_mw": round(max(0.1, energy_required_mw), 3),
            "capex_estimate_usd": capex,
            "roi_months": roi_months,
            "incr_monthly_income": incr_monthly_income,
            "explainability": {
                "current_capacity_tpa": capacity,
                "utilization": util,
                "capacity_addition_type": "New steel production capacity",
                "analysis_note": "Steel EM analysis based on LOCAL Node data"
            }
        }
        candidates.append(candidate)

    # Return plants sorted by expansion potential
    candidates = sorted(candidates, key=lambda x: (-x["feasible_increase_tpa"], x["roi_months"]))
    return candidates

def evaluate_ports(ports_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ports Enterprise Manager: Analyzes port capacity for increased throughput.
    
    Processes data from LOCAL Nodes at each port and provides capacity
    analysis to Group Manager with commercial operations protection.
    """
    ports_list = ports_payload.get("ports_list", [])
    total_capacity_tpa = 0
    total_throughput_tpa = 0
    
    for p in ports_list:
        cap_mt = p.get("annual_capacity_mt", 0.0)
        thr_mt = p.get("current_throughput_mt", 0.0)
        total_capacity_tpa += int(cap_mt * 1_000_000)
        total_throughput_tpa += int(thr_mt * 1_000_000)
    
    # Capacity analysis (based on the 10 MTPA total, 6.5 MTPA current example)
    available_headroom_tpa = total_capacity_tpa - total_throughput_tpa
    
    # Business constraint: 70% commercial cargo must be protected
    commercial_cargo_tpa = total_throughput_tpa * 0.70
    group_x_cargo_tpa = total_throughput_tpa * 0.30

    return {
        "port_headroom_tpa": available_headroom_tpa, 
        "current_throughput_tpa": total_throughput_tpa,
        "total_capacity_tpa": total_capacity_tpa,
        "commercial_cargo_tpa": commercial_cargo_tpa,
        "group_x_cargo_tpa": group_x_cargo_tpa,
        "ports_list": ports_list, 
        "explainability": {
            "total_capacity_mtpa": f"{total_capacity_tpa/1_000_000:.1f}",
            "current_throughput_mtpa": f"{total_throughput_tpa/1_000_000:.1f}",
            "commercial_cargo_mtpa": f"{commercial_cargo_tpa/1_000_000:.1f} (70% - PROTECTED)",
            "group_x_cargo_mtpa": f"{group_x_cargo_tpa/1_000_000:.1f} (30% - Group X usage)",
            "available_headroom_mtpa": f"{available_headroom_tpa/1_000_000:.1f}",
            "analysis_note": "Ports EM analysis with commercial operations protection"
        }
    }

def evaluate_energy(energy_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Energy Enterprise Manager: Analyzes power generation capacity.
    
    Processes data from LOCAL Nodes at each power plant and provides
    capacity analysis to Group Manager with grid sales protection.
    """
    units = energy_payload.get("energy_units_list", [])
    total_available = 0
    total_capacity = 0
    current_generation = 0
    
    for u in units:
        capacity = u.get("capacity_mw", 0)
        available = u.get("available_mw", 0)
        total_available += available
        total_capacity += capacity
        current_generation += (capacity - available)
    
    # Business constraint: 60% grid sales must be protected
    grid_sales_mw = current_generation * 0.60
    group_x_usage_mw = current_generation * 0.40

    return {
        "energy_headroom_mw": total_available, 
        "energy_available_mw": total_available,
        "total_capacity_mw": total_capacity,
        "current_generation_mw": current_generation,
        "grid_sales_mw": grid_sales_mw,
        "group_x_usage_mw": group_x_usage_mw,
        "energy_units_list": units, 
        "explainability": {
            "total_capacity_mw": total_capacity,
            "current_generation_mw": current_generation,
            "grid_sales_mw": f"{grid_sales_mw} MW (60% - PROTECTED)",
            "group_x_usage_mw": f"{group_x_usage_mw} MW (40% - Group X usage)",
            "available_capacity_mw": f"{total_available} MW",
            "analysis_note": "Energy EM analysis with grid sales protection"
        }
    }
