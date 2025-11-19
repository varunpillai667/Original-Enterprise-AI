"""
decision_engine.py

Orchestrator that:
- Ingests local node payload(s)
- Fetches company HQ stubs (simulated)
- Calls each Enterprise Manager with both HQ and Local Node inputs
- Calls Group Manager with cross-EM outputs and group-level inputs

This version ensures the UI-visible EM summaries include detailed unit lists:
- steel_units_details
- port_units_details
- energy_units_details
"""
from local_node import ingest_local_site
from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
from group_manager import orchestrate_across_ems

def _fetch_company_hq_stub(company: str) -> dict:
    return {"company": company, "erp_snapshot_note": f"ERP snapshot for {company}"}

def _fetch_group_systems_stub() -> dict:
    return {"commodity_index": 102.5, "treasury_signal": "neutral", "esg_reporting_required": False}

# Canonical unit lists aligned with your architecture (kept for reference)
PORT_UNITS = ["Port 1", "Port 2", "Port 3", "Port 4"]
STEEL_UNITS = ["SP1", "SP2", "SP3", "SP4"]
ENERGY_UNITS = ["PP1", "PP2", "PP3"]

def run_simulation(query: str, capex_limit_usd: float = None) -> dict:
    # --- ingest local node (OT) payload ---
    local_payload = ingest_local_site(site_id="Port+Plant-Site")

    # --- simulated company HQ stubs ---
    steel_hq = _fetch_company_hq_stub("CompanyB_Steel")
    ports_hq = _fetch_company_hq_stub("CompanyA_Ports")
    energy_hq = _fetch_company_hq_stub("CompanyC_Energy")

    # --- simulated group-level systems ---
    group_systems = _fetch_group_systems_stub()

    # --- call each Enterprise Manager ---
    steel_candidates = evaluate_steel(steel_hq, local_payload, budget_usd=capex_limit_usd) if capex_limit_usd is not None else evaluate_steel(steel_hq, local_payload)
    ports_info = evaluate_ports(ports_hq, local_payload)
    energy_info = evaluate_energy(energy_hq, local_payload)

    # --- handle budget filter that produced empty candidate list ---
    budget_flag = False
    if not steel_candidates:
        budget_flag = True
        steel_candidates = evaluate_steel(steel_hq, local_payload, budget_usd=None)

    # --- group manager orchestration across EMs + group-level signals ---
    result = orchestrate_across_ems(steel_candidates, ports_info, energy_info, group_systems, capex_limit_usd)

    # --- provenance metadata (internal) ---
    result["provenance"] = {
        "local_node_id": local_payload.get("site_id"),
        "steel_hq": steel_hq.get("company"),
        "ports_hq": ports_hq.get("company"),
        "energy_hq": energy_hq.get("company"),
        "group_systems": list(group_systems.keys()),
        "budget_flag": budget_flag
    }

    # --- EM summaries for UI (concise top candidates + full unit details) ---
    # steel_units_details: from local_payload steel_plants (full details)
    steel_units_details
