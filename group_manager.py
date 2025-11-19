"""
group_manager.py

Takes outputs from Steel-EM (list of candidates), Ports-EM (port struct),
and Energy-EM (energy struct). Runs cross-enterprise checks to select the optimal
steel expansion plan that respects port and energy constraints.
"""
from typing import Dict, Any, List

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           capex_limit_usd: float = None) -> Dict[str, Any]:
    """
    Strategy:
      - Iterate steel candidates in order of EM score
      - For each candidate, check:
          * candidate.energy_required_mw <= energy_info['energy_headroom_mw']
          * candidate.estimated_increase_units <= ports_info['port_headroom_units']
          * candidate.capex_estimate_usd <= capex_limit_usd (if provided)
      - Return the first candidate satisfying all constraints with cross-EM justification.
      - If none match, return top candidate with flagged constraint breaches and recommended mitigations.
    """
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
            justification = {
                "why": "Candidate meets energy and port headroom constraints",
                "energy_headroom_mw": energy_headroom,
                "energy_required_mw": c["energy_required_mw"],
                "port_headroom_units": port_headroom,
                "estimated_increase_units": c["estimated_increase_units"]
            }
            return {
                "recommended_plant": c["plant_id"],
                "expected_increase_pct": f"+{c['feasible_increase_pct']}%",
                "investment_usd": c["capex_estimate_usd"],
                "roi_period_months": c["roi_months"],
                "energy_required_mw": c["energy_required_mw"],
                "summary": f"Select {c['plant_id']} expansion; passes port & energy checks.",
                "justification": justification,
                "explainability": {
                    "steel_em": c.get("explainability", {}),
                    "ports_em": ports_info.get("explainability", {}),
                    "energy_em": energy_info.get("explainability", {})
                }
            }

    # No candidate satisfied hard constraints: return top candidate with breach details
    top = steel_candidates[0]
    breaches = {
        "energy_required_mw": top["energy_required_mw"],
        "energy_headroom_mw": energy_headroom,
        "estimated_increase_units": top["estimated_increase_units"],
        "port_headroom_units": port_headroom,
        "capex_exceeded": capex_limit_usd is not None and top["capex_estimate_usd"] > capex_limit_usd
    }
    mitigation = []
    if breaches["energy_required_mw"] > breaches["energy_headroom_mw"]:
        mitigation.append("increase energy supply or phase expansion")
    if breaches["estimated_increase_units"] > breaches["port_headroom_units"]:
        mitigation.append("stagger shipments or expand port throughput")
    if breaches["capex_exceeded"]:
        mitigation.append("raise CapEx budget or choose lower-capex option")

    return {
        "recommended_plant": top["plant_id"],
        "expected_increase_pct": f"+{top['feasible_increase_pct']}% (soft)",
        "investment_usd": top["capex_estimate_usd"],
        "roi_period_months": top["roi_months"],
        "energy_required_mw": top["energy_required_mw"],
        "summary": f"Top candidate {top['plant_id']} requires mitigation: {', '.join(mitigation)}",
        "justification": {
            "why": "Top candidate selected but crosses one or more group constraints",
            "breaches": breaches,
            "recommended_mitigations": mitigation
        },
        "explainability": {
            "steel_em": top.get("explainability", {}),
            "ports_em": ports_info.get("explainability", {}),
            "energy_em": energy_info.get("explainability", {})
        }
    }
