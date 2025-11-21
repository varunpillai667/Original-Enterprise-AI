# local_node.py
"""
Local Node simulation helpers (mock).

Provides:
- ingest_local_site(site_id: str) -> Dict[str, Any]
- transmit_to_enterprise_manager(payload: dict, enterprise_manager: str) -> bool

These are simple stubs to illustrate local node behaviour.
"""

from typing import Dict, Any
import random


def ingest_local_site(site_id: str) -> Dict[str, Any]:
    """Return a sample site payload. In real deployments this would read sensors/OT data."""
    # simple mock data
    if site_id.lower().startswith("port"):
        return {
            "site_id": site_id,
            "type": "port",
            "throughput_tpa": random.randint(200_000, 2_000_000),
            "status": "ok",
        }
    if site_id.lower().startswith("steel"):
        return {
            "site_id": site_id,
            "type": "steel",
            "current_capacity_tpa": random.randint(400_000, 1_300_000),
            "utilization_pct": round(random.uniform(0.6, 0.95), 2),
            "status": "ok",
        }
    if site_id.lower().startswith("power"):
        return {
            "site_id": site_id,
            "type": "power",
            "available_mw": random.randint(100, 600),
            "status": "ok",
        }
    return {"site_id": site_id, "type": "unknown", "status": "ok"}


def transmit_to_enterprise_manager(payload: Dict[str, Any], enterprise_manager: str) -> bool:
    """
    Mock transmit: validate payload and pretend to send to EM.
    Returns True on success.
    """
    if not isinstance(payload, dict) or not enterprise_manager:
        return False
    # basic validation
    if "site_id" not in payload:
        return False
    # in real system would perform encryption, buffering, retries
    return True


# Quick demo if run directly
if __name__ == "__main__":
    print(ingest_local_site("Steel_SP1"))
    print(ingest_local_site("Port_P1"))
    print(transmit_to_enterprise_manager({"site_id": "Steel_SP1"}, "Steel_EM"))
