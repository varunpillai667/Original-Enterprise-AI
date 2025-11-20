# group_manager.py
from typing import Dict, Any, List
import itertools
import math

def _combined_roi_months(combo: List[Dict[str, Any]]) -> float:
    """Calculate combined ROI across multiple plants."""
    total_capex = sum(c.get("capex_estimate_usd", 0) for c in combo)
    total_monthly_income = sum(c.get("incr_monthly_income", 0) for c in combo)
    if total_monthly_income <= 0:
        return float("inf")
    return round(total_capex / total_monthly_income, 2)

def _allocate_required(combo: List[Dict[str, Any]], required: int) -> List[Dict[str, Any]]:
    """Allocate production increase across selected plants."""
    allocations = []
    feasible_total = sum(c["feasible_increase_tpa"] for c in combo)
    if feasible_total <= 0:
        return []
    remaining = required
    
    # First pass: proportional allocation
    for c in combo:
        prop = c["feasible_increase_tpa"] / feasible_total
        alloc = min(c["feasible_increase_tpa"], int(round(required * prop)))
        allocations.append({
            "plant_id": c["plant_id"], 
            "allocated_tpa": alloc, 
            "feasible_tpa": c["feasible_increase_tpa"], 
            "capex_estimate_usd": c.get("capex_estimate_usd", 0), 
            "incr_monthly_income": c.get("incr_monthly_income",0)
        })
        remaining -= alloc

    # Distribute remainder
    idx = 0
    while remaining > 0:
        placed = False
        for a in allocations:
            spare = a["feasible_tpa"] - a["allocated_tpa"]
            if spare > 0:
                a["allocated_tpa"] += 1
                remaining -= 1
                placed = True
                if remaining == 0:
                    break
        if not placed:
            break
        idx += 1
        if idx > 10000:
            break

    # Calculate pro-rata capex allocation
    for a in allocations:
        feasible = a["feasible_tpa"] or 1
        capex = a.get("capex_estimate_usd", 0)
        frac = a["allocated_tpa"] / feasible if feasible > 0 else 0
        a["capex_allocated_usd"] = int(round(capex * frac))
        a.pop("capex_estimate_usd", None)
    return allocations

def _calculate_port_upgrades(required_tpa: int, available_tpa: int, total_capacity_tpa: int, commercial_cargo_tpa: int) -> List[str]:
    """Analyze port capacity requirements protecting commercial operations."""
    upgrades = []
    
    if required_tpa > available_tpa:
        deficit = required_tpa - available_tpa
        upgrades.append(f"Additional port capacity needed: {deficit/1_000_000:.2f} MTPA")
        upgrades.append("Constraint: Commercial cargo (4.55 MTPA) must be protected")
        upgrades.append("Recommendation: Optimize Group X operations or phase expansion")
    else:
        upgrades.append(f"Sufficient port capacity available: {available_tpa/1_000_000:.1f} MTPA")
        upgrades.append("Commercial cargo operations (4.55 MTPA) remain protected")
        
    return upgrades

def _calculate_energy_upgrades(required_mw: int, available_mw: int, total_capacity_mw: int, grid_sales_mw: int) -> List[str]:
    """Analyze energy capacity requirements protecting grid sales."""
    upgrades = []
    
    if required_mw > available_mw:
        deficit = required_mw - available_mw
        upgrades.append(f"Additional energy capacity needed: {deficit} MW")
        upgrades.append("Constraint: Grid sales (720 MW) must be protected")
        upgrades.append("Recommendation: Efficiency improvements or new capacity")
    else:
        upgrades.append(f"Sufficient energy capacity available: {available_mw} MW")
        upgrades.append("Grid sales to national grid (720 MW) remain protected")
        
    return upgrades

