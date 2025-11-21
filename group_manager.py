# group_manager.py
"""
Group-level orchestration helpers.

Function:
- orchestrate_across_ems(em_summaries: Dict[str, Any]) -> Dict[str, Any]
"""

from typing import Dict, Any


def orchestrate_across_ems(em_summaries: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform lightweight cross-enterprise checks and return a combined summary.

    This is intentionally simple: it flags if any EM reports shortages (very high-level).
    """
    combined = {"flags": [], "summary": {}}

    # Check energy headroom
    energy = em_summaries.get("energy_info", {})
    if isinstance(energy, dict):
        total_available = energy.get("total_available_mw")
        if total_available is not None and total_available < 500:
            combined["flags"].append("Limited aggregate energy headroom across Group X.")

    # Check ports headroom (just a placeholder)
    ports = em_summaries.get("ports_info", {})
    if isinstance(ports, dict) and ports.get("num_ports", 0) < 1:
        combined["flags"].append("No ports detected in EM summaries.")

    combined["summary"] = {
        "energy": energy,
        "ports": ports,
        "steel": em_summaries.get("steel_info", {}),
    }

    return combined
