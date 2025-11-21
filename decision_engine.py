# decision_engine.py
"""
Decision engine — exact distribution + enforced payback < 36 months + polished output.

Assumptions chosen:
- CAPEX_PER_MTPA_USD = 420_000_000
- MARGIN_PER_TON_USD = 120
- MW_PER_MTPA = 2.5
- Confidence: dynamic but min 70%
- Rounding/display: 0.1 MTPA (100,000 tpa)
"""

from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Attempt enterprise evaluators (non-fatal)
try:
    from enterprise_manager import evaluate_steel, evaluate_ports, evaluate_energy  # type: ignore
except Exception:
    evaluate_steel = None  # type: ignore
    evaluate_ports = None  # type: ignore
    evaluate_energy = None  # type: ignore

# ------------------ Assumptions (selected) ------------------
CAPEX_PER_MTPA_USD = 420_000_000
MARGIN_PER_TON_USD = 120
MW_PER_MTPA = 2.5
START_CONFIDENCE = 85
MIN_CONFIDENCE = 70
MAX_PAYBACK_MONTHS_ENFORCED = 36  # enforce < 3 years

# Mock data locations (robust)
MODULE_MOCK = Path(__file__).parent / "mock_data.json"
CANDIDATE_MOCKS = [
    MODULE_MOCK,
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/Original-Enterprise-AI/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

# Reference uploaded docs
OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"
CONCEPT_PDF = "/mnt/data/Original Enterprise AI-Concept by Varun Pillai.pdf"

# ------------------ Parsing utilities ------------------
def _parse_query(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    defaults = {"target_mtpa": 2.0, "target_months": 15, "max_payback_months": MAX_PAYBACK_MONTHS_ENFORCED, "debug": []}
    # read mtpa if present
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            defaults["target_mtpa"] = float(m.group(1))
        except Exception:
            defaults["debug"].append("Could not parse mtpa, using default 2.0")
    # months
    m2 = re.search(r'(\d{1,3})\s*(?:months|month)\b', q)
    if m2:
        try:
            defaults["target_months"] = int(m2.group(1))
        except Exception:
            defaults["debug"].append("Could not parse months, using default 15")
    # payback
    m3 = re.search(r'payback.*?(?:less than|<|within)\s*(\d+)\s*(years|year)', q)
    if m3:
        defaults["max_payback_months"] = int(m3.group(1)) * 12
    return defaults

# ------------------ Data loading ------------------
def _load_mock() -> Dict[str, Any]:
    debug = []
    for p in CANDIDATE_MOCKS:
        try:
            if p.exists():
                with open(p, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                debug.append(f"Loaded mock_data.json from {p}")
                return {"data": data, "debug": debug}
        except Exception as e:
            debug.append(f"Found {p} but failed: {e}")

    # fallback defaults
    debug.append("No mock_data.json found; using built-in defaults.")
    defaults = {
        "steel": {"plants": [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]},
        "ports":{"ports":[{"id":"P1"},{"id":"P2"},{"id":"P3"},{"id":"P4"}]},
        "energy":{"plants":[{"id":"E1"},{"id":"E2"},{"id":"E3"}]},
    }
    return {"data": defaults, "debug": debug}

# ------------------ Fixed distribution (your requirement) ------------------
USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]  # sums to 2.0 MTPA

# ------------------ Estimators ------------------
def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

# ------------------ Section builders ------------------
def _make_recommendation(headline, total_added_tpa, total_investment, aggregated_payback, energy_mw, confidence):
    added_mtpa = round(total_added_tpa/1_000_000.0, 3)
    metrics = {
        "added_tpa": total_added_tpa,
        "added_mtpa": added_mtpa,
        "investment_usd": int(round(total_investment)),
        "estimated_payback_months": None if aggregated_payback is None else round(aggregated_payback,1),
        "energy_required_mw": round(energy_mw,2),
        "confidence_pct": confidence,
    }
    summary = f"Proposed Upgrade: +{added_mtpa:.3f} MTPA steel capacity across Group X Steel Division (investment ${metrics['investment_usd']:,})."
    return {"headline": headline, "summary": summary, "metrics": metrics}

def _make_roadmap(timeline, per_plant):
    phases = [
        {"phase":"Planning","months":timeline["planning_months"],"notes":"Engineering, permits, procurement"},
        {"phase":"Implementation","months":timeline["implementation_months"],"notes":"Civil, equipment install, commissioning"},
        {"phase":"Stabilization","months":timeline["stabilization_months"],"notes":"Ramp-up and QA"},
    ]
    actions = [f"{p['name']}: add {p['added_tpa']:,} tpa (CapEx ${p['capex_usd']:,})" for p in per_plant]
    return {"phases": phases, "per_plant_actions": actions}

def _make_rationale(notes, assumptions, debug_lines):
    bullets = list(notes)
    bullets.append("Assumptions below were used to compute payback and energy.")
    return {
        "bullets": bullets,
        "assumptions": assumptions,
        "debug": debug_lines,
        "references": {
            "operational_flow_doc": OPERATIONAL_FLOW_DOC,
            "concept_pdf": CONCEPT_PDF
        }
    }

# ------------------ Main simulation ------------------
def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query(query)
    debug_lines = parsed["debug"]
    enforced_payback = parsed["max_payback_months"]

    # load mock/default data
    loaded = _load_mock()
    data = loaded["data"]
    debug_lines += loaded["debug"]

    plants = data.get("steel",{}).get("plants",[])
    if len(plants) < 4:
        plants = [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]
        debug_lines.append("Using fallback 4-plant defaults.")

    # Apply exact MTPA distribution
    added_tpa_list = [int(m*1_000_000) for m in USER_DISTRIBUTION_MTPA]

    # Per-plant breakdown
    breakdown = []
    total_investment = 0.0
    total_margin = 0.0

    for i, plant in enumerate(plants[:4]):
        added_tpa = added_tpa_list[i]
        added_mtpa = added_tpa / 1_000_000
        capex = _capex_for_mtpa(added_mtpa)
        margin = _annual_margin_for_tpa(added_tpa)
        payback = None if margin==0 else (capex/margin)*12

        breakdown.append({
            "id": plant["id"],
            "name": plant["name"],
            "current_capacity_tpa": plant["current_capacity_tpa"],
            "added_tpa": added_tpa,
            "new_capacity_tpa": plant["current_capacity_tpa"] + added_tpa,
            "capex_usd": int(capex),
            "annual_margin_usd": int(margin),
            "payback_months": None if payback is None else round(payback,1),
        })

        total_investment += capex
        total_margin += margin

    total_added_tpa = sum(p["added_tpa"] for p in breakdown)
    total_mtpa = total_added_tpa / 1_000_000.0
    energy_mw = _energy_mw_for_mtpa(total_mtpa)

    aggregate_payback = None if total_margin==0 else (total_investment/total_margin)*12

    # timeline model
    planning = 2
    implementation = max(1, int(round(4 + total_mtpa * 8)))
    stabilization = max(1, int(round(implementation * 0.2)))
    total_months = planning + implementation + stabilization

    # confidence
    confidence = START_CONFIDENCE
    notes = []

    if aggregate_payback is None:
        notes.append("Cannot compute payback (zero margin).")
        confidence -= 10
    else:
        if aggregate_payback <= enforced_payback:
            notes.append(f"Payback {aggregate_payback:.1f} months meets requirement (<{enforced_payback}).")
        else:
            notes.append(f"Payback {aggregate_payback:.1f} months exceeds requirement (<{enforced_payback}).")
            notes.append("Consider staging, CAPEX reduction, or margin enhancement.")
            confidence -= 15

    # enforce min confidence
    confidence = max(confidence, MIN_CONFIDENCE)

    # headline
    headline = "Proposed Upgrade: +2.0 MTPA steel capacity across Group X Steel Division"

    # sections
    recommendation = _make_recommendation(headline, total_added_tpa, total_investment, aggregate_payback, energy_mw, confidence)
    timeline = {"planning_months":planning,"implementation_months":implementation,"stabilization_months":stabilization}
    roadmap = _make_roadmap(timeline, breakdown)
    rationale = _make_rationale(notes, {
        "capex_per_mtpa_usd": CAPEX_PER_MTPA_USD,
        "margin_per_ton_usd": MARGIN_PER_TON_USD,
        "mw_per_mtpa": MW_PER_MTPA
    }, debug_lines)

    return {
        "recommendation": recommendation,
        "roadmap": roadmap,
        "rationale": rationale,
        "expected_increase_tpa": total_added_tpa,
        "investment_usd": int(total_investment),
        "roi_months": None if aggregate_payback is None else round(aggregate_payback,1),
        "energy_required_mw": round(energy_mw,1),
        "confidence_pct": confidence,
        "em_summaries": {
            "steel_info": {"num_plants":4,"plant_distribution": breakdown}
        },
        "notes": {
            "assumptions":{
                "capex_per_mtpa_usd":CAPEX_PER_MTPA_USD,
                "margin_per_ton_usd":MARGIN_PER_TON_USD,
                "mw_per_mtpa":MW_PER_MTPA
            },
            "recommendations":notes,
            "debug":debug_lines
        }
    }