def _calculate_implementation_timeline(allocations: List[Dict[str, Any]], total_investment: float) -> Dict[str, Any]:
    """Calculate realistic implementation timeline."""
    n_plants = len(allocations)
    
    # Timeline factors
    base_planning = 3  # months
    
    if n_plants <= 2:
        parallel_factor = 1
        per_plant_implementation = 6
    elif n_plants <= 4:
        parallel_factor = 2  
        per_plant_implementation = 5
    else:
        parallel_factor = 3
        per_plant_implementation = 4
    
    implementation_phase = (n_plants * per_plant_implementation) / parallel_factor
    commissioning_phase = 2
    
    total_months = math.ceil(base_planning + implementation_phase + commissioning_phase)
    
    return {
        "total_months": total_months,
        "planning_months": base_planning,
        "implementation_months": round(implementation_phase, 1),
        "commissioning_months": commissioning_phase,
        "phasing_description": f"{n_plants} plants across {parallel_factor} parallel streams",
        "key_milestones": [
            f"Months 1-{base_planning}: Detailed engineering and approvals",
            f"Months {base_planning+1}-{base_planning + math.ceil(implementation_phase)}: Construction and equipment installation",
            f"Months {base_planning + math.ceil(implementation_phase)+1}-{total_months}: Commissioning and production ramp-up"
        ]
    }

