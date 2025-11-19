"""
local_node.py

LOCAL Node: ingest mock OT telemetry and forward structured payload to EMs.
"""
import json
from datetime import datetime
from typing import Dict, Any

DATA_PATH = "mock_data.json"

def ingest_local_site(site_id: str = "Port+Plant-Site", path: str = DATA_PATH) -> Dict[str, Any]:
    with open(path, "r") as f:
        raw = json.load(f)

    now = datetime.utcnow().isoformat() + "Z"

    ot_payload = {
        "site_id": site_id,
        "timestamp": now,
        "systems": {
            "SCADA": {"note": "telemetry sample"},
            "MES": {"note": "production sample"},
            "TOS": {"note": "terminal sample"}
        },
        "steel_plants": raw.get("steel_plants", []),
        "energy": raw.get("energy", {}),
        "ports": raw.get("ports", {})
    }

    return ot_payload
