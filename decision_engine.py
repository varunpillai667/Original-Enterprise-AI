# decision_engine.py
"""
Decision engine — considers:
- Steel plant distribution (0.8 / 0.6 / 0.4 / 0.2 MTPA)
- Port constraints (70% utilized, 1/3 group, 2/3 commercial protected)
- Power constraints (75% utilized, 3/4 grid protected)
- Financials, payback, confidence scoring
- No reduction in commercial cargo or grid supply
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# ----------------------
# CONSTANTS
# ----------------------
CAPEX_PER_MTPA_USD = 420_000_000
MARGIN_PER_TON_USD = 120
MW_PER_MTPA = 2.5
CARGO_TONNE_PER_STEEL_TONNE = 0.15

PORT_UTILIZATION = 0.70
PORT_GROUP_SHARE_OF_USED = 1/3

ENERGY_UTILIZATION = 0.75
ENERGY_GRID_SHARE_OF_USED = 3/4

START_CONFIDENCE = 85
MIN_CONFIDENCE = 70
MAX_PAYBACK_MONTHS = 36

DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]

MOCK_PATHS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/Original-Enterprise-AI/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"
CONCEPT_PDF = "/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf"

# ----------------------
# HELPERS
# ----------------------
def _energy_mw_for_mtpa(mtpa: float) -> float:
    """Energy requirement in MW."""
    return mtpa * MW_PER_MTPA

def _annual_margin(added_tpa: int) -> float:
    return added_tpa * MARGIN_PER_TON_USD

def _capex(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

# ----------------------
# LOAD MOCK
# ----------------------
def _load_mock() -> Dict[str, Any]:
    debug = []
    for p in MOCK_PATHS:
        try:
            if p.exists():
                debug.append(f"Loaded mock_data.json from {p}")
                return {"data": json.load(open(p)), "debug": debug}
        except Exception as e:
            debug.append(f"Failed loading {p}: {e}")

    debug.append("Using fallback defaults (mock_data.json not found).")
    return {
        "data": {
            "steel": {
                "plants": [
                    {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
                    {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
                    {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
                    {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
                ]
            },
            "ports": {
                "ports": [
                    {"id":"P1","capacity_tpa":2_000_000},
                    {"id":"P2","capacity_tpa":1_800_000},
                    {"id":"P3","capacity_tpa":1_600_000},
                    {"id":"P4","capacity_tpa":1_400_000},
                ]
            },
            "energy": {
                "plants": [
                    {"id":"E1","capacity_mw":500},
                    {"id":"E2","capacity_mw":450},
                    {"id":"E3","capacity_mw":400},
                ]
            }
        },
        "debug": debug
    }

# ----------------------
# PARSE QUERY
# ----------------------
def _parse(query: str):
    out = {
        "target_mtpa": 2.0,
        "target_months": 15,
        "max_payback_months": MAX_PAYBACK_MONTHS,
        "debug": []
    }
    q = query.lower()

    mt = re.search(r"(\d+(\.\d+)?)\s*mtpa", q)
    if mt:
        try: out["target_mtpa"] = float(mt.group(1))
        except: pass

    mo = re.search(r"(\d{1,3})\s*months?", q)
    if mo:
        try: out["target_months"] = int(mo.group(1))
        except: pass

    return out

# ----------------------
# MAIN SIMULATION
# ----------------------
def run_simulation(query: str) -> Dict[str, Any]:

    parsed = _parse(query)
    debug = parsed["debug"]

    # load data
    mock = _load_mock()
    data = mock["data"]
    debug += mock["debug"]

    # steel
    plants = data["steel"]["plants"]

    # ports
    ports = data["ports"]["ports"]
    total_port_capacity = sum(p["capacity_tpa"] for p in ports)
    used_port = PORT_UTILIZATION * total_port_capacity
    group_port = used_port * PORT_GROUP_SHARE_OF_USED
    spare_port = total_port_capacity - used_port
    available_port_for_steel = group_port + spare_port

    # energy
    energy_plants = data["energy"]["plants"]
    total_energy_capacity = sum(p["capacity_mw"] for p in energy_plants)
    used_energy = ENERGY_UTILIZATION * total_energy_capacity
    grid_energy = used_energy * ENERGY_GRID_SHARE_OF_USED
    group_energy = used_energy - grid_energy
    spare_energy = total_energy_capacity - used_energy
    available_energy_for_steel = group_energy + spare_energy

    # distribution
    added_tpa_list = [int(m * 1_000_000) for m in DISTRIBUTION_MTPA]

    breakdown = []
    total_added_tpa = 0
    total_capex = 0
    total_margin = 0

    for idx, plant in enumerate(plants[:4]):
        added = added_tpa_list[idx]
        mtpa = added / 1_000_000

        capex = _capex(mtpa)
        margin = _annual_margin(added)
        payback = (capex / margin) * 12 if margin > 0 else None

        breakdown.append({
            "id": plant["id"],
            "name": plant["name"],
            "current_capacity_tpa": plant["current_capacity_tpa"],
            "added_tpa": added,
            "new_capacity_tpa": plant["current_capacity_tpa"] + added,
            "capex_usd": int(capex),
            "annual_margin_usd": int(margin),
            "payback_months": None if payback is None else round(payback,1)
        })

        total_added_tpa += added
        total_capex += capex
        total_margin += margin

    total_added_mtpa = total_added_tpa / 1_000_000
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)
    port_required_tpa = int(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE)

    payback_months = (total_capex / total_margin) * 12 if total_margin > 0 else None

    # timeline
    planning = 2
    impl = max(6, int(6 + total_added_mtpa * 6))
    stab = max(1, int(impl * 0.2))
    total_months = planning + impl + stab

    # -------------------------
    # Confidence & constraints
    # -------------------------
    confidence = START_CONFIDENCE
    notes = []

    # port feasibility
    if port_required_tpa <= available_port_for_steel:
        notes.append("Ports: Sufficient spare + group allocation available.")
    else:
        notes.append(f"Port shortage: Need additional {port_required_tpa - available_port_for_steel:,} tpa.")
        confidence -= 20

    # energy feasibility
    if energy_required_mw <= available_energy_for_steel:
        notes.append("Energy: Sufficient spare + group allocation available.")
    else:
        notes.append(f"Energy shortage: Need additional {energy_required_mw - available_energy_for_steel:.1f} MW.")
        confidence -= 20

    # payback
    if payback_months and payback_months <= MAX_PAYBACK_MONTHS:
        notes.append(f"Payback meets requirement: {payback_months:.1f} months.")
    else:
        notes.append(f"Payback exceeds requirement: {payback_months:.1f} months.")
        confidence -= 15

    confidence = max(confidence, MIN_CONFIDENCE)

    return {
        "recommendation": {
            "headline": "Proposed Upgrade: +2.0 MTPA steel capacity across Group X Steel Division",
            "summary": f"Add {total_added_mtpa:.3f} MTPA across 4 plants.",
            "metrics": {
                "added_tpa": total_added_tpa,
                "added_mtpa": total_added_mtpa,
                "investment_usd": int(total_capex),
                "estimated_payback_months": None if payback_months is None else round(payback_months,1),
                "energy_required_mw": round(energy_required_mw,2),
                "confidence_pct": confidence,
            }
        },

        "roadmap": {
            "phases":[
                {"phase":"Planning","months":planning},
                {"phase":"Implementation","months":impl},
                {"phase":"Stabilization","months":stab},
            ],
            "per_plant_actions":[
                f"{p['name']}: add {p['added_tpa']:,} tpa (CapEx ${p['capex_usd']:,})"
                for p in breakdown
            ]
        },

        "rationale":{
            "bullets":notes,
            "assumptions":{
                "port_utilization":PORT_UTILIZATION,
                "energy_utilization":ENERGY_UTILIZATION,
                "cargo_factor":CARGO_TONNE_PER_STEEL_TONNE
            },
            "debug":debug,
            "references":{
                "operational_flow_doc":OPERATIONAL_FLOW_DOC,
                "concept_pdf":CONCEPT_PDF
            }
        },

        "em_summaries":{
            "steel_info":{"plant_distribution":breakdown},
            "ports_info":{"total_port_capacity_tpa":total_port_capacity},
            "energy_info":{"total_energy_capacity_mw":total_energy_capacity}
        }
    }
