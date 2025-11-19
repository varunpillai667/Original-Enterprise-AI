# group_manager.py
"""
Group-level orchestrator: picks candidate(s) satisfying query constraints:
- required increase in tpa
- ROI must be under max_roi_months
- Energy and port headroom checks
Produces action_plan and explainability.
"""

from typing import Dict, Any, List

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           group_systems: Dict[str, Any],
                           required_increase_tpa: int = 2_000_000,
                           max_roi_months: int = 9) -> Dict[str, Any]:
    # quick checks
    if not steel_candidates:
        raise RuntimeError("No steel candidates provided to Group Manager.")

    energy_headroom = energy_info.get("energy_headroom_mw", 0)
    port_headroom = ports_info.get("port_headroom_units", 0)

    # first, find candidates that individually meet the required increase and ROI
    for c in steel_candidates:
        if c["feasible_increase_tpa"] >= required_increase_tpa and c["roi_months"] <= max_roi_months:
            # also ensure energy and port headroom
            if c["energy_required_mw"] <= energy_headroom and c["estimated_increase_units"] <= port_headroom:
                action_plan = (
                    f"Action Plan for {c['plant_id']} to achieve +{c['feasible_increase_tpa']} tpa:\n"
                    f"1) Ramp operations to target uplift (pilot 2 weeks). Assign Ops lead to implement shifts.\n"
                    f"2) Allocate {c['energy_required_mw']} MW from Energy (confirm dispatch daily).\n"
                    f"3) Confirm port slots for {c['estimated_increase_units']} additional shipments and stage inventory accordingly.\n"
                    f"4) Perform QA checks during pilot; roll out on successful metrics.\n"
                    f"Note: Investment expected to be recovered in {c['roi_months']} months per EM estimate."
                )
                return {
                    "recommended_plant": c["plant_id"],
                    "expected_increase_tpa": c["feasible_increase_tpa"],
                    "investment_usd": c["capex_estimate_usd"],
                    "roi_months": c["roi_months"],
                    "energy_required_mw": c["energy_required_mw"],
                    "summary": f"Candidate {c['plant_id']} satisfies target increase and ROI constraint.",
                    "action_plan": action_plan,
                    "justification": {"energy_headroom_mw": energy_headroom, "port_headroom_units": port_headroom},
                    "explainability": {
                        "steel_em": c.get("explainability", {}),
                        "ports_em": ports_info.get("explainability", {}),
                        "energy_em": energy_info.get("explainability", {})
                    }
                }

    # if no single candidate meets both target + ROI, try combinations (simple greedy sum)
    total = 0
    selected = []
    for c in steel_candidates:
        if c["roi_months"] <= max_roi_months:
            # check resource feasibility before adding
            if c["energy_required_mw"] <= energy_headroom and c["estimated_increase_units"] <= port_headroom:
                selected.append(c)
                total += c["feasible_increase_tpa"]
                # subtract headroom conservatively
                energy_headroom -= c["energy_required_mw"]
                port_headroom -= c["estimated_increase_units"]
                if total >= required_increase_tpa:
                    break

    if total >= required_increase_tpa:
        # group recommendation as combined rollout
        names = ", ".join([s["plant_id"] for s in selected])
        action_plan = (
            f"Combined Action Plan across {names} to achieve +{total} tpa:\n"
            f"1) Run staged pilots at each plant (per-plant Ops lead). Start smallest pilot first to confirm learnings.\n"
            f"2) Coordinate energy allocation and staggered shipping windows to match port headroom.\n"
            f"3) Reconcile combined investment and expected recovery across the selected plants (per-plant ROI <= {max_roi_months} months).\n"
            f"Timeline: phased rollout over 4-12 weeks depending on coordination."
        )
        return {
            "recommended_plant": names,
            "expected_increase_tpa": total,
            "investment_usd": sum(s["capex_estimate_usd"] for s in selected),
            "roi_months": min(s["roi_months"] for s in selected),
            "energy_required_mw": sum(s["energy_required_mw"] for s in selected),
            "summary": "Combined candidate set meets target under ROI constraint.",
            "action_plan": action_plan,
            "justification": {"energy_headroom_mw": energy_info.get("energy_headroom_mw"), "port_headroom_units": ports_info.get("port_headroom_units")},
            "explainability": {
                "steel_em": [s.get("explainability", {}) for s in selected],
                "ports_em": ports_info.get("explainability", {}),
                "energy_em": energy_info.get("explainability", {})
            }
        }

    # fallback: show best single candidate (highest feasible increase) and be explicit about breaches & mitigations
    top = steel_candidates[0]
    breaches = []
    if top["feasible_increase_tpa"] < required_increase_tpa:
        breaches.append("insufficient_single_plant_increase")
    if top["roi_months"] > max_roi_months:
        breaches.append("roi_exceeds_limit")
    if top["energy_required_mw"] > energy_info.get("energy_headroom_mw", 0):
        breaches.append("energy_shortfall")
    if top["estimated_increase_units"] > ports_info.get("port_headroom_units", 0):
        breaches.append("port_shortfall")

    mitigations = []
    if "energy_shortfall" in breaches:
        mitigations.append("phase energy allocation; schedule off-peak windows; consider temporary purchase")
    if "port_shortfall" in breaches:
        mitigations.append("stagger shipments; use temporary staging; request additional port slots")
    if "roi_exceeds_limit" in breaches:
        mitigations.append("consider lower-capex operational options or phased rollout to improve ROI")

    action_plan = (
        f"Recommended top candidate (soft): {top['plant_id']} with feasible uplift {top['feasible_increase_tpa']} tpa.\n"
        f"Mitigations: {', '.join(mitigations) if mitigations else 'none'}. Pilot 2-4 weeks and re-evaluate."
    )

    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_tpa": top["feasible_increase_tpa"],
        "investment_usd": top["capex_estimate_usd"],
        "roi_months": top["roi_months"],
        "energy_required_mw": top["energy_required_mw"],
        "summary": "Top candidate selected but requires mitigations; see action_plan.",
        "action_plan": action_plan,
        "justification": {"breaches": breaches, "mitigations": mitigations},
        "explainability": {
            "steel_em": top.get("explainability", {}),
            "ports_em": ports_info.get("explainability", {}),
            "energy_em": energy_info.get("explainability", {})
        }
    }
