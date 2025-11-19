"""
decision_engine.py

Orchestrator that:
- Ingests local node payload(s)
- Fetches company HQ stubs (simulated)
- Calls each Enterprise Manager with both HQ and Local Node inputs
- Calls Group Manager with cross-EM outputs and group-level inputs
Returns detailed EM unit lists for UI display.
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
    # Read local node payload
    local_payload = ingest_local_site(site_id="Port+Plant-Site")

    # Company HQ stubs
    steel_hq = _fetch_company_hq_stub("CompanyB_Steel")
    ports_hq = _fetch_company_hq_stub("CompanyA_Ports")
    energy_hq = _fetch_company_hq_stub("CompanyC_Energy")
    group_systems = _fetch_group_systems_stub()

    # Enterprise Managers produce candidate lists and unit details
    steel_candidates = evaluate_steel(steel_hq, local_payload, budget_usd=capex_limit_usd) if capex_limit_usd is not None else evaluate_steel(steel_hq, local_payload)
    ports_info = evaluate_ports(ports_hq, local_payload)    # returns aggregated + ports_list
    energy_info = evaluate_energy(energy_hq, local_payload) # returns aggregated + energy_units

    budget_flag = False
    if not steel_candidates:
        budget_flag = True
        steel_candidates = evaluate_steel(steel_hq, local_payload, budget_usd=None)

    # Group Manager applies cross-EM constraints
    result = orchestrate_across_ems(steel_candidates, ports_info, energy_info, group_systems, capex_limit_usd)

    # Provenance (kept internal structure; UI doesn't show file/doc references)
    result["provenance"] = {
        "local_node_id": local_payload.get("site_id"),
        "steel_hq": steel_hq.get("company"),
        "ports_hq": ports_hq.get("company"),
        "energy_hq": energy_hq.get("company"),
        "group_systems": list(group_systems.keys()),
        "budget_flag": budget_flag
    }

    # EM summaries include concise candidate list and full unit details
    result["em_summaries"] = {
        "steel_top_candidates": steel_candidates[:3],
        "ports_info": {
            "port_headroom_units": ports_info.get("port_headroom_units"),
            "current_utilization": ports_info.get("current_utilization")
        },
        "energy_info": {
            "energy_headroom_mw": energy_info.get("energy_headroom_mw"),
            "energy_available_mw": energy_info.get("energy_available_mw")
        },
        # full details for UI
        "steel_units_details": [
            # create unit detail entries using mock data (local_payload steel_plants)
            {
                "plant_id": p.get("plant_id"),
                "capacity": p.get("capacity"),
                "utilization": p.get("utilization"),
                "capex_estimate_usd": p.get("capex_estimate_usd")
            } for p in local_payload.get("steel_plants", [])
        ],
        "port_units_details": ports_info.get("ports_list", []),
        "energy_units_details": energy_info.get("energy_units_list", [])
    }

    result["query"] = query
    return result

def explain_decision(query: str, result: dict) -> str:
    expl = f"Cross-EM Explainable Narrative\n\n"
    expl += f"Query: {query}\n\n"
    expl += "Recommendation: " + f"{result['recommended_plant']} — {result['summary']}\n\n"
    expl += "Explainability (per EM):\n"
    expl += "- Steel EM: " + str(result['explainability'].get("steel_em", {})) + "\n"
    expl += "- Ports EM: " + str(result['explainability'].get("ports_em", {})) + "\n"
    expl += "- Energy EM: " + str(result['explainability'].get("energy_em", {})) + "\n"
    if result['provenance'].get("budget_flag", False):
        expl += "\nNOTE: CapEx limit filtered candidates; recommendation shows top candidate but budget flag is set.\n"
    return expl
