"""
local_node.py
Simulates LOCAL Node responsibilities:
- Ingests raw operational data (reads mock_data.json)
- Performs light preprocessing: validation, timestamping, simple normalization
- Buffers data (here: returns structured dict for EM)
This node does NOT perform analytics or model inference; it prepares data for the Enterprise Manager.
"""
import json
from datetime import datetime
from typing import Dict, Any

DATA_PATH = "/mnt/data/mock_data.json"

def ingest_data(path: str = DATA_PATH) -> Dict[str, Any]:
    with open(path, "r") as f:
        raw = json.load(f)
    # Basic validation and light preprocessing
    now = datetime.utcnow().isoformat() + "Z"
    # Normalize keys and ensure numeric types
    steel = []
    for p in raw.get("steel_plants", []):
        steel.append({
            "plant_id": p.get("plant_id"),
            "capacity": float(p.get("capacity", 0)),
            "utilization": float(p.get("utilization", 0)),
            "capex_estimate_usd": float(p.get("capex_estimate_usd", 0)),
            "roi_months": int(p.get("roi_months", 0))
        })
    energy = {
        "available_mw": float(raw.get("energy", {}).get("available_mw", 0)),
        "cost_per_mw_usd": float(raw.get("energy", {}).get("cost_per_mw_usd", 0))
    }
    ports = {
        "port2_capacity": float(raw.get("ports", {}).get("port2_capacity", 0)),
        "current_utilization": float(raw.get("ports", {}).get("current_utilization", 0))
    }
    return {
        "timestamp": now,
        "steel_plants": steel,
        "energy": energy,
        "ports": ports
    }
