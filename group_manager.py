# group_manager.py
"""
Group-level orchestrator: finds a combination of steel plants (and checks energy & port capacity)
that meets the required increase in tpa while ensuring the combined ROI meets the constraint.
"""

from typing import Dict, Any, List
import itertools

def _combined_roi_months(combo: List[Dict[str, Any]]) -> float:
    """
    Compute combined ROI in months for the provided combo.
    combined_roi_months = total_capex / total_incremental_monthly_income
    If incremental monthly income is zero, return a very large number.
    """
    total_capex = sum(c.get("capex_estimate_usd", 0) for c in combo)
    total_monthly_income = sum(c.get("incr_monthly_income", 0) for c in combo)
    if total_monthly_income <= 0:
        return float("inf")
    return round(total_capex / total_monthly_income, 2)

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           group_systems: Dict[str, Any],
                           required_increase_tpa: int = 2_000_000,
                           max_roi_months: int = 9) -> Dict[str, Any]:
    if not steel_candidates:
        raise RuntimeError("No steel candidates provided to Group Manager.")

    port_headroom_tpa = ports_info.get("port_headroom_tpa", 0)
    energy_headroom_mw = energy_info.get("energy_headroom_mw", 0)

    n = len(steel_candidates)

    # Try combinations of plants (1..N). Prefer smaller combos first.
    for r in range(1, n + 1):
        for combo in itertools.combinations(steel_candidates, r):
            total_increase = sum(c["feasible_increase_tpa"] for c in combo)
            total_energy_req = sum(c["energy_required_mw"] for c in combo)
            total_shipment_units = sum(c["feasible_increase_tpa"] for c in combo)
            combined_roi = _combined_roi_months(combo)

            # check resource constraints and combined ROI
            if total_increase >= required_increase_tpa and total_energy_req <= energy_headroom_mw and total_shipment_units <= port_headroom_tpa and combined_roi <= max_roi_months:
                names = ", ".join([c["plant_id"] for c in combo])
                action_plan = (
                    f"Combined Action Plan across {names} to achieve +{total_increase} tpa:\n"
                    "1) Run coordinated pilots at each selected plant to validate process changes and rate scaling.\n"
                    f"2) Allocate energy dispatch totaling {total_energy_req} MW from available generation.\n"
                    f"3) Reserve port throughput for {total_shipment_units:,} tpa (approx {total_shipment_units/1_000_000:.2f} Mtpa) and stagger shipments.\n"
                    "4) Monitor KPIs weekly and scale rollout on success."
                )
                return {
                    "recommended_plant": names,
                    "expected_increase_tpa": total_increase,
                    "investment_usd": sum(c.get("capex_estimate_usd", 0) for c in combo),
                    "roi_months": combined_roi,
                    "energy_required_mw": total_energy_req,
                    "summary": "Combined candidate set meets target under combined ROI and resource constraints.",
                    "action_plan": action_plan,
                    "justification": {
                        "energy_headroom_mw": energy_headroom_mw,
                        "port_headroom_tpa": port_headroom_tpa,
                        "expected_increase_tpa": total_increase,
                        "breaches": [],
                        "mitigations": []
                    },
                    "explainability": {
                        "steel_em": [c.get("explainability", {}) for c in combo],
                        "ports_em": ports_info.get("explainability", {}),
                        "energy_em": energy_info.get("explainability", {})
                    }
                }

    # No perfect combination found: attempt greedy combination allowing combos where combined ROI <= max even if some individuals exceed max
    # Greedy by feasible_increase desc but evaluate combined ROI at each addition
    sorted_candidates = sorted(steel_candidates, key=lambda x: -x["feasible_increase_tpa"])
    selected = []
    total_inc = 0
    total_energy = 0
    total_shipments = 0
    for c in sorted_candidates:
        selected.append(c)
        total_inc += c["feasible_increase_tpa"]
        total_energy += c["energy_required_mw"]
        total_shipments += c["feasible_increase_tpa"]
        combined_roi = _combined_roi_months(selected)
        if total_inc >= required_increase_tpa and total_energy <= energy_headroom_mw and total_shipments <= port_headroom_tpa and combined_roi <= max_roi_months:
            names = ", ".join([s["plant_id"] for s in selected])
            action_plan = (
                f"Greedy combined Action Plan across {names} to achieve +{total_inc} tpa:\n"
                f"Combined ROI estimated: {combined_roi} months.\n"
                "Coordinate energy and port reservations accordingly and run pilots."
            )
            return {
                "recommended_plant": names,
                "expected_increase_tpa": total_inc,
                "investment_usd": sum(s.get("capex_estimate_usd", 0) for s in selected),
                "roi_months": combined_roi,
                "energy_required_mw": total_energy,
                "summary": "Greedy combined candidate meets target and combined ROI constraint.",
                "action_plan": action_plan,
                "justification": {
                    "energy_headroom_mw": energy_headroom_mw,
                    "port_headroom_tpa": port_headroom_tpa,
                    "expected_increase_tpa": total_inc,
                    "breaches": [],
                    "mitigations": []
                },
                "explainability": {
                    "steel_em": [s.get("explainability", {}) for s in selected],
                    "ports_em": ports_info.get("explainability", {}),
                    "energy_em": energy_info.get("explainability", {})
                }
            }

    # Final fallback: best single candidate with clear mitigation recommendations
    top = steel_candidates[0]
    breaches = []
    if top["feasible_increase_tpa"] < required_increase_tpa:
        breaches.append("insufficient_single_plant_increase")
    if top["roi_months"] > max_roi_months:
        breaches.append("roi_exceeds_limit")
    if top["energy_required_mw"] > energy_headroom_mw:
        breaches.append("energy_shortfall")
    if top["feasible_increase_tpa"] > port_headroom_tpa:
        breaches.append("port_shortfall")

    mitigations = []
    if "energy_shortfall" in breaches:
        mitigations.append("phase energy allocation; schedule off-peak windows; consider temporary purchase")
    if "port_shortfall" in breaches:
        mitigations.append("stagger shipments; use temporary staging; request additional port slots")
    if "roi_exceeds_limit" in breaches:
        mitigations.append("consider lower-capex operational options or phased rollout to improve ROI")
    if "insufficient_single_plant_increase" in breaches:
        mitigations.append("combine multiple plants (cross-company rollout) or extend timeline beyond immediate target")

    action_plan = (
        f"Recommended top candidate (soft): {top['plant_id']} with feasible uplift {top['feasible_increase_tpa']} tpa.\n"
        f"Mitigations: {', '.join(mitigations) if mitigations else 'none'}. Pilot and re-evaluate."
    )

    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_tpa": top["feasible_increase_tpa"],
        "investment_usd": top["capex_estimate_usd"],
        "roi_months": top["roi_months"],
        "energy_required_mw": top["energy_required_mw"],
        "summary": "Top candidate selected but requires mitigations; see action_plan.",
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
