"""
local_node.py

LOCAL Node: Simulates data ingestion from operational systems at each site.
Each port, steel plant, and power plant has LOCAL Nodes that collect real-time data
and transmit to their respective Enterprise Managers.
"""
import json
from datetime import datetime
from typing import Dict, Any

DATA_PATH = "mock_data.json"

def ingest_local_site(site_id: str = "Steel_Plant_SP1", path: str = DATA_PATH) -> Dict[str, Any]:
    """
    LOCAL Node function that collects operational data from site systems.
    
    In production, this would connect to:
    - Steel Plants: MES, SCADA, quality systems
    - Ports: TOS, VTMS, IoT sensors  
    - Power Plants: SCADA, DCS, fuel management systems
    
    Returns structured payload for Enterprise Manager processing.
    """
    with open(path, "r") as f:
        raw = json.load(f)

    now = datetime.utcnow().isoformat() + "Z"

    # Simulate different payloads based on site type
    if "Steel" in site_id or "SP" in site_id:
        ot_payload = {
            "site_id": site_id,
            "timestamp": now,
            "data_source": "Steel Plant LOCAL Node",
            "systems": {
                "MES": {"production_rates": "real-time", "downtime_logs": "current"},
                "SCADA": {"equipment_monitoring": "active", "process_control": "online"},
                "Quality_System": {"inspection_data": "updated"}
            },
            "operational_data": {
                "current_throughput_tph": 185,
                "energy_consumption_mw": 45.6,
                "raw_material_inventory": 12000,
                "equipment_availability": 0.94
            }
        }
    elif "Port" in site_id:
        ot_payload = {
            "site_id": site_id,
            "timestamp": now,
            "data_source": "Port LOCAL Node",
            "systems": {
                "TOS": {"berth_planning": "active", "yard_management": "online"},
                "VTMS": {"vessel_tracking": "real-time", "navigation_safety": "monitored"},
                "IoT_Sensors": {"crane_operations": "tracked", "gate_control": "automated"}
            },
            "operational_data": {
                "vessels_at_berth": 3,
                "crane_utilization": 0.78,
                "gate_throughput_trucks_hour": 45,
                "yard_occupancy_percent": 65
            }
        }
    elif "Power" in site_id or "PP" in site_id:
        ot_payload = {
            "site_id": site_id,
            "timestamp": now,
            "data_source": "Power Plant LOCAL Node",
            "systems": {
                "SCADA": {"turbine_control": "automated", "boiler_monitoring": "real-time"},
                "DCS": {"generation_control": "optimized", "safety_systems": "active"},
                "Fuel_Management": {"consumption_tracking": "live"}
            },
            "operational_data": {
                "current_generation_mw": 320,
                "plant_efficiency": 0.89,
                "fuel_consumption_rate": 45.2,
                "emissions_level": "within_limits"
            }
        }
    else:
        ot_payload = {
            "site_id": site_id,
            "timestamp": now,
            "data_source": "Generic LOCAL Node",
            "systems": {"SCADA": {"note": "telemetry_sample"}},
            "operational_data": {"status": "operational"}
        }

    return ot_payload

def transmit_to_enterprise_manager(site_data: Dict[str, Any], enterprise_manager: str) -> bool:
    """
    Simulates secure transmission of LOCAL Node data to the appropriate Enterprise Manager.
    
    In production, this would use:
    - TLS 1.3 encryption
    - Token-based authentication
    - Message queuing for resilience
    - Compression for efficiency
    """
    print(f"LOCAL Node {site_data['site_id']} transmitting to {enterprise_manager}...")
    
    # Simulate transmission logic
    if enterprise_manager in ["Steel_EM", "Ports_EM", "Energy_EM"]:
        print(f"✓ Successfully transmitted data to {enterprise_manager}")
        return True
    else:
        print(f"✗ Transmission failed: Invalid Enterprise Manager {enterprise_manager}")
        return False

# Example usage
if __name__ == "__main__":
    # Simulate LOCAL Node operation
    steel_data = ingest_local_site("Steel_Plant_SP1")
    transmit_to_enterprise_manager(steel_data, "Steel_EM")
    
    port_data = ingest_local_site("Port_A1")
    transmit_to_enterprise_manager(port_data, "Ports_EM")
    
    power_data = ingest_local_site("Power_Plant_PP1")
    transmit_to_enterprise_manager(power_data, "Energy_EM")
