"""
local_node.py
Simulates LOCAL Node behavior:
- Ingests raw data (mock_data.json)
- Performs light preprocessing
- Buffers data (returns structured dict)
No analytics. Matches architecture rules.
"""
import json
from datetime import datetime
from typing import Dict, Any

# FIXED — use project-relative path
DATA_PATH = "mock_data.json"

def ingest_data(path: str = DATA_PATH) -> Dict[str, Any]:
    with open(path, "r") as f:
        raw = json.load(f)

    now = datetime.utcnow().isoformat() + "Z"

    steel = []
    for p in raw.get("steel_plants", []):
        steel.append({
            "plant_id": p["plant_id"],
            "capacity": float(p["capacity"]),
            "utilization": float(p["utilization"]),
            "capex_estimate_usd": float(p["capex_estimate_usd"]),
            "roi_months": int(p["roi_months"])
        })

    energy = {
        "available_mw": float(raw["energy"]["available_mw"]),
        "cost_per_mw_usd": float(raw["energy"]["cost_per_mw_usd"])
    }

    ports = {
        "port2_capacity": float(raw["ports"]["port2_capacity"]),
        "current_utilization": float(raw["ports"]["current_utilization"])
    }

    return {
        "timestamp": now,
        "steel_plants": steel,
        "energy": energy,
        "ports": ports
    }
