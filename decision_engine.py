# decision_engine.py
import json
import os
import re
from typing import Dict, Any, List

from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy
from group_manager import orchestrate_across_ems

MOCK_PATH = "/mnt/data/mock_data.json"

def _load_mock_data():
    """
    Load consolidated data representing processed information from all LOCAL Nodes
    via their respective Enterprise Managers.
    
    In production, this would be real-time API calls to:
    - Steel Enterprise Manager (Company B)
    - Ports Enterprise Manager (Company A) 
    - Energy Enterprise Manager (Company C)
    """
    if os.path.exists(MOCK_PATH):
        with open(MOCK_PATH, "r") as f:
            return json.load(f)
    # Fallback data representing the three companies under Group X
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
    """
    Parse natural language strategic query from Group CEO.
    
    Converts business language into structured constraints for
    cross-company optimization by the Group Manager.
    """
    q = query.lower()
    parsed = {"target_increase_tpa": None, "max_roi_months": None, "distribution_strategy": "selective"}
    
    # Detect strategic intent
    if "across all" in q or "all steel plants" in q or "distribute" in q:
        parsed["distribution_strategy"] = "across_all"

    # Parse capacity target
    m = re.search(r"(\d+(?:\.\d+)?)\s*(million|millions|mtpa|m tpa|mt)\s*", q)
    if m:
        num = float(m.group(1))
        parsed["target_increase_tpa"] = int(num * 1_000_000)
    else:
        # Default strategic target: 2 MTPA
        parsed["target_increase_tpa"] = 2_000_000

    # Parse investment recovery period
    m_years = re.search(r"(\d+)\s*years?", q)
    if m_years:
        parsed["max_roi_months"] = int(m_years.group(1)) * 12
    else:
        m_months = re.search(r"(\d+)\s*months?", q)
        if m_months:
            parsed["max_roi_months"] = int(m_months.group(1))
        else:
            # Default strategic ROI: 3 years
            parsed["max_roi_months"] = 36

    return parsed

def run_simulation(query: str) -> Dict[str, Any]:
    """
    Main decision engine that simulates the Original Enterprise AI workflow.
    
    Architecture Flow:
    1. Group CEO places strategic query in Group Manager interface
    2. Group Manager retrieves analyzed data from all Enterprise Managers
    3. Enterprise Managers have processed data from their LOCAL Nodes
    4. Group Manager performs cross-company optimization
    5. Returns unified strategic recommendation with explainable AI
    
    Companies in Group X:
    - Company A: Port Operations (4 ports)
    - Company B: Steel Manufacturing (4 plants) 
    - Company C: Energy Generation (3 power plants)
    """
    # Load data representing processed intelligence from Enterprise Managers
    mock = _load_mock_data()
    steel_plants = mock.get("steel_plants", [])
    ports = mock.get("ports", {})
    energy = mock.get("energy", {})
    group_systems = mock.get("group_systems", {})

    # Parse strategic query into optimization constraints
    constraints = _parse_query(query)
    target_tpa = constraints["target_increase_tpa"]
    max_roi = constraints["max_roi_months"]
    distribution_strategy = constraints["distribution_strategy"]

    # Get analyzed data from Enterprise Managers
    # In production, these would be real-time API calls to respective EMs
    steel_candidates = evaluate_steel(steel_plants, target_tpa)  # From Steel EM (Company B)
    ports_info = evaluate_ports(ports)  # From Ports EM (Company A)  
    energy_info = evaluate_energy(energy)  # From Energy EM (Company C)

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

    # Compile comprehensive Enterprise Manager summaries
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

    # Add query context for audit and explainability
    result["query_constraints"] = constraints
    result["query"] = query
    result["architecture_note"] = "Analysis performed via Group Manager coordinating Steel EM, Ports EM, and Energy EM"
    
    return result

# Example simulation for testing
if __name__ == "__main__":
    test_query = "How can we increase steel production capacity by 2 million tonnes per annum across all steel plants while ensuring existing commercial cargo operations at ports and grid sales from power plants remain unaffected? The additional investment should be recovered within three years."
    
    print("Running Original Enterprise AI Simulation...")
    print("=" * 60)
    print(f"Strategic Query: {test_query}")
    print("=" * 60)
    
    result = run_simulation(test_query)
    
    print(f"Recommended Plants: {result.get('recommended_plant')}")
    print(f"Expected Increase: {result.get('expected_increase_tpa', 0)/1_000_000:.2f} MTPA")
    print(f"Total Investment: ${result.get('investment_usd', 0)/1_000_000:.2f}M")
    print(f"ROI Period: {result.get('roi_months', 0)} months")
    print(f"Energy Required: {result.get('energy_required_mw', 0)} MW")
    
    print("\n" + "=" * 60)
    print("ENTERPRISE AI SIMULATION COMPLETE")
    print("=" * 60)
