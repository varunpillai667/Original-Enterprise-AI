"""
decision_engine.py

Coordinates:
- ingest_data() from Local Node
- evaluate_steel(), evaluate_ports(), evaluate_energy() from Enterprise Managers
- orchestrate_across_ems() from Group Manager

Returns an explainable result that shows the Group Manager exercised cross-EM reasoning.
"""
from local_node import ingest_data
from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
from group_manager import orchestrate_across_ems

def run_simulation(query: str, capex_limit_usd=None) -> dict:
    data = ingest_data()

    # Call each Enterprise Manager (they act independently)
    steel_candidates = evaluate_steel(data, budget_usd=capex_limit_usd) if capex_limit_usd is not None else evaluate_steel(data)
    ports_info = evaluate_ports(data)
    energy_info = evaluate_energy(data)

    # If steel candidates got filtered to empty by budget, fallback to all candidates for diagnostics
    budget_flag = False
    if not steel_candidates:
        budget_flag = True
        steel_candidates = evaluate_steel(data, budget_usd=None)

    # Group Manager orchestrates across EM outputs
    result = orchestrate_across_ems(steel_candidates, ports_info, energy_info, capex_limit_usd)

    result["query"] = query
    result["timestamp"] = data["timestamp"]
    result["budget_flag"] = budget_flag

    # Include short EM summaries (not raw snapshots) so UI can display cross-EM decisions clearly
    result["em_summaries"] = {
        "steel_top_candidates": steel_candidates[:3],  # top 3 for display
        "ports_info": ports_info,
        "energy_info": energy_info
    }

    return result


def explain_decision(query: str, result: dict) -> str:
    expl = f"**Explainable Cross-EM Decision**\n\n"
    expl += f"CEO Query: {query}\n\n"
    expl += "Group Manager orchestration considered:\n"
    expl += f"- Steel EM candidates (top shown): {[c['plant_id'] for c in result['em_summaries']['steel_top_candidates']]}\n"
    expl += f"- Ports EM: headroom {result['em_summaries']['ports_info']['port_headroom_units']} units\n"
    expl += f"- Energy EM: headroom {result['em_summaries']['energy_info']['energy_headroom_mw']} MW\n\n"

    expl += f"Recommendation: **{result['recommended_plant']}** — {result['summary']}\n\n"
    expl += "Explainability details (by EM):\n"
    expl += "- Steel EM: " + str(result["explainability"].get("steel_em", {})) + "\n"
    expl += "- Ports EM: " + str(result["explainability"].get("ports_em", {})) + "\n"
    expl += "- Energy EM: " + str(result["explainability"].get("energy_em", {})) + "\n"

    if result.get("budget_flag", False):
        expl += "\nNOTE: The CapEx limit filtered out candidates; result shows top candidate and flagged budget constraint.\n"

    return expl
