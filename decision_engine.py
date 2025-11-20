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
    # fallback mock data (4 ports, 4 steel plants, 3 power plants)
    return {
        "steel_plants": [
            {"plant_id":"SP1","capacity_tpa":1_300_000,"utilization":0.70,"capex_estimate_usd":700000,"energy_required_mw":1.0},
            {"plant_id":"SP2","capacity_tpa":1_100_000,"utilization":0.68,"capex_estimate_usd":800000,"energy_required_mw":1.1},
            {"plant_id":"SP3","capacity_tpa":900_000,"utilization":0.62,"capex_estimate_usd":600000,"energy_required_mw":0.6},
            {"plant_id":"SP4","capacity_tpa":1_000_000,"utilization":0.75,"capex_estimate_usd":850000,"energy_required_mw":1.2}
        ],
        "ports": {
            "ports_list": [
                {"port_id":"PortA1","annual_capacity_mt":2.0,"current_throughput_mt":1.6},
                {"port_id":"PortA2","annual_capacity_mt":1.5,"current_throughput_mt":1.0},
                {"port_id":"PortA3","annual_capacity_mt":1.8,"current_throughput_mt":1.2},
                {"port_id":"PortA4","annual_capacity_mt":2.5,"current_throughput_mt":2.0}
            ]
        },
        "energy": {
            "energy_units_list":[
                {"plant_id":"PP1","capacity_mw":10,"available_mw":3},
                {"plant_id":"PP2","capacity_mw":12,"available_mw":5},
                {"plant_id":"PP3","capacity_mw":8,"available_mw":4}
            ]
        },
        "group_systems": {}
    }

def _parse_query(query: str) -> Dict[str, Any]:
    q = query.lower()
    parsed = {"target_increase_tpa": None, "max_roi_months": None, "distribution_strategy": "selective"}
    
    # NEW: Detect "across all" strategy
    if "across all" in q:
        parsed["distribution_strategy"] = "across_all"

    # target tpa
    m = re.search(r"(\d+(?:\.\d+)?)\s*(mtpa|mta|m tpa|tpa)", q)
    if m:
        num = float(m.group(1))
        unit = m.group(2)
        if "mt" in unit:
            parsed["target_increase_tpa"] = int(num * 1_000_000)
        else:
            parsed["target_increase_tpa"] = int(num)

    # ROI: months or years
    m_years = re.search(r"(\d+)\s*years?", q)
    if m_years:
        parsed["max_roi_months"] = int(m_years.group(1)) * 12
    else:
        m_months = re.search(r"(\d+)\s*months?", q)
        if m_months:
            parsed["max_roi_months"] = int(m_months.group(1))

    # defaults
    if parsed["target_increase_tpa"] is None:
        parsed["target_increase_tpa"] = 2_000_000
    if parsed["max_roi_months"] is None:
        parsed["max_roi_months"] = 36  # 3 years default per user's request

    return parsed

def run_simulation(query: str) -> Dict[str, Any]:
    mock = _load_mock_data()
    steel_plants = mock.get("steel_plants", [])
    ports = mock.get("ports", {})
    energy = mock.get("energy", {})
    group_systems = mock.get("group_systems", {})

    constraints = _parse_query(query)
    target_tpa = constraints["target_increase_tpa"]
    max_roi = constraints["max_roi_months"]
    distribution_strategy = constraints["distribution_strategy"]

    steel_candidates = evaluate_steel(steel_plants, target_tpa)
    ports_info = evaluate_ports(ports)
    energy_info = evaluate_energy(energy)

    result = orchestrate_across_ems(
        steel_candidates=steel_candidates,
        ports_info=ports_info,
        energy_info=energy_info,
        group_systems=group_systems,
        required_increase_tpa=target_tpa,
        max_roi_months=max_roi,
        distribution_strategy=distribution_strategy
    )

    result["em_summaries"] = {
        "steel_top_candidates": steel_candidates[:10],
        "steel_units_details": steel_plants,
        "ports_info": {
            "port_headroom_tpa": ports_info.get("port_headroom_tpa"),
            "current_throughput_mt": sum([p.get("current_throughput_mt", 0) for p in ports.get("ports_list", [])])
        },
        "port_units_details": ports.get("ports_list", []),
        "energy_info": {
            "energy_headroom_mw": energy_info.get("energy_headroom_mw"),
            "energy_available_mw": energy_info.get("energy_available_mw")
        },
        "energy_units_details": energy_info.get("energy_units_list", [])
    }

    result["query_constraints"] = constraints
    result["query"] = query
    return result
