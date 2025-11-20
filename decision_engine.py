# decision_engine.py
import json
import os
import re
from typing import Dict, Any, List

from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
from group_manager import orchestrate_across_ems

MOCK_PATH = "/mnt/data/mock_data.json"

def _load_mock_data():
    if os.path.exists(MOCK_PATH):
        with open(MOCK_PATH, "r") as f:
            return json.load(f)
    # Realistic mock data representing the three companies
    return {
        "steel_plants": [
            {"plant_id": "SP1", "capacity_tpa": 1500000, "utilization": 0.75, "capex_estimate_usd": 800000, "energy_required_mw": 1.2},
            {"plant_id": "SP2", "capacity_tpa": 1200000, "utilization": 0.72, "capex_estimate_usd": 750000, "energy_required_mw": 1.0},
            {"plant_id": "SP3", "capacity_tpa": 1800000, "utilization": 0.68, "capex_estimate_usd": 950000, "energy_required_mw": 1.5},
            {"plant_id": "SP4", "capacity_tpa": 1400000, "utilization": 0.70, "capex_estimate_usd": 820000, "energy_required_mw": 1.1}
        ],
        "ports": {
            "ports_list": [
                {"port_id": "PortA1", "annual_capacity_mt": 3.0, "current_throughput_mt": 2.0},
                {"port_id": "PortA2", "annual_capacity_mt": 2.5, "current_throughput_mt": 1.5},
                {"port_id": "PortA3", "annual_capacity_mt": 2.8, "current_throughput_mt": 1.8},
                {"port_id": "PortA4", "annual_capacity_mt": 1.7, "current_throughput_mt": 1.2}
            ]
        },
        "energy": {
            "energy_units_list": [
                {"plant_id": "PP1", "capacity_mw": 800, "available_mw": 320},
                {"plant_id": "PP2", "capacity_mw": 700, "available_mw": 280},
                {"plant_id": "PP3", "capacity_mw": 500, "available_mw": 200}
            ]
        },
        "group_systems": {}
    }

def _parse_query(query: str) -> Dict[str, Any]:
    q = query.lower()
    parsed = {"target_increase_tpa": None, "max_roi_months": None, "distribution_strategy": "selective"}
    
    # Detect distribution strategy
    if "across all" in q or "all steel plants" in q:
        parsed["distribution_strategy"] = "across_all"

    # Parse target increase
    m = re.search(r"(\d+(?:\.\d+)?)\s*(million|millions|mtpa|m tpa|mt)", q)
    if m:
        num = float(m.group(1))
        parsed["target_increase_tpa"] = int(num * 1_000_000)
    else:
        # Default to 2 MTPA if not specified
        parsed["target_increase_tpa"] = 2_000_000

    # Parse ROI period
    m_years = re.search(r"(\d+)\s*years?", q)
    if m_years:
        parsed["max_roi_months"] = int(m_years.group(1)) * 12
    else:
        m_months = re.search(r"(\d+)\s*months?", q)
        if m_months:
            parsed["max_roi_months"] = int(m_months.group(1))
        else:
            # Default to 3 years (36 months)
            parsed["max_roi_months"] = 36

    return parsed

def run_simulation(query: str) -> Dict[str, Any]:
    """
    Main simulation engine that orchestrates analysis across all Enterprise Managers.
    
    Flow:
    1. Group Manager receives strategic query from CEO
    2. Retrieves processed data from all Enterprise Managers
    3. Enterprise Managers have already processed data from their LOCAL Nodes
    4. Group Manager performs cross-company optimization
    5. Returns unified strategic recommendation
    """
    # Load mock data representing processed data from LOCAL Nodes
    mock = _load_mock_data()
    steel_plants = mock.get("steel_plants", [])
    ports = mock.get("ports", {})
    energy = mock.get("energy", {})
    group_systems = mock.get("group_systems", {})

    # Parse strategic query
    constraints = _parse_query(query)
    target_tpa = constraints["target_increase_tpa"]
    max_roi = constraints["max_roi_months"]
    distribution_strategy = constraints["distribution_strategy"]

    # Get analyzed data from Enterprise Managers
    # Note: In real implementation, these would be API calls to respective EMs
    steel_candidates = evaluate_steel(steel_plants, target_tpa)  # Steel EM analysis
    ports_info = evaluate_ports(ports)  # Ports EM analysis  
    energy_info = evaluate_energy(energy)  # Energy EM analysis

    # Group Manager orchestrates cross-company optimization
    result = orchestrate_across_ems(
        steel_candidates=steel_candidates,
        ports_info=ports_info,
        energy_info=energy_info,
        group_systems=group_systems,
        required_increase_tpa=target_tpa,
        max_roi_months=max_roi,
        distribution_strategy=distribution_strategy
    )

    # Compile comprehensive results from all Enterprise Managers
    result["em_summaries"] = {
        "steel_top_candidates": steel_candidates[:10],
        "steel_units_details": steel_plants,
        "ports_info": {
            "port_headroom_tpa": ports_info.get("port_headroom_tpa"),
            "current_throughput_mt": sum([p.get("current_throughput_mt", 0) for p in ports.get("ports_list", [])]),
            "current_throughput_tpa": ports_info.get("current_throughput_tpa")
        },
        "port_units_details": ports.get("ports_list", []),
        "energy_info": {
            "energy_headroom_mw": energy_info.get("energy_headroom_mw"),
            "energy_available_mw": energy_info.get("energy_available_mw"),
            "total_capacity_mw": energy_info.get("total_capacity_mw")
        },
        "energy_units_details": energy_info.get("energy_units_list", [])
    }

    # Add query context for traceability
    result["query_constraints"] = constraints
    result["query"] = query
    
    return result
