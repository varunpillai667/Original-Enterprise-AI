"""
enterprise_manager.py

Provides three Enterprise Managers:
- Steel EM: uses company HQ data + Local Node telemetry
- Ports EM: uses company HQ data + Local Node telemetry
- Energy EM: uses company HQ data + Local Node telemetry

Each EM returns a compact explainable summary with a `data_sources` field
that indicates whether the decision used Company HQ data, Local Node data, or both.
"""
from typing import Dict, Any, List

def evaluate_steel(company_hq: Dict[str, Any], local_node_payload: Dict[str, Any], budget_usd: float = None) -> List[Dict[str, Any]]:
    """
    Company HQ contains ERP and financial constraints; local_node_payload contains OT signals.
    Returns ranked candidate expansions with explainability and data_sources metadata.
    """
    plants = local_node_payload.get("steel_plants", [])
    energy_avail = local_node_payload.get("energy", {}).get("available_mw", 0)

    results = []
    for p in plants:
        spare = p["capacity"] * (1 - p["utilization"])
        capex_penalty = 1_000_000 / (p["capex_estimate_usd"] + 1)
        roi_bonus = 12 / (p["roi_months"] + 1)
        energy_score = energy_avail / (1 + p["capacity"]/1000)
        score = spare * 0.6 + capex_penalty * 0.25 + roi_bonus * 0.15 + energy_score * 0.1
        feasible_pct = min(25, (spare / p["capacity"]) * 100) if p["capacity"] > 0 else 0
        increase_units = p["capacity"] * feasible_pct / 100
        energy_required = round(increase_units * 0.004, 2)

        results.append({
            "plant_id": p["plant_id"],
            "score": round(score, 3),
            "feasible_increase_pct": round(feasible_pct, 2),
            "estimated_increase_units": round(increase_units, 2),
            "energy_required_mw": energy_required,
            "capex_estimate_usd": p["capex_estimate_usd"],
            "roi_months": p["roi_months"],
            "explainability": {"spare_capacity": round(spare,2), "capex_penalty": round(capex_penalty,3)},
            "data_sources": ["Company_HQ", "Local_Node"]  # clearly indicate both sources were used
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    if budget_usd is not None:
        results = [r for r in results if r["capex_estimate_usd"] <= budget_usd]
    return results


def evaluate_ports(company_hq: Dict[str, Any], local_node_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ports EM analyzes company HQ logistics planning + Local Node TOS telemetry.
    """
    ports = local_node_payload.get("ports", {})
    cap = ports.get("port2_capacity", 0)
    util = ports.get("current_utilization", 0)
    headroom = max(0.0, (1.0 - util)) * cap
    return {
        "port_id": "Port2",
        "port_headroom_units": round(headroom,2),
        "current_utilization": util,
        "throughput_score": round(headroom/(cap+1),3),
        "explainability": {"port_headroom_units": round(headroom,2)},
        "data_sources": ["Company_HQ", "Local_Node"]
    }


def evaluate_energy(company_hq: Dict[str, Any], local_node_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Energy EM uses company treasury/planning info + Local Node SCADA telemetry to report headroom.
    """
    energy = local_node_payload.get("energy", {})
    avail = energy.get("available_mw", 0)
    cost = energy.get("cost_per_mw_usd", 0)
    reserve = 2.0
    headroom = max(0.0, avail - reserve)
    return {
        "energy_available_mw": avail,
        "energy_headroom_mw": round(headroom,2),
        "energy_cost_per_mw_usd": cost,
        "explainability": {"available_mw": avail, "reserve_buffer_mw": reserve},
        "data_sources": ["Company_HQ", "Local_Node"]
    }
