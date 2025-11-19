"""
group_manager.py

Group Manager orchestration across EM outputs and group-level systems.
Selects candidate that satisfies energy & port headroom and CapEx if provided.
Provides an action_plan string with concrete next steps for the recommended plant.
"""
from typing import Dict, Any, List

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           group_systems: Dict[str, Any],
                           capex_limit_usd: float = None) -> Dict[str, Any]:
    energy_headroom = energy_info.get("energy_headroom_mw", 0.0)
    port_headroom = ports_info.get("port_headroom_units", 0.0)

    if not steel_candidates:
        raise RuntimeError("No steel candidates provided to Group Manager.")

    for c in steel_candidates:
        if capex_limit_usd is not None and c["capex_estimate_usd"] > capex_limit_usd:
            continue
        energy_ok = c["energy_required_mw"] <= energy_headroom
        port_ok = c["estimated_increase_units"] <= port_headroom
        if energy_ok and port_ok:
            rationale = {
                "why": "Meets energy and port headroom constraints and aligns with group signals",
                "commodity_price_index": group_systems.get("commodity_index"),
                "energy_headroom_mw": energy_headroom,
                "port_headroom_units": port_headroom
            }

            # Build an explicit, actionable plan — no CapEx talk here
            action_plan = (
                f"Action Plan to increase production at {c['plant_id']} by {c['feasible_increase_pct']}%:\n\n"
                f"1) Operational uplift — Ramp furnace/line throughput to target (≈{c['feasible_increase_pct']}%). "
                f"Assign Production Lead to implement schedule changes and short-term process tuning (2–4 weeks).\n\n"
                f"2) Energy allocation — Secure incremental energy allocation of {c['energy_required_mw']} MW from Energy team "
                f"(coordinate with Energy dispatch; prioritize off-peak window where possible).\n\n"
                f"3) Logistics coordination — Confirm port capacity for the estimated increase ({c['estimated_increase_units']} units). "
                f"Schedule staggered shipments and temporary yard staging to avoid congestion (Operations & Logistics).\n\n"
                f"4) Quality & maintenance checks — Perform targeted maintenance and QA checks to sustain throughput (Maintenance & QA). "
                f"Plan a one-week pilot ramp then full rollout after validation.\n\n"
                f"5) Timeline & owner — Pilot within 2–4 weeks; Operations Lead to report daily metrics during pilot and sign-off for full rollout.\n"
            )

            return {
                "recommended_plant": c["plant_id"],
                "expected_increase_pct": f"+{c['feasible_increase_pct']}%",
                "investment_usd": c["capex_estimate_usd"],
                "roi_period_months": c["roi_months"],
                "energy_required_mw": c["energy_required_mw"],
                "summary": f"Select {c['plant_id']} expansion — passes cross-EM checks.",
                "action_plan": action_plan,
                "justification": rationale,
                "explainability": {
                    "steel_em": c.get("explainability", {}),
                    "ports_em": ports_info.get("explainability", {}),
                    "energy_em": energy_info.get("explainability", {})
                }
            }

    # No candidate passed strict constraints — return top candidate with suggested mitigations and action plan
    top = steel_candidates[0]
    breaches = {
        "energy_required_mw": top["energy_required_mw"],
        "energy_headroom_mw": energy_headroom,
        "estimated_increase_units": top["estimated_increase_units"],
        "port_headroom_units": port_headroom,
        "capex_exceeded": capex_limit_usd is not None and top["capex_estimate_usd"] > capex_limit_usd
    }
    mitigations = []
    if breaches["energy_required_mw"] > breaches["energy_headroom_mw"]:
        mitigations.append("increase energy supply or phase rollout")
    if breaches["estimated_increase_units"] > breaches["port_headroom_units"]:
        mitigations.append("stagger shipments or increase port throughput")
    if breaches["capex_exceeded"]:
        mitigations.append("raise CapEx budget or choose lower-capex option")

    # Build an action plan that focuses on operational steps and mitigations (no CapEx centric phrasing)
    action_plan_soft = (
        f"Action Plan (soft recommendation) for {top['plant_id']}:\n\n"
        f"1) Pilot a phased rollout for the proposed increase ({top['feasible_increase_pct']}%) to reduce simultaneous demand spikes.\n\n"
        f"2) Coordinate with Energy team to schedule required {top['energy_required_mw']} MW in phases; consider off-peak windows.\n\n"
        f"3) Logistics mitigation — stagger shipments and use temporary staging to manage port headroom constraints.\n\n"
        f"4) Execute maintenance & QA readiness before each phase; measure production and quality metrics closely.\n\n"
        f"5) Timeline: pilot 2–4 weeks, then incremental ramp contingent on energy & port confirmations."
    )

    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_pct": f"+{top['feasible_increase_pct']}% (soft)",
        "investment_usd": top["capex_estimate_usd"],
        "roi_period_months": top["roi_months"],
        "energy_required_mw": top["energy_required_mw"],
        "summary": f"Top candidate {top['plant_id']} requires mitigations: {', '.join(mitigations)}",
        "action_plan": action_plan_soft,
        "justification": {
            "why": "Breaches group constraints; mitigations proposed",
            "breaches": breaches,
            "mitigations": mitigations
        },
        "explainability": {
            "steel_em": top.get("explainability", {}),
            "ports_em": ports_info.get("explainability", {}),
            "energy_em": energy_info.get("explainability", {})
        }
    }
