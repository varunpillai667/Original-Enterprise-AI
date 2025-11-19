"""
local_node.py

LOCAL Node responsibilities (lightweight, no analytics):
- Ingest OT system feeds from ports & plants (SCADA, DCS, MES, TOS)
- Light preprocess (validate, timestamp, normalize)
- Tag data with source metadata and forward to Enterprise Manager
"""
import json
from datetime import datetime
from typing import Dict, Any

DATA_PATH = "mock_data.json"

def ingest_local_site(site_id: str = "Site-1", path: str = DATA_PATH) -> Dict[str, Any]:
    """
    Simulate reading OT system data for a local site and returning
    a structured payload annotated with source info.
    """
    with open(path, "r") as f:
        raw = json.load(f)

    now = datetime.utcnow().isoformat() + "Z"

    # Example OT telemetry (taken from mock data for demo purposes)
    # Tag every field with the originating OT system in the 'sources' field
    ot_payload = {
        "site_id": site_id,
        "timestamp": now,
        "systems": {
            "SCADA": {"note": "turbine/boiler telemetry (sample)", "sample_values": {"temp": 350}},
            "MES": {"note": "production rates & downtime (sample)", "sample_values": {"rate": 120}},
            "TOS": {"note": "terminal yard stats (sample)", "sample_values": {"throughput": 450}}
        },
        # For demo, include small slices of mock_data so EMs can use realistic numbers
        "steel_plants": raw.get("steel_plants", []),
        "energy": raw.get("energy", {}),
        "ports": raw.get("ports", {}),
        "source": "LOCAL_NODE"
    }

    return ot_payload
