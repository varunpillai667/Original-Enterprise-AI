# enterprise_manager.py
"""
Enterprise-level helper functions for the prototype.

Provides:
- evaluate_steel(payload)
- evaluate_ports(payload)
- evaluate_energy(payload)

Each function accepts a payload (dict) and returns a summary dict.
Designed for use by decision_engine.run_simulation.
"""

from typing import Dict, Any, List


def evaluate_steel(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts: {"plants": [{id, name, current_capacity_tpa, ...}, ...]}
    Returns a summary with plant-level stats and basic health signals.
    """
    plants = payload.get("plants", [])
    plant_summaries: List[Dict[str, Any]] = []
    total_capacity = 0
    for p in plants:
        cap = int(p.get("current_capacity_tpa", 0))
        total_capacity += cap
        plant_summaries.append({
            "id": p.get("id"),
            "name": p.get("name", p.get("id", "")),
            "current_capacity_tpa": cap,
            "utilization_pct": p.get("utilization_pct", 0.75),  # default 75%
            "notes": p.get("notes", ""),
        })
    return {
        "num_plants": len(plants),
        "total_capacity_tpa": total_capacity,
        "plant_summaries": plant_summaries,
    }


def evaluate_ports(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts: {"ports": [{id, ...}, ...]}
    Returns simple port-level summary.
    """
    ports = payload.get("ports", [])
    return {
        "num_ports": len(ports),
        "port_recommendations": [
            "Validate export handling capacity for incremental steel output.",
            "Check berth scheduling and yard stacking for seasonal peaks."
        ],
    }


def evaluate_energy(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts: {"energy_units_list": [{id, ...}, ...]}
    Returns aggregated energy capacity signals.
    """
    plants = payload.get("energy_units_list", [])
    # if each plant had 'available_mw' we could aggregate; use defaults
    total_available = sum(p.get("available_mw", p.get("capacity_mw", 500)) for p in plants)
    return {
        "num_plants": len(plants),
        "total_available_mw": total_available,
        "energy_recommendations": [
            "Confirm spare generation margins and marginal cost for incremental load.",
            "Evaluate short-term grid purchases vs. internal generation."
        ],
    }
