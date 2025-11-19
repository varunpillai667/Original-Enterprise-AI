"""
local_node.py

LOCAL Node responsibilities:
- Ingest OT system feeds from ports & plants (SCADA, DCS, MES, TOS)
- Light preprocess (validate, timestamp, normalize)
- Annotate payload for Enterprise Managers (no analytics here)
"""
import json
from datetime import datetime
from typing import Dict, Any

DATA_PATH = "mock_data.json"

def ingest_local_site(site_id: str = "Site-1", path: str = DATA_PATH) -> Dict[str, Any]:
    with open(path, "r") as f:
        raw = json.load(f)

    now = datetime.utcnow().isoformat() + "Z"

    ot_payload = {
        "site_id": site_id,
        "timestamp": now,
        "systems": {
            "SCADA": {"note": "turbine/boiler telemetry (sample)"},
            "MES": {"note": "production rates & downtime (sample)"},
            "TOS": {"note": "terminal yard stats (sample)"}
        },
        "steel_plants": raw.get("steel_plants", []),
        "energy": raw.get("energy", {}),
        "ports": raw.get("ports", {})
    }

    return ot_payload
