# group_manager.py
from typing import Dict, Any, List
import itertools

def _combined_roi_months_total(capex_total: float, total_monthly_income: float) -> float:
    if total_monthly_income <= 0:
        return float("inf")
    return round(capex_total / total_monthly_income, 2)

def _allocate_required_with_expansion(combo: List[Dict[str, Any]], required: int) -> List[Dict[str, Any]]:
    """
    Allocate required tpa across combo plants using both operational feasible and expansion if needed.
    Strategy:
      - First use each plant's feasible_increase_tpa (operational uplift).
      - If still short, allocate expansion across plants ordered by cheapest expansion_cost_per_tpa_usd.
    Returns list with per-plant:
      plant_id, allocated_tpa, allocated_operational_tpa, allocated_expansion_tpa, op_capex, expansion_capex
    """
    # start with operational allocations (use all feasible first)
    allocations = []
    remaining = required
    for c in combo:
        op = min(c["feasible_increase_tpa"], remaining)
        allocations.append({
            "plant_id": c["plant_id"],
            "allocated_operational_tpa": op,
            "allocated_expansion_tpa": 0,
            "feasible_tpa": c["feasible_increase_tpa"],
            "op_capex": c.get("op_capex_estimate_usd", 0),
            "expansion_cost_per_tpa_usd": c.get("expansion_cost_per_tpa_usd", 3000),
            "capex_estimate_usd": c.get("capex_estimate_usd", 0),
            "incr_monthly_income": c.get("incr_monthly_income", 0)
        })
        remaining -= op

    if remaining <= 0:
        # no expansion needed
        for a in allocations:
            a["allocated_tpa"] = a["allocated_operational_tpa"]
            a["expansion_capex"] = 0
            a["op_capex_used"] = a["op_capex"] if a["allocated_operational_tpa"]>0 else 0
        return allocations

    # need expansion: sort allocations by expansion cost per tpa (cheapest first)
    sorted_alloc_idx = sorted(range(len(allocations)), key=lambda i: allocations[i]["expansion_cost_per_tpa_usd"])
    # allocate expansion tonnage one-by-one (simple) — but we can allocate proportionally instead
    for idx in sorted_alloc_idx:
        if remaining <= 0:
            break
        # allow expansion up to some practical limit per plant — for prototype allow up to 50% of capacity as expansion
        # we need capacity info - derive from feasible proportion: use feasible_tpa as base; allow additional up to double feasible for prototype
        # Simpler: allow unlimited for prototype but compute expansion capex accordingly
        add = remaining  # allocate all to cheapest first (fast), alternatively distribute
        allocations[idx]["allocated_expansion_tpa"] += add
        remaining -= add

    # compute capex used
    for a in allocations:
        a["allocated_tpa"] = a["allocated_operational_tpa"] + a["allocated_expansion_tpa"]
        a["expansion_capex"] = int(round(a["allocated_expansion_tpa"] * a["expansion_cost_per_tpa_usd"]))
        # op capex used proportional to op allocated (simple heuristic)
        a["op_capex_used"] = a["op_capex"] if a["allocated_operational_tpa"]>0 else 0

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

    # Step 1: try combos using only operational feasible (no expansion)
    for r in range(1, n + 1):
        for combo in itertools.combinations(steel_candidates, r):
            total_op = sum(c["feasible_increase_tpa"] for c in combo)
            total_energy = sum(c["energy_required_mw"] for c in combo)
            if total_op >= required_increase_tpa and total_energy <= energy_headroom_mw and total_op <= port_headroom_tpa:
                # compute combined op capex and monthly income
                total_op_capex = sum(c.get("op_capex_estimate_usd", 0) for c in combo)
                total_monthly = sum(c.get("incr_monthly_income", 0) for c in combo)
                combined_roi = _combined_roi_months_total(total_op_capex, total_monthly)
                if combined_roi <= max_roi_months:
                    # allocate operational only
                    allocations = _allocate_required_with_expansion(combo, required_increase_tpa)
                    names = ", ".join([c["plant_id"] for c in combo])
                    action_plan = f"Use operational uplifts across {names} to meet target. Monitor and scale."
                    return {
                        "recommended_plant": names,
                        "expected_increase_tpa": required_increase_tpa,
                        "investment_usd": total_op_capex,
                        "roi_months": combined_roi,
                        "energy_required_mw": sum(c["energy_required_mw"] for c in combo),
                        "summary": "Operational uplift across selected plants meets the target.",
                        "action_plan": action_plan,
                        "justification": {"energy_headroom_mw": energy_headroom_mw, "port_headroom_tpa": port_headroom_tpa, "breaches": []},
                        "explainability": {"steel_em": [c.get("explainability", {}) for c in combo]},
                        "allocations": allocations,
                        "why_chosen": ["Operational uplift suffices; combined ROI within constraint."]
                    }

    # Step 2: try combos allowing expansion capex (we will compute required expansion and its capex)
    for r in range(1, n + 1):
        for combo in itertools.combinations(steel_candidates, r):
            total_op = sum(c["feasible_increase_tpa"] for c in combo)
            total_energy_op = sum(c["energy_required_mw"] for c in combo)
            # if operational already covers, we skipped earlier; here total_op < required
            # compute remaining needed beyond op
            remaining_needed = max(0, required_increase_tpa - total_op)
            # approximate extra energy per tpa for expansion: use average energy_required_mw per op tonne ratio
            if total_op > 0:
                energy_per_tpa = total_energy_op / total_op
            else:
                # fallback small ratio
                energy_per_tpa = 0.00001
            extra_energy_needed = remaining_needed * energy_per_tpa
            if (total_energy_op + extra_energy_needed) > energy_headroom_mw:
                # cannot supply energy even with expansion
                continue
            # compute expansion capex: distribute remaining_needed to plants by cheapest expansion_cost_per_tpa_usd
            # simple: allocate all remaining to cheapest plant(s) in combo
            combo_sorted = sorted(combo, key=lambda c: c.get("expansion_cost_per_tpa_usd", 3000))
            # compute total expansion capex
            expansion_capex_total = 0
            remaining = remaining_needed
            for c in combo_sorted:
                take = remaining  # for prototype, allocate to cheapest primarily
                cost_per = c.get("expansion_cost_per_tpa_usd", 3000)
                expansion_capex_total += take * cost_per
                remaining -= take
                if remaining <= 0:
                    break
            # op capex
            op_capex_total = sum(c.get("op_capex_estimate_usd", 0) for c in combo)
            total_capex = int(round(op_capex_total + expansion_capex_total))
            total_monthly_income = sum(c.get("incr_monthly_income", 0) for c in combo)
            # If we expand, assume incremental monthly income scales with allocated tonnage; for simplicity scale pro-rata:
            if total_op > 0:
                scale_factor = required_increase_tpa / max(1, total_op)
            else:
                scale_factor = 1 + (remaining_needed / (sum(c.get("capacity_tpa",1) for c in combo)))
            combined_monthly_income = total_monthly_income * scale_factor
            combined_roi = _combined_roi_months_total(total_capex, combined_monthly_income)
            if combined_roi <= max_roi_months and required_increase_tpa <= port_headroom_tpa:
                allocations = _allocate_required_with_expansion(combo, required_increase_tpa)
                names = ", ".join([c["plant_id"] for c in combo])
                action_plan = (
                    f"Combined operational + expansion plan across {names} to achieve +{required_increase_tpa:,} tpa.\n"
                    "Allocate expansion capex and secure energy & port reservations. Pilot and validate."
                )
                return {
                    "recommended_plant": names,
                    "expected_increase_tpa": required_increase_tpa,
                    "investment_usd": total_capex,
                    "roi_months": combined_roi,
                    "energy_required_mw": total_energy_op + extra_energy_needed,
                    "summary": "Combined operational uplift + planned expansion meets the target within ROI.",
                    "action_plan": action_plan,
                    "justification": {"energy_headroom_mw": energy_headroom_mw, "port_headroom_tpa": port_headroom_tpa, "breaches": []},
                    "explainability": {"steel_em": [c.get("explainability", {}) for c in combo]},
                    "allocations": allocations,
                    "why_chosen": [
                        "Operational uplift + targeted expansion delivers required capacity.",
                        "Expansion capex allocated to lowest $/tpa plant(s).",
                        "Combined ROI meets recovery constraint."
                    ]
                }

    # Final fallback: best-effort greedy (same as earlier)
    sorted_candidates = sorted(steel_candidates, key=lambda x: -x["feasible_increase_tpa"])
    selected = []
    total_inc = 0
    total_energy = 0
    for c in sorted_candidates:
        selected.append(c)
        total_inc += c["feasible_increase_tpa"]
        total_energy += c["energy_required_mw"]
        if total_inc >= required_increase_tpa:
            break

    # if still not enough, return best candidate with mitigations
    top = sorted_candidates[0]
    breaches = []
    mitigations = []
    if top["feasible_increase_tpa"] < required_increase_tpa:
        breaches.append("insufficient_single_plant_increase")
        mitigations.append("combine multiple plants or plan expansion investments")
    if top["energy_required_mw"] > energy_headroom_mw:
        breaches.append("energy_shortfall")
        mitigations.append("phase energy allocation; procure temporary energy")
    if required_increase_tpa > port_headroom_tpa:
        breaches.append("port_shortfall")
        mitigations.append("stagger shipments; temporary staging")

    action_plan = f"Top candidate (soft): {top['plant_id']} yields {top['feasible_increase_tpa']:,} tpa uplift. Mitigations: {', '.join(mitigations)}."

    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_tpa": top["feasible_increase_tpa"],
        "investment_usd": top["capex_estimate_usd"],
        "roi_months": top.get("roi_months"),
        "energy_required_mw": top.get("energy_required_mw"),
        "summary": "Best-effort candidate selected; does not meet all constraints.",
        "action_plan": action_plan,
        "justification": {"breaches": breaches, "mitigations": mitigations, "energy_headroom_mw": energy_headroom_mw, "port_headroom_tpa": port_headroom_tpa},
        "explainability": {"steel_em": top.get("explainability", {})}
    }
