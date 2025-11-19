# group_manager.py
"""
Group-level orchestrator: finds a combination of steel plants (and checks energy & port capacity)
that meets the required increase in tpa while respecting ROI limit. Returns actionable plan.
"""

from typing import Dict, Any, List
import itertools

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           group_systems: Dict[str, Any],
                           required_increase_tpa: int = 2_000_000,
                           max_roi_months: int = 9) -> Dict[str, Any]:
    # sanity
    if not steel_candidates:
        raise RuntimeError("No steel candidates provided to Group Manager.")

    port_headroom_tpa = ports_info.get("port_headroom_tpa", 0)
    energy_headroom_mw = energy_info.get("energy_headroom_mw", 0)

    # Try to find any combination (1..N) of steel candidates that together meet required_increase_tpa
    # and whose per-plant ROI <= max_roi_months, and whose total energy & port usage <= headroom.
    n = len(steel_candidates)
    # limit combination size to avoid combinatorial explosion in prototype; allow up to all plants
    best_solution = None

    # Try combinations by increasing size (prefer small sets)
    for r in range(1, n + 1):
        # iterate combinations of r plants
        for combo in itertools.combinations(steel_candidates, r):
            total_increase = sum(c["feasible_increase_tpa"] for c in combo)
            # require per-plant ROI <= max_roi_months (user specified that investment must be recovered <9 months)
            if any(c["roi_months"] > max_roi_months for c in combo):
                continue
            total_energy_req = sum(c["energy_required_mw"] for c in combo)
            total_shipment_units = sum(c["feasible_increase_tpa"] for c in combo)  # shipments proportional to tonnes
            # check resource constraints
            if total_increase >= required_increase_tpa and total_energy_req <= energy_headroom_mw and total_shipment_units <= port_headroom_tpa:
                # Found a valid solution
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
                    "roi_months": min(c.get("roi_months") for c in combo),
                    "energy_required_mw": total_energy_req,
                    "summary": "Combined candidate set meets target under ROI and resource constraints.",
                    "action_plan": action_plan,
                    "justification": {
                        "energy_headroom_mw": energy_headroom_mw,
                        "port_headroom_tpa": port_headroom_tpa,
                        "breaches": [],
                        "mitigations": []
                    },
                    "explainability": {
                        "steel_em": [c.get("explainability", {}) for c in combo],
                        "ports_em": ports_info.get("explainability", {}),
                        "energy_em": energy_info.get("explainability", {})
                    }
                }

    # If no valid combination found that meets all constraints, attempt best-effort solution:
    # Greedy select plants by feasible increase (desc) but only include those with ROI <= max_roi_months
    remaining_energy = energy_headroom_mw
    remaining_port = port_headroom_tpa
    selected = []
    total = 0
    for c in steel_candidates:
        if c["roi_months"] > max_roi_months:
            continue
        if c["energy_required_mw"] <= remaining_energy and c["feasible_increase_tpa"] <= remaining_port:
            selected.append(c)
            total += c["feasible_increase_tpa"]
            remaining_energy -= c["energy_required_mw"]
            remaining_port -= c["feasible_increase_tpa"]
        if total >= required_increase_tpa:
            break

    if total >= required_increase_tpa:
        names = ", ".join([s["plant_id"] for s in selected])
        action_plan = (
            f"Combined (greedy) plan across {names} to achieve +{total} tpa. Energy allocation and port reservation assigned accordingly."
        )
        return {
            "recommended_plant": names,
            "expected_increase_tpa": total,
            "investment_usd": sum(s.get("capex_estimate_usd", 0) for s in selected),
            "roi_months": min(s.get("roi_months") for s in selected),
            "energy_required_mw": sum(s.get("energy_required_mw", 0) for s in selected),
            "summary": "Greedy combined candidate meets target under ROI & resource checks.",
            "action_plan": action_plan,
            "justification": {
                "energy_headroom_mw": energy_headroom_mw,
                "port_headroom_tpa": port_headroom_tpa,
                "breaches": [],
                "mitigations": []
            },
            "explainability": {
                "steel_em": [s.get("explainability", {}) for s in selected],
                "ports_em": ports_info.get("explainability", {}),
                "energy_em": energy_info.get("explainability", {})
            }
        }

    # Final fallback: return best single candidate with clear mitigations and explicit breaches
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
