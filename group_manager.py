"""
Group Manager:
Applies cross-enterprise constraints:
- energy system
- port capacity
Selects the best EM candidate while respecting optional CapEx limits.
"""
from typing import Dict, Any, List

def orchestrate(em_candidates: List[Dict[str, Any]], data: Dict[str, Any], capex_limit_usd: float = None):
    energy_available = data["energy"]["available_mw"]
    port_capacity = data["ports"]["port2_capacity"]
    port_util = data["ports"]["current_utilization"]

    # Conservative headroom in units (based on port capacity and utilization)
    port_headroom = max(0.0, (1.0 - port_util)) * port_capacity

    # Iterate candidates in order (EM should provide them sorted by score)
    for c in em_candidates:
        # Respect capex limit if provided
        if capex_limit_usd is not None and c["capex_estimate_usd"] > capex_limit_usd:
            continue

        # Check energy and port headroom constraints
        if c["energy_required_mw"] <= energy_available and c["estimated_increase_units"] <= port_headroom:
            return {
                "recommended_plant": c["plant_id"],
                "expected_increase_pct": f"+{c['feasible_increase_pct']}%",
                "investment_usd": c["capex_estimate_usd"],
                "roi_period_months": c["roi_months"],
                "energy_required_mw": c["energy_required_mw"],
                "summary": f"Expand {c['plant_id']} by {c['feasible_increase_pct']}% using {c['energy_required_mw']} MW.",
                "justification": {
                    "why": "Meets energy & port constraints",
                    "energy_available_mw": energy_available,
                    "energy_required_mw": c["energy_required_mw"],
                    "port_headroom_units": port_headroom,
                    "estimated_increase_units": c["estimated_increase_units"]
                },
                "explainability": c.get("explainability", {})
            }

    # If no candidate satisfies strict constraints, return top candidate with a note
    if not em_candidates:
        raise RuntimeError("No EM candidates provided to Group Manager.")

    top = em_candidates[0]
    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_pct": f"+{top['feasible_increase_pct']}% (soft)",
        "investment_usd": top["capex_estimate_usd"],
        "roi_period_months": top["roi_months"],
        "energy_required_mw": top["energy_required_mw"],
        "summary": f"Top candidate {top['plant_id']} selected but constraints exceeded.",
        "justification": {
            "why": "No candidate satisfied strict constraints",
            "energy_available_mw": energy_available,
            "energy_required_mw": top["energy_required_mw"],
            "port_headroom_units": port_headroom,
            "estimated_increase_units": top["estimated_increase_units"]
        },
        "explainability": top.get("explainability", {})
    }
