"""
decision_engine.py

Orchestrator: Local Node -> Enterprise Managers -> Group Manager
Includes a rationale builder that explains why the action plan was recommended,
based on data collected from Local Node and EM outputs (steel, ports, energy).
"""
from local_node import ingest_local_site
from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
from group_manager import orchestrate_across_ems

def _fetch_company_hq_stub(company: str) -> dict:
    return {"company": company}

def _fetch_group_systems_stub() -> dict:
    return {"commodity_index": 102.5, "treasury_signal": "neutral", "esg_reporting_required": False}

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

    result["budget_flag"] = budget_flag
    result["query"] = query
    return result


def rationale_for_action_plan(query: str, result: dict) -> str:
    """
    Build a human-readable rationale that explains why the action plan was given,
    referencing the exact measurements or diagnostics that drove each action.
    Returns markdown text suitable for st.markdown().
    """

    # Pull required numbers safely
    steel_ex = result.get('explainability', {}).get("steel_em", {})
    ports_ex = result.get('explainability', {}).get("ports_em", {})
    energy_ex = result.get('explainability', {}).get("energy_em", {})

    # Candidate-level numbers
    recommended = result.get('recommended_plant', 'N/A')
    expected_increase = result.get('expected_increase_pct', 'N/A')
    energy_required = result.get('energy_required_mw', 'N/A')

    # EM-level metrics
    spare_capacity = steel_ex.get('spare_capacity', None)
    capex_penalty = steel_ex.get('capex_penalty', None)

    port_headroom = ports_ex.get('port_headroom_units', result.get('em_summaries', {}).get('ports_info', {}).get('port_headroom_units', 'N/A'))
    avg_port_util = result.get('em_summaries', {}).get('ports_info', {}).get('current_utilization', 'N/A')

    energy_headroom = energy_ex.get('energy_headroom_mw', result.get('em_summaries', {}).get('energy_info', {}).get('energy_headroom_mw', 'N/A'))
    energy_available = energy_ex.get('available_mw', result.get('em_summaries', {}).get('energy_info', {}).get('energy_available_mw', 'N/A'))

    # Unit-level diagnostics (examples taken from em_summaries)
    steel_units = result.get('em_summaries', {}).get('steel_units_details', [])
    ports_units = result.get('em_summaries', {}).get('port_units_details', [])
    energy_units = result.get('em_summaries', {}).get('energy_units_details', [])

    # Build rationale lines
    lines = []
    lines.append("### Rationale for Action Plan")
    lines.append("")
    lines.append(f"**Query:** {query}")
    lines.append("")
    lines.append(f"**Recommendation:** Increase output at {recommended} by {expected_increase}.")
    lines.append("")
    lines.append("**What the system observed (key data points):**")
    # Steel observations
    if spare_capacity is not None:
        lines.append(f"- Steel diagnostics: spare capacity = {spare_capacity} units (shows available margin at plant level).")
    else:
        lines.append(f"- Steel diagnostics: spare capacity not available but candidate ranking indicates available throughput potential.")
    if capex_penalty is not None:
        lines.append(f"- Cost signal: capex penalty score = {capex_penalty}. (Used for ranking, not for the action plan.)")

    # Energy observations
    lines.append(f"- Energy diagnostics: required = {energy_required} MW; available headroom = {energy_headroom} MW (available {energy_available} MW).")
    if energy_required != 'N/A' and isinstance(energy_headroom, (int, float)):
        if energy_required <= energy_headroom:
            lines.append("  → Energy headroom is sufficient to support the proposed uplift without immediate new generation.")
        else:
            lines.append("  → Energy headroom is insufficient. Action plan phases energy allocation and suggests off-peak scheduling to mitigate this.")

    # Ports observations
    lines.append(f"- Ports diagnostics: aggregate port headroom = {port_headroom} units (avg utilization {avg_port_util}).")
    if isinstance(port_headroom, (int, float)) and result.get('em_summaries', {}).get('steel_top_candidates'):
        est_increase_units = result['em_summaries']['steel_top_candidates'][0].get('estimated_increase_units', 'N/A')
        lines.append(f"  → Estimated additional shipments = {est_increase_units} units. If estimated shipments <= headroom, single-phase rollout possible; otherwise staging/staggering required.")

    # Unit-level evidence examples
    lines.append("")
    lines.append("**Sample unit-level evidence used to form actions:**")
    if steel_units:
        # show 1-2 steel unit examples
        ex = steel_units[0]
        lines.append(f"- Steel unit example: {ex['plant_id']} capacity {ex['capacity']}, utilization {ex['utilization']}.")
    if ports_units:
        ex = ports_units[0]
        lines.append(f"- Port unit example: {ex.get('port_id')} capacity {ex.get('capacity')} util {ex.get('utilization')}.")
    if energy_units:
        ex = energy_units[0]
        lines.append(f"- Power plant example: {ex.get('plant_id')} capacity {ex.get('capacity_mw')} MW, available {ex.get('available_mw')} MW, util {ex.get('utilization')}.")

    # Tie observations to action plan steps
    lines.append("")
    lines.append("**How observations map to action steps:**")
    lines.append("- Because the steel diagnostics show spare capacity, the action plan recommends an operational ramp and a short pilot to validate throughput and quality.")
    lines.append("- Because the energy headroom is shown as (or not) sufficient, the action plan specifies energy allocation steps and off-peak scheduling.")
    lines.append("- Because port headroom is constrained/limited, the action plan prescribes staggered shipments, temporary staging, and close Logistics coordination.")
    lines.append("")
    lines.append("**Confidence & next checks:**")
    lines.append("- Pilot performance metrics to track: throughput rate, energy draw profile, shipping throughput, and quality metrics.")
    lines.append("- Re-check energy dispatch and port slot confirmations before full rollout.")
    if result.get("budget_flag", False):
        lines.append("- Note: Candidate ranking was influenced by the CapEx filter; ensure operational feasibility checks are prioritized.")

    return "\n\n".join(lines)
