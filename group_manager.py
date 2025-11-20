# group_manager.py
from typing import Dict, Any, List
import itertools
import math

def _combined_roi_months(combo: List[Dict[str, Any]]) -> float:
    total_capex = sum(c.get("capex_estimate_usd", 0) for c in combo)
    total_monthly_income = sum(c.get("incr_monthly_income", 0) for c in combo)
    if total_monthly_income <= 0:
        return float("inf")
    return round(total_capex / total_monthly_income, 2)

def _allocate_required(combo: List[Dict[str, Any]], required: int) -> List[Dict[str, Any]]:
    """
    Allocate required tpa across combo plants proportionally to feasible_increase_tpa
    without exceeding per-plant feasible.
    Returns list of dicts with plant_id, allocated_tpa, feasible_tpa, capex_allocated_usd (pro rata).
    """
    allocations = []
    feasible_total = sum(c["feasible_increase_tpa"] for c in combo)
    if feasible_total <= 0:
        return []
    remaining = required
    # allocate proportionally but cap at feasible per plant and adjust
    # first pass proportional allocation
    for c in combo:
        prop = c["feasible_increase_tpa"] / feasible_total
        alloc = min(c["feasible_increase_tpa"], int(round(required * prop)))
        allocations.append({"plant_id": c["plant_id"], "allocated_tpa": alloc, "feasible_tpa": c["feasible_increase_tpa"], "capex_estimate_usd": c.get("capex_estimate_usd", 0), "incr_monthly_income": c.get("incr_monthly_income",0)})
        remaining -= alloc

    # distribute any remaining one-by-one to plants with spare feasible capacity
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
            # cannot allocate more
            break
        idx += 1
        if idx > 10000:
            break

    # compute capex allocation pro-rata to allocated_tpa relative to feasible_tpa
    for a in allocations:
        feasible = a["feasible_tpa"] or 1
        capex = a.get("capex_estimate_usd", 0)
        # allocate capex proportionally to fraction of feasible used
        frac = a["allocated_tpa"] / feasible if feasible > 0 else 0
        a["capex_allocated_usd"] = int(round(capex * frac))
        # remove internal fields not needed further
        a.pop("capex_estimate_usd", None)
    return allocations

def _calculate_port_upgrades(required_tpa: int, available_tpa: int) -> List[str]:
    """Calculate what port upgrades are needed."""
    upgrades = []
    if required_tpa > available_tpa:
        deficit = required_tpa - available_tpa
        upgrades.append(f"Additional port capacity needed: {deficit:,} tpa ({deficit/1_000_000:.2f} MTPA)")
        upgrades.append("Consider: Berth optimization, yard expansion, or temporary logistics hubs")
    else:
        upgrades.append("Existing port capacity sufficient with optimized scheduling")
    return upgrades

def _calculate_energy_upgrades(required_mw: int, available_mw: int) -> List[str]:
    """Calculate what energy upgrades are needed."""
    upgrades = []
    if required_mw > available_mw:
        deficit = required_mw - available_mw
        upgrades.append(f"Additional energy capacity needed: {deficit} MW")
        upgrades.append("Consider: Peak load management, temporary power contracts, or efficiency improvements")
    else:
        upgrades.append("Existing energy capacity sufficient with load balancing")
    return upgrades

