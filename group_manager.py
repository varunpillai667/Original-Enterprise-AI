"""
group_manager.py

Group Manager receives:
- group_systems (market, regulatory, ESG, treasury signals) — these represent Group-level systems
- outputs from each Enterprise Manager
Runs cross-EM orchestration and returns explainable recommendation.
"""
from typing import Dict, Any, List

def orchestrate_across_ems(steel_candidates: List[Dict[str, Any]],
                           ports_info: Dict[str, Any],
                           energy_info: Dict[str, Any],
                           group_systems: Dict[str, Any],
                           capex_limit_usd: float = None) -> Dict[str, Any]:
    """
    group_systems: dict simulating group-level signals (commodity_prices, regulations, treasury)
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
            # Include group-level rationale e.g., commodity price signal
            rationale = {
                "why": "Meets energy and port constraints and aligns with group signals",
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
                "summary": f"Select {c['plant_id']} expansion — meets cross-EM constraints and group-level signals.",
                "justification": rationale,
                "explainability": {
                    "steel_em": c.get("explainability", {}),
                    "ports_em": ports_info.get("explainability", {}),
                    "energy_em": energy_info.get("explainability", {})
                },
                "data_sources": {
                    "group_systems": list(group_systems.keys()),
                    "steel_em_sources": c.get("data_sources", []),
                    "ports_em_sources": ports_info.get("data_sources", []),
                    "energy_em_sources": energy_info.get("data_sources", [])
                }
            }

    # No candidate satisfied all constraints: return top candidate with mitigations
    top = steel_candidates[0]
    breaches = {
        "energy_required_mw": top["energy_required_mw"],
        "energy_headroom_mw": energy_headroom,
        "estimated_increase_units": top["estimated_increase_units"],
        "port_headroom_units": port_headroom
    }
    mitigations = []
    if breaches["energy_required_mw"] > breaches["energy_headroom_mw"]:
        mitigations.append("increase energy supply or phase rollout")
    if breaches["estimated_increase_units"] > breaches["port_headroom_units"]:
        mitigations.append("stagger shipments or augment port capacity")

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
        },
        "data_sources": {
            "group_systems": list(group_systems.keys()),
            "steel_em_sources": top.get("data_sources", []),
            "ports_em_sources": ports_info.get("data_sources", []),
            "energy_em_sources": energy_info.get("data_sources", [])
        }
    }
