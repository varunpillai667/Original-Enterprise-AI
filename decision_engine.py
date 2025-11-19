"""
decision_engine.py (orchestrator)
Coordinates Local Node -> Enterprise Manager -> Group Manager flows.
Provides run_simulation(query, capex_limit_usd=None) and explain_decision() to the Streamlit app.
This module aims to align code behavior with the Whitepaper & Operational Flow documents.
"""
from typing import Dict, Any
from local_node import ingest_data
from enterprise_manager import evaluate_plants
from group_manager import orchestrate

def run_simulation(query: str, capex_limit_usd: float = None) -> Dict[str, Any]:
    """
    High-level orchestration:
      - Ingest data from LOCAL Nodes
      - EM evaluates plants
      - GM orchestrates final recommendation
    """
    data = ingest_data()
    em_candidates = evaluate_plants(data, budget_usd=capex_limit_usd)
    if not em_candidates:
        raise RuntimeError(\"No EM candidates available for evaluation.\")
    result = orchestrate(em_candidates, data, capex_limit_usd)
    # Attach metadata
    result["query"] = query
    result["timestamp"] = data["timestamp"]
    result["data_snapshot"] = {
        "energy": data["energy"],
        "ports": data["ports"]
    }
    return result

def explain_decision(query: str, result: Dict[str, Any]) -> str:
    """
    Create an explainability narrative matching the whitepaper style.
    """
    expl = f\"\"\"**Operational Simulation Flow — Explainability**\n\n\"\"\"\n
    expl += f\"1️⃣ **CEO Query:** {query}\\n\\n\"\n
    expl += \"2️⃣ **Group Manager:** Integrated cross-enterprise constraints were evaluated (energy, port capacity).\\n\\n\"\n
    expl += \"3️⃣ **Enterprise Manager (Steel):** Ranked plants using spare capacity, CapEx, and ROI heuristics.\\n\\n\"\n
    expl += f\"4️⃣ **Selected Plant:** {result['recommended_plant']} — Expected increase: {result['expected_increase_pct']}, Energy needed: {result['energy_required_mw']} MW.\\n\\n\"\n\n    expl += \"5️⃣ **Justification & Explainability:**\\n\"\n    for k, v in result['explainability'].items():\n        expl += f\"- {k}: {v}\\n\"\n    expl += \"\\n---\\n\\n\"\n    expl += f\"**System Summary:** {result['summary']}\"\n    return expl