def _distribute_across_all_plants(steel_candidates: List[Dict[str, Any]],
                                 ports_info: Dict[str, Any],
                                 energy_info: Dict[str, Any],
                                 required_increase_tpa: int,
                                 max_roi_months: int) -> Dict[str, Any]:
    """
    NEW: Distribute production increase evenly across ALL steel plants
    while considering port and energy constraints.
    """
    port_headroom_tpa = ports_info.get("port_headroom_tpa", 0)
    energy_headroom_mw = energy_info.get("energy_headroom_mw", 0)
    
    n_plants = len(steel_candidates)
    if n_plants == 0:
        raise RuntimeError("No steel plants available for distribution.")
    
    # Calculate base allocation per plant
    base_allocation_per_plant = required_increase_tpa // n_plants
    remainder = required_increase_tpa % n_plants
    
    allocations = []
    total_energy_required = 0
    total_investment = 0
    total_monthly_income = 0
    
    # Distribute allocation considering each plant's capacity constraints
    for i, plant in enumerate(steel_candidates):
        # Allocate base amount plus remainder distribution
        allocated_tpa = base_allocation_per_plant
        if i < remainder:
            allocated_tpa += 1
            
        # Ensure we don't exceed plant's feasible capacity
        feasible_tpa = plant["feasible_increase_tpa"]
        final_allocation = min(allocated_tpa, feasible_tpa)
        
        # Calculate proportional energy and investment
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
    
    # Check constraints
    breaches = []
    mitigations = []
    
    total_allocated = sum(a["allocated_tpa"] for a in allocations)
    if total_allocated < required_increase_tpa:
        breaches.append("insufficient_capacity_distribution")
        mitigations.append(f"Consider timeline extension or additional plants. Shortfall: {required_increase_tpa - total_allocated:,} tpa")
    
    if total_energy_required > energy_headroom_mw:
        breaches.append("energy_shortfall")
        mitigations.append(f"Phase implementation or procure additional energy. Deficit: {total_energy_required - energy_headroom_mw:.1f} MW")
    
    if required_increase_tpa > port_headroom_tpa:
        breaches.append("port_throughput_shortfall")
        mitigations.append(f"Stagger shipments or optimize logistics. Deficit: {required_increase_tpa - port_headroom_tpa:,} tpa")
    
    if combined_roi > max_roi_months:
        breaches.append("roi_constraint")
        mitigations.append(f"Optimize investment allocation or extend recovery period. Current ROI: {combined_roi:.1f} months")
    
    # Build action plan
    plant_names = ", ".join([p["plant_id"] for p in steel_candidates])
    action_plan = (
        f"Distributed Action Plan across ALL steel plants ({plant_names}) to achieve +{required_increase_tpa:,} tpa.\n\n"
        f"1) Allocate production increases evenly across all {n_plants} plants\n"
        f"2) Coordinate energy dispatch of {total_energy_required:.1f} MW across power plants\n"
        f"3) Reserve port throughput capacity of {required_increase_tpa:,} tpa\n"
        f"4) Implement phased rollout with weekly progress monitoring\n"
        f"5) Cross-train workforce for flexible resource allocation"
    )
    
    return {
        "recommended_plant": f"ALL PLANTS: {plant_names}",
        "expected_increase_tpa": total_allocated,
        "investment_usd": round(total_investment),
        "roi_months": round(combined_roi, 2),
        "energy_required_mw": round(total_energy_required, 2),
        "summary": f"Production increase distributed across all {n_plants} steel plants with combined ROI analysis.",
        "action_plan": action_plan,
        "justification": {
            "energy_headroom_mw": energy_headroom_mw,
            "port_headroom_tpa": port_headroom_tpa,
            "expected_increase_tpa": required_increase_tpa,
            "breaches": breaches,
            "mitigations": mitigations,
            "distribution_strategy": "even_across_all_plants"
        },
        "explainability": {
            "steel_em": [p.get("explainability", {}) for p in steel_candidates],
            "ports_em": ports_info.get("explainability", {}),
            "energy_em": energy_info.get("explainability", {})
        },
        "allocations": allocations,
        "why_chosen": [
            "Strategic decision to distribute capacity increase across entire steel production network",
            "Enhances operational resilience by not over-relying on single plants",
            "Allows for coordinated infrastructure upgrades across the enterprise",
            "Supports balanced workforce development and resource allocation"
        ],
        "infrastructure_requirements": {
            "ports_capacity_utilization": f"{(required_increase_tpa / port_headroom_tpa * 100) if port_headroom_tpa > 0 else 0:.1f}%",
            "energy_capacity_utilization": f"{(total_energy_required / energy_headroom_mw * 100) if energy_headroom_mw > 0 else 0:.1f}%",
            "recommended_port_upgrades": _calculate_port_upgrades(required_increase_tpa, port_headroom_tpa),
            "recommended_energy_upgrades": _calculate_energy_upgrades(total_energy_required, energy_headroom_mw)
        }
    }

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           group_systems: Dict[str, Any],
                           required_increase_tpa: int = 2_000_000,
                           max_roi_months: int = 36,
                           distribution_strategy: str = "selective") -> Dict[str, Any]:
    
    if not steel_candidates:
        raise RuntimeError("No steel candidates provided to Group Manager.")

    # NEW: Use distribution strategy
    if distribution_strategy == "across_all":
        return _distribute_across_all_plants(
            steel_candidates, ports_info, energy_info, 
            required_increase_tpa, max_roi_months
        )
    
    # Existing selective logic for backward compatibility
    port_headroom_tpa = ports_info.get("port_headroom_tpa", 0)
    energy_headroom_mw = energy_info.get("energy_headroom_mw", 0)

    n = len(steel_candidates)

    # Try all combinations 1..N (prefer smaller combos)
    for r in range(1, n + 1):
        for combo in itertools.combinations(steel_candidates, r):
            total_increase = sum(c["feasible_increase_tpa"] for c in combo)
            total_energy_req = sum(c["energy_required_mw"] for c in combo)
            total_shipment_units = total_increase
            combined_roi = _combined_roi_months(combo)
            if total_increase >= required_increase_tpa and total_energy_req <= energy_headroom_mw and total_shipment_units <= port_headroom_tpa and combined_roi <= max_roi_months:
                # compute allocation per plant for clarity in UI
                allocations = _allocate_required(combo, required_increase_tpa)
                names = ", ".join([c["plant_id"] for c in combo])
                action_plan = (
                    f"Combined Action Plan across {names} to achieve +{required_increase_tpa:,} tpa.\n"
                    "1) Run coordinated pilots at selected plants and validate processes.\n"
                    f"2) Allocate energy dispatch of {total_energy_req} MW.\n"
                    f"3) Reserve port throughput of approx {required_increase_tpa:,} tpa and stagger shipments.\n"
                    "4) Monitor KPIs weekly and scale rollout."
                )
                return {
                    "recommended_plant": names,
                    "expected_increase_tpa": required_increase_tpa,
                    "investment_usd": sum(c.get("capex_estimate_usd", 0) for c in combo),
                    "roi_months": combined_roi,
                    "energy_required_mw": total_energy_req,
                    "summary": "Combined candidate set meets target and combined ROI constraint.",
                    "action_plan": action_plan,
                    "justification": {
                        "energy_headroom_mw": energy_headroom_mw,
                        "port_headroom_tpa": port_headroom_tpa,
                        "expected_increase_tpa": required_increase_tpa,
                        "breaches": [],
                        "mitigations": [],
                        "distribution_strategy": "selective_combination"
                    },
                    "explainability": {
                        "steel_em": [c.get("explainability", {}) for c in combo],
                        "ports_em": ports_info.get("explainability", {}),
                        "energy_em": energy_info.get("explainability", {})
                    },
                    "allocations": allocations,
                    "why_chosen": [
                        "Selected plants collectively deliver the required uplift.",
                        "Combined ROI meets the recovery constraint.",
                        "Energy and port headroom are sufficient for the plan."
                    ]
                }

    # If no perfect combo found, attempt greedy selection allowing combined ROI <= max
    sorted_candidates = sorted(steel_candidates, key=lambda x: (-x["feasible_increase_tpa"], x["roi_months"]))
    selected = []
    total_inc = 0
    total_energy = 0
    total_shipments = 0
    for c in sorted_candidates:
        # tentatively add and compute combined ROI
        selected.append(c)
        total_inc += c["feasible_increase_tpa"]
        total_energy += c["energy_required_mw"]
        total_shipments += c["feasible_increase_tpa"]
        combined_roi = _combined_roi_months(selected)
        if total_inc >= required_increase_tpa and total_energy <= energy_headroom_mw and total_shipments <= port_headroom_tpa and combined_roi <= max_roi_months:
            allocations = _allocate_required(selected, required_increase_tpa)
            names = ", ".join([s["plant_id"] for s in selected])
            action_plan = (
                f"Greedy combined Action Plan across {names} to achieve +{required_increase_tpa:,} tpa.\n"
                f"Combined ROI estimated: {combined_roi} months.\n"
                "Coordinate energy and port reservations accordingly and run pilots."
            )
            return {
                "recommended_plant": names,
                "expected_increase_tpa": required_increase_tpa,
                "investment_usd": sum(s.get("capex_estimate_usd", 0) for s in selected),
                "roi_months": combined_roi,
                "energy_required_mw": total_energy,
                "summary": "Greedy combined candidate meets target under combined ROI constraint.",
                "action_plan": action_plan,
                "justification": {
                    "energy_headroom_mw": energy_headroom_mw,
                    "port_headroom_tpa": port_headroom_tpa,
                    "expected_increase_tpa": required_increase_tpa,
                    "breaches": [],
                    "mitigations": [],
                    "distribution_strategy": "greedy_selection"
                },
                "explainability": {
                    "steel_em": [s.get("explainability", {}) for s in selected],
                    "ports_em": ports_info.get("explainability", {}),
                    "energy_em": energy_info.get("explainability", {})
                },
                "allocations": allocations,
                "why_chosen": [
                    "Combined plants were selected to reach the target while meeting combined ROI.",
                    "Greedy selection prioritized plants with highest feasible uplift."
                ]
            }

    # Final fallback: best-effort top plants (report breaches + mitigations)
    top = sorted_candidates[0]
    breaches = []
    mitigations = []
    if top["feasible_increase_tpa"] < required_increase_tpa:
        breaches.append("insufficient_single_plant_increase")
        mitigations.append("combine multiple plants or extend timeline")
    if top["energy_required_mw"] > energy_headroom_mw:
        breaches.append("energy_shortfall")
        mitigations.append("phase energy allocation; procure temporary energy")
    if top["feasible_increase_tpa"] > port_headroom_tpa:
        breaches.append("port_shortfall")
        mitigations.append("stagger shipments; temporary staging")

    action_plan = (
        f"Top candidate (soft): {top['plant_id']} yields {top['feasible_increase_tpa']:,} tpa uplift. "
        f"Mitigations: {', '.join(mitigations)}. Pilot and re-evaluate."
    )

    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_tpa": top["feasible_increase_tpa"],
        "investment_usd": top["capex_estimate_usd"],
        "roi_months": top["roi_months"],
        "energy_required_mw": top["energy_required_mw"],
        "summary": "Best-effort candidate selected; does not meet all constraints.",
        "action_plan": action_plan,
        "justification": {
            "breaches": breaches,
            "mitigations": mitigations,
            "energy_headroom_mw": energy_headroom_mw,
            "port_headroom_tpa": port_headroom_tpa,
            "distribution_strategy": "best_effort_fallback"
        },
        "explainability": {
            "steel_em": top.get("explainability", {}),
            "ports_em": ports_info.get("explainability", {}),
            "energy_em": energy_info.get("explainability", {})
        }
    }
