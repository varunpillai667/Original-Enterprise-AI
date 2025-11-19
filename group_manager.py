"""
group_manager.py

Group Manager orchestration across EM outputs and group-level systems.
Selects candidate that satisfies energy & port headroom and CapEx if provided.
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
            return {
                "recommended_plant": c["plant_id"],
                "expected_increase_pct": f"+{c['feasible_increase_pct']}%",
                "investment_usd": c["capex_estimate_usd"],
                "roi_period_months": c["roi_months"],
                "energy_required_mw": c["energy_required_mw"],
                "summary": f"Select {c['plant_id']} expansion — passes cross-EM checks.",
                "justification": rationale,
                "explainability": {
                    "steel_em": c.get("explainability", {}),
                    "ports_em": ports_info.get("explainability", {}),
                    "energy_em": energy_info.get("explainability", {})
                }
            }

    # No candidate passed strict constraints — return top candidate with suggested mitigations
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

    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_pct": f"+{top['feasible_increase_pct']}% (soft)",
        "investment_usd": top["capex_estimate_usd"],
        "roi_period_months": top["roi_months"],
        "energy_required_mw": top["energy_required_mw"],
        "summary": f"Top candidate {top['plant_id']} requires mitigations: {', '.join(mitigations)}",
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
