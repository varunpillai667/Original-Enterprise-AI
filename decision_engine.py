"""
decision_engine.py

Orchestrator that:
- Ingests local node payload(s)
- Fetches company HQ stubs (simulated)
- Calls each Enterprise Manager with both HQ and Local Node inputs
- Calls Group Manager with cross-EM outputs and group-level inputs
"""
from local_node import ingest_local_site
from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
from group_manager import orchestrate_across_ems

def _fetch_company_hq_stub(company: str) -> dict:
    return {"company": company, "erp_snapshot_note": f"ERP snapshot for {company}"}

def _fetch_group_systems_stub() -> dict:
    return {"commodity_index": 102.5, "treasury_signal": "neutral", "esg_reporting_required": False}

# Canonical unit lists aligned with your architecture
PORT_UNITS = ["Port 1", "Port 2", "Port 3", "Port 4"]
STEEL_UNITS = ["SP1", "SP2", "SP3", "SP4"]
ENERGY_UNITS = ["PP1", "PP2", "PP3"]

def run_simulation(query: str, capex_limit_usd: float = None) -> dict:
    local_payload = ingest_local_site(site_id="Port+Plant-Site")
    steel_hq = _fetch_company_hq_stub("CompanyB_Steel")
    ports_hq = _fetch_company_hq_stub("CompanyA_Ports")
    energy_hq = _fetch_company_hq_stub("CompanyC_Energy")
    group_systems = _fetch_group_systems_stub()

    steel_candidates = evaluate_steel(steel_hq, local_payload, budget_usd=capex_limit_usd) if capex_limit_usd is not None else evaluate_steel(steel_hq, local_payload)
    ports_info = evaluate_ports(ports_hq, local_payload)
    energy_info = evaluate_energy(energy_hq, local_payload)

    budget_flag = False
    if not steel_candidates:
        budget_flag = True
        steel_candidates = evaluate_steel(steel_hq, local_payload, budget_usd=None)

    result = orchestrate_across_ems(steel_candidates, ports_info, energy_info, group_systems, capex_limit_usd)

    result["provenance"] = {
        "local_node_id": local_payload.get("site_id"),
        "steel_hq": steel_hq.get("company"),
        "ports_hq": ports_hq.get("company"),
        "energy_hq": energy_hq.get("company"),
        "group_systems": list(group_systems.keys()),
        "budget_flag": budget_flag
    }

    result["em_summaries"] = {
        "steel_top_candidates": steel_candidates[:3],
        "ports_info": ports_info,
        "energy_info": energy_info,
        "steel_units": STEEL_UNITS,
        "port_units": PORT_UNITS,
        "energy_units": ENERGY_UNITS
    }

    result["query"] = query
    return result

def explain_decision(query: str, result: dict) -> str:
    expl = f"Cross-EM Explainable Narrative\n\n"
    expl += f"Query: {query}\n\n"
    expl += "Provenance (data sources):\n"
    expl += f"- Local Node: {result['provenance']['local_node_id']}\n"
    expl += f"- Steel Company HQ: {result['provenance']['steel_hq']}\n"
    expl += f"- Ports Company HQ: {result['provenance']['ports_hq']}\n"
    expl += f"- Energy Company HQ: {result['provenance']['energy_hq']}\n"
    expl += f"- Group systems: {', '.join(result['provenance']['group_systems'])}\n\n"

    expl += f"Recommendation: {result['recommended_plant']} — {result['summary']}\n\n"
    expl += "Explainability (per EM):\n"
    expl += "- Steel EM: " + str(result['explainability'].get("steel_em", {})) + "\n"
    expl += "- Ports EM: " + str(result['explainability'].get("ports_em", {})) + "\n"
    expl += "- Energy EM: " + str(result['explainability'].get("energy_em", {})) + "\n"

    if result['provenance'].get("budget_flag", False):
        expl += "\nNOTE: CapEx limit filtered candidates; recommendation shows top candidate but budget flag is set.\n"

    return expl
