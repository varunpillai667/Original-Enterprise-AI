"""
group_manager.py
Implements Group Manager orchestration logic:
- Accepts enterprise-level candidate evaluations
- Applies cross-enterprise constraints (energy availability, port capacity)
- Produces final recommendation and high-level reasoning
"""
from typing import Dict, Any, List, Tuple

def orchestrate(em_candidates: List[Dict[str, Any]], data: Dict[str, Any], capex_limit_usd: float = None) -> Dict[str, Any]:
    """
    Select the best candidate considering energy and port constraints.
    Strategy:
      - Take top EM candidate, verify energy_required <= energy_available
      - Verify port utilization allows additional throughput (very simple heuristic)
      - If top candidate fails constraints, try next candidate
    """
    energy_available = data["energy"]["available_mw"]
    port_capacity = data["ports"]["port2_capacity"]
    port_util = data["ports"]["current_utilization"]
    # Conservative available port headroom units (normalized)
    port_headroom = max(0, (1 - port_util)) * port_capacity
    for c in em_candidates:
        if capex_limit_usd is not None and c["capex_estimate_usd"] > capex_limit_usd:
            continue
        if c["energy_required_mw"] <= energy_available and c["estimated_increase_units"] <= port_headroom:
            # Good candidate
            justification = {
                "why": "Meets energy and port constraints",
                "energy_available_mw": energy_available,
                "energy_required_mw": c["energy_required_mw"],
                "port_headroom_units": port_headroom,
                "estimated_increase_units": c["estimated_increase_units"]
            }
            return {
                "recommended_plant": c["plant_id"],
                "expected_increase_pct": f\"+{c['feasible_increase_pct']}%\",
                "investment_usd": c["capex_estimate_usd"],
                "roi_period_months": c["roi_months"],
                "energy_required_mw": c["energy_required_mw"],
                "summary": f\"Expand {c['plant_id']} by {c['feasible_increase_pct']}% using {c['energy_required_mw']} MW.\",
                "justification": justification,
                "explainability": c["explainability"]
            }
    # If none satisfy strict constraints, relax constraints and return top candidate with notes
    top = em_candidates[0]
    justification = {
        "why": "No candidate met strict constraints. Returning top candidate with flagged constraint breaches.",
        "energy_available_mw": energy_available,
        "energy_required_mw": top["energy_required_mw"],
        "port_headroom_units": port_headroom,
        "estimated_increase_units": top["estimated_increase_units"]
    }
    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_pct": f\"+{top['feasible_increase_pct']}% (soft) \",
        "investment_usd": top["capex_estimate_usd"],
        "roi_period_months": top["roi_months"],
        "energy_required_mw": top["energy_required_mw"],
        "summary": f\"Top candidate {top['plant_id']} but constraints require further mitigation.\",
        "justification": justification,
        "explainability": top["explainability"]
    }