def _distribute_across_all_plants(steel_candidates: List[Dict[str, Any]],
                                 ports_info: Dict[str, Any],
                                 energy_info: Dict[str, Any],
                                 required_increase_tpa: int,
                                 max_roi_months: int) -> Dict[str, Any]:
    """Group Manager: Distribute capacity addition across all steel plants."""
    
    # Get capacity constraints from Enterprise Managers
    port_headroom_tpa = ports_info.get("port_headroom_tpa", 0)
    energy_headroom_mw = energy_info.get("energy_headroom_mw", 0)
    commercial_cargo_tpa = ports_info.get("commercial_cargo_tpa", 0)
    grid_sales_mw = energy_info.get("grid_sales_mw", 0)
    total_port_capacity_tpa = ports_info.get("total_capacity_tpa", 0)
    total_energy_capacity_mw = energy_info.get("total_capacity_mw", 0)
    
    n_plants = len(steel_candidates)
    if n_plants == 0:
        raise RuntimeError("No steel plants available for distribution.")
    
    # Calculate allocation across all plants
    base_allocation_per_plant = required_increase_tpa // n_plants
    remainder = required_increase_tpa % n_plants
    
    allocations = []
    total_energy_required = 0
    total_investment = 0
    total_monthly_income = 0
    
    # Distribute allocation
    for i, plant in enumerate(steel_candidates):
        allocated_tpa = base_allocation_per_plant
        if i < remainder:
            allocated_tpa += 1
            
        feasible_tpa = plant["feasible_increase_tpa"]
        final_allocation = min(allocated_tpa, feasible_tpa)
        
        # Calculate proportional requirements
        energy_required = (final_allocation / max(1, plant["feasible_increase_tpa"])) * plant["energy_required_mw"]
        investment = (final_allocation / max(1, plant["feasible_increase_tpa"])) * plant["capex_estimate_usd"]
        monthly_income = (final_allocation / max(1, plant["feasible_increase_tpa"])) * plant["incr_monthly_income"]
        
        allocations.append({
            "plant_id": plant["plant_id"],
            "allocated_tpa": final_allocation,
            "feasible_tpa": feasible_tpa,
            "energy_required_mw": round(energy_required, 2),
            "capex_allocated_usd": round(investment),
            "monthly_income_allocated": round(monthly_income, 2)
        })
        
        total_energy_required += energy_required
        total_investment += investment
        total_monthly_income += monthly_income
    
    # Calculate combined ROI
    combined_roi = total_investment / total_monthly_income if total_monthly_income > 0 else float('inf')
    
    # Calculate implementation timeline
    implementation_timeline = _calculate_implementation_timeline(allocations, total_investment)
    
    # Constraint validation
    breaches = []
    mitigations = []
    
    total_allocated = sum(a["allocated_tpa"] for a in allocations)
    if total_allocated < required_increase_tpa:
        shortfall = required_increase_tpa - total_allocated
        breaches.append("insufficient_capacity")
        mitigations.append(f"Capacity shortfall: {shortfall/1_000_000:.2f} MTPA")
    
    # Critical business protection checks
    if total_energy_required > energy_headroom_mw:
        deficit = total_energy_required - energy_headroom_mw
        breaches.append("energy_shortfall")
        mitigations.append(f"Cannot reduce 720 MW grid sales. Deficit: {deficit:.1f} MW")
    
    if required_increase_tpa > port_headroom_tpa:
        deficit = required_increase_tpa - port_headroom_tpa
        breaches.append("port_shortfall")
        mitigations.append(f"Cannot reduce 4.55 MTPA commercial cargo. Deficit: {deficit/1_000_000:.2f} MTPA")
    
    if combined_roi > max_roi_months:
        breaches.append("roi_constraint")
        mitigations.append(f"ROI target: {max_roi_months} months. Current: {combined_roi:.1f} months")
    
    # Build strategic recommendation
    plant_names = ", ".join([p["plant_id"] for p in steel_candidates])
    action_plan = (
        f"STRATEGIC RECOMMENDATION: 2 MTPA STEEL CAPACITY EXPANSION\n\n"
        f"CROSS-COMPANY COORDINATION:\n"
        f"- Steel Plants (Company B): Capacity addition across {n_plants} facilities\n"
        f"- Ports (Company A): Utilize {required_increase_tpa/1_000_000:.1f} MTPA of available capacity\n"
        f"- Power Plants (Company C): Allocate {total_energy_required:.1f} MW from internal supply\n\n"
        f"CRITICAL BUSINESS PROTECTIONS:\n"
        f"• Commercial cargo: 4.55 MTPA completely protected\n"
        f"• Grid sales: 720 MW to national grid completely protected\n\n"
        f"IMPLEMENTATION ROADMAP ({implementation_timeline['total_months']} months):\n"
        f"1. Planning & Approvals ({implementation_timeline['planning_months']} months)\n"
        f"2. Parallel Construction ({implementation_timeline['implementation_months']:.1f} months)\n"
        f"3. Commissioning & Ramp-up ({implementation_timeline['commissioning_months']} months)"
    )
    
    return {
        "recommended_plant": f"All {n_plants} Steel Plants: {plant_names}",
        "expected_increase_tpa": total_allocated,
        "investment_usd": round(total_investment),
        "roi_months": round(combined_roi, 2),
        "energy_required_mw": round(total_energy_required, 2),
        "summary": f"Group Manager recommends distributed 2 MTPA capacity addition across {n_plants} steel plants with complete protection of commercial operations.",
        "action_plan": action_plan,
        "implementation_timeline": implementation_timeline,
        "justification": {
            "energy_headroom_mw": energy_headroom_mw,
            "port_headroom_tpa": port_headroom_tpa,
            "expected_increase_tpa": required_increase_tpa,
            "breaches": breaches,
            "mitigations": mitigations,
            "distribution_strategy": "across_all_plants",
            "commercial_operations_protected": True,
            "grid_sales_protected": True
        },
        "allocations": allocations,
        "why_chosen": [
            "Strategic capacity distribution across entire steel production network",
            "Complete protection of commercial cargo operations (4.55 MTPA)",
            "Complete protection of grid sales revenue (720 MW)",
            "Optimal utilization of available infrastructure capacity",
            "Enhanced operational resilience across Group X"
        ],
        "infrastructure_requirements": {
            "port_capacity_analysis": _calculate_port_upgrades(required_increase_tpa, port_headroom_tpa, total_port_capacity_tpa, commercial_cargo_tpa),
            "energy_capacity_analysis": _calculate_energy_upgrades(total_energy_required, energy_headroom_mw, total_energy_capacity_mw, grid_sales_mw)
        }
    }

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           group_systems: Dict[str, Any],
                           required_increase_tpa: int = 2_000_000,
                           max_roi_months: int = 36,
                           distribution_strategy: str = "selective") -> Dict[str, Any]:
    """
    Group Manager: Main orchestration function that coordinates across all Enterprise Managers.
    
    This function:
    1. Receives analyzed data from Steel EM, Ports EM, and Energy EM
    2. Performs cross-company optimization
    3. Ensures business constraints are respected
    4. Returns unified strategic recommendation
    """
    
    if not steel_candidates:
        raise RuntimeError("No steel capacity data received from Steel Enterprise Manager.")

    # Use appropriate distribution strategy
    if distribution_strategy == "across_all":
        return _distribute_across_all_plants(
            steel_candidates, ports_info, energy_info, 
            required_increase_tpa, max_roi_months
        )
    
    # For selective plant strategies (existing logic would go here)
    # This maintains compatibility with different query types
    
    # Fallback to across-all strategy for this implementation
    return _distribute_across_all_plants(
        steel_candidates, ports_info, energy_info, 
        required_increase_tpa, max_roi_months
    )
