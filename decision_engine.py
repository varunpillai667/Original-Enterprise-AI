"""
decision_engine.py

Orchestrator: Local Node -> Enterprise Managers (Steel, Ports, Energy) -> Group Manager
Produces em_summaries with full unit details for UI consumption.
"""
from local_node import ingest_local_site
from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
from group_manager import orchestrate_across_ems

def _fetch_company_hq_stub(company: str) -> dict:
    return {"company": company}

def _fetch_group_systems_stub() -> dict:
    return {"commodity_index": 102.5, "treasury_signal": "neutral", "esg_reporting_required": False}

# canonical unit lists (kept internally)
PORT_UNITS = ["Port 1", "Port 2", "Port 3", "Port 4"]
STEEL_UNITS = ["SP1", "SP2", "SP3", "SP4"]
ENERGY_UNITS = ["PP1", "PP2", "PP3"]

def run_simulation(query: str, capex_limit_usd: float = None) -> dict:
    # ingest local payload
    local_payload = ingest_local_site(site_id="Port+Plant-Site")

    # company HQ stubs
    steel_hq = _fetch_company_hq_stub("CompanyB_Steel")
    ports_hq = _fetch_company_hq_stub("CompanyA_Ports")
    energy_hq = _fetch_company_hq_stub("CompanyC_Energy")
    group_systems = _fetch_group_systems_stub()

    # call EMs
    steel_candidates = evaluate_steel(steel_hq, local_payload, budget_usd=capex_limit_usd) if capex_limit_usd is not None else evaluate_steel(steel_hq, local_payload)
    ports_info = evaluate_ports(ports_hq, local_payload)
    energy_info = evaluate_energy(energy_hq, local_payload)

    # handle budget filter empty-result
    budget_flag = False
    if not steel_candidates:
        budget_flag = True
        steel_candidates = evaluate_steel(steel_hq, local_payload, budget_usd=None)

    # group manager decision
    result = orchestrate_across_ems(steel_candidates, ports_info, energy_info, group_systems, capex_limit_usd)

    # em_summaries with full unit details (used by UI)
    steel_units_details = [
        {
            "plant_id": p.get("plant_id"),
            "capacity": p.get("capacity"),
            "utilization": p.get("utilization"),
            "capex_estimate_usd": p.get("capex_estimate_usd"),
            "roi_months": p.get("roi_months")
        } for p in local_payload.get("steel_plants", [])
    ]

    port_units_details = ports_info.get("ports_list", [])
    if not port_units_details:
        # synthesize safe defaults if EM didn't provide list
        port_units_details = [{"port_id": name, "capacity": 0, "utilization": 0.0} for name in PORT_UNITS]

    energy_units_details = energy_info.get("energy_units_list", [])
    if not energy_units_details:
        energy_units_details = [{"plant_id": name, "capacity_mw": 0, "utilization": 0.0, "available_mw": 0} for name in ENERGY_UNITS]

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
        "steel_units_details": steel_units_details,
        "port_units_details": port_units_details,
        "energy_units_details": energy_units_details
    }

    # metadata
    result["budget_flag"] = budget_flag
    result["query"] = query
    return result

def explain_decision(query: str, result: dict) -> str:
    # build a clean, human-readable narrative (no dict raw printing)
    steel_ex = result.get('explainability', {}).get("steel_em", {})
    ports_ex = result.get('explainability', {}).get("ports_em", {})
    energy_ex = result.get('explainability', {}).get("energy_em", {})

    spare_capacity = steel_ex.get('spare_capacity', 'N/A')
    capex_penalty = steel_ex.get('capex_penalty', 'N/A')
    port_headroom = ports_ex.get('port_headroom_units', 'N/A')
    available_mw = energy_ex.get('available_mw', energy_ex.get('energy_available_mw', 'N/A'))
    reserve_buffer = energy_ex.get('reserve_buffer_mw', energy_ex.get('reserve_buffer_mw', 'N/A'))

    lines = []
    lines.append("### Cross-EM Explainable Narrative")
    lines.append("")
    lines.append(f"**Query:** {query}")
    lines.append("")
    lines.append(f"**Recommendation:** {result.get('recommended_plant','N/A')} — {result.get('summary','')}")
    lines.append("")
    lines.append("**Explainability (per EM)**")
    lines.append(f"- **Steel EM:** spare capacity {spare_capacity}, capex penalty {capex_penalty}")
    lines.append(f"- **Ports EM:** port headroom {port_headroom}")
    lines.append(f"- **Energy EM:** available {available_mw} MW, reserve buffer {reserve_buffer} MW")
    if result.get("budget_flag", False):
        lines.append("")
        lines.append("**NOTE:** The CapEx limit filtered out all candidates; the recommendation shows the top candidate and flags the budget constraint.")
    return "\n\n".join(lines)
