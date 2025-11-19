# decision_engine.py
"""
Top-level simulation runner. Parses query constraints and orchestrates EM evaluations + Group Manager.
"""

import json
import os
import re
from typing import Dict, Any, List

from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
from group_manager import orchestrate_across_ems

# default mock data path (uploaded by user)
MOCK_PATH = "/mnt/data/mock_data.json"

def _load_mock_data():
    if os.path.exists(MOCK_PATH):
        with open(MOCK_PATH, "r") as f:
            return json.load(f)
    # fallback sample data if file missing
    return {
        "steel_plants": [
            {"plant_id":"SP1","capacity_tpa":1000000,"utilization":0.7,"capex_estimate_usd":750000,"roi_months":8,"energy_required_mw":0.72},
            {"plant_id":"SP2","capacity_tpa":1200000,"utilization":0.65,"capex_estimate_usd":950000,"roi_months":10,"energy_required_mw":1.2},
            {"plant_id":"SP3","capacity_tpa":900000,"utilization":0.6,"capex_estimate_usd":600000,"roi_months":6,"energy_required_mw":0.5},
            {"plant_id":"SP4","capacity_tpa":1100000,"utilization":0.75,"capex_estimate_usd":820000,"roi_months":9.5,"energy_required_mw":1.1}
        ],
        "ports": {
            "port_headroom_units": 10000,
            "current_utilization": 0.82,
            "ports_list":[
                {"port_id":"PortA-1","capacity":5000,"utilization":0.8},
                {"port_id":"PortA-2","capacity":4000,"utilization":0.85}
            ]
        },
        "energy": {
            "energy_headroom_mw": 20,
            "energy_available_mw": 20,
            "energy_units_list":[
                {"plant_id":"PP1","capacity_mw":10,"utilization":0.7,"available_mw":3},
                {"plant_id":"PP2","capacity_mw":15,"utilization":0.6,"available_mw":5}
            ]
        },
        "group_systems": {"commodity_index":102.5, "treasury_signal":"neutral", "esg_reporting_required":False}
    }

def _parse_query(query: str) -> Dict[str, Any]:
    """
    Very small parser to extract:
     - target_increase_tpa (e.g., '2 MTPA' -> 2_000_000)
     - max_roi_months (e.g., '9 months' or '<9 months')
    """
    q = query.lower()
    parsed = {"target_increase_tpa": None, "max_roi_months": None}

    # find patterns like '2 mtpa' or '2 mtpa' or '2 mtpa.'
    m = re.search(r"(\d+(?:\.\d+)?)\s*(mtpa|mta|m tpa|tpa|tpa\.)", q)
    if m:
        # interpret number as million tonnes per annum if unit contains 'mtpa' or 'mta'
        num = float(m.group(1))
        if "mt" in m.group(2):  # mtpa
            parsed["target_increase_tpa"] = int(num * 1_000_000)
        else:
            # 'tpa' -> assume raw tonnes
            parsed["target_increase_tpa"] = int(num)

    # find numeric months constraint
    m2 = re.search(r"less than\s*(\d+)\s*months|<\s*(\d+)\s*months|within\s*(\d+)\s*months", q)
    if m2:
        for g in m2.groups():
            if g:
                parsed["max_roi_months"] = int(g)
                break
    else:
        m3 = re.search(r"(\d+)\s*months", q)
        if m3:
            parsed["max_roi_months"] = int(m3.group(1))

    # fallback defaults
    if parsed["target_increase_tpa"] is None:
        # if no explicit mention, default to 2_000_000 (to match UI default)
        parsed["target_increase_tpa"] = 2_000_000
    if parsed["max_roi_months"] is None:
        parsed["max_roi_months"] = 9

    return parsed

def run_simulation(query: str) -> Dict[str, Any]:
    """
    Full simulation: get data (mock/fallback), call EM evaluators and group manager,
    and assemble results for the UI.
    """
    mock = _load_mock_data()
    steel_plants = mock.get("steel_plants", [])
    ports = mock.get("ports", {})
    energy = mock.get("energy", {})
    group_systems = mock.get("group_systems", {})

    # parse query constraints
    constraints = _parse_query(query)
    target_tpa = constraints["target_increase_tpa"]
    max_roi = constraints["max_roi_months"]

    # run EM evaluations (these return candidate lists and aggregate info)
    steel_candidates = evaluate_steel(steel_plants, target_tpa)
    ports_info = evaluate_ports(ports)
    energy_info = evaluate_energy(energy)

    # orchestrate and pick recommendation
    result = orchestrate_across_ems(
        steel_candidates=steel_candidates,
        ports_info=ports_info,
        energy_info=energy_info,
        group_systems=group_systems,
        required_increase_tpa=target_tpa,
        max_roi_months=max_roi
    )

    # Build EM summaries for UI
    result["em_summaries"] = {
        "steel_top_candidates": steel_candidates[:5],
        "steel_units_details": steel_plants,
        "ports_info": {
            "port_headroom_units": ports.get("port_headroom_units"),
            "current_utilization": ports.get("current_utilization")
        },
        "port_units_details": ports.get("ports_list", []),
        "energy_info": {
            "energy_headroom_mw": energy.get("energy_headroom_mw"),
            "energy_available_mw": energy.get("energy_available_mw")
        },
        "energy_units_details": energy.get("energy_units_list", [])
    }

    # include parsed constraints for rationale
    result["query_constraints"] = constraints
    result["query"] = query
    return result
