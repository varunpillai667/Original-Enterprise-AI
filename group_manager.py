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

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           group_systems: Dict[str, Any],
                           required_increase_tpa: int = 2_000_000,
                           max_roi_months: int = 36) -> Dict[str, Any]:
    if not steel_candidates:
        raise RuntimeError("No steel candidates provided to Group Manager.")

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
                        "mitigations": []
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
    sorted_candidates = sorted(steel_candidates, key=lambda x: -x["feasible_increase_tpa"])
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
                    "mitigations": []
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
            "port_headroom_tpa": port_headroom_tpa
        },
        "explainability": {
            "steel_em": top.get("explainability", {}),
            "ports_em": ports_info.get("explainability", {}),
            "energy_em": energy_info.get("explainability", {})
        }
    }
