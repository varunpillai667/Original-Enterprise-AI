# =========================
# File: decision_engine.py
# =========================
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List

# Executive decision engine with deterministic Option-A risk adjustments.
# Minimal comments (why only where needed).

# -------------------------
# Constants & baseline settings
# -------------------------
CAPEX_PER_MTPA_USD = 420_000_000
MARGIN_PER_TON_USD = 120
MW_PER_MTPA = 2.5
CARGO_TONNE_PER_STEEL_TONNE = 0.15

PORT_UTILIZATION = 0.70
PORT_GROUP_SHARE_OF_USED = 1.0 / 3.0
ENERGY_UTILIZATION = 0.75
ENERGY_GRID_SHARE_OF_USED = 3.0 / 4.0

START_CONFIDENCE = 88
MIN_CONFIDENCE = 40

USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]  # SP1..SP4

# Path to uploaded operational flow doc (kept for traceability)
OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"

# -------------------------
# Deterministic Option-A risk multipliers
# -------------------------
RISK_PROFILE = {
    "weather": {
        "procurement_delay_pct": 0.04,
        "implementation_delay_pct": 0.06,
        "commissioning_delay_pct": 0.03,
    },
    "supply_chain": {
        "procurement_delay_pct": 0.10,
        "capex_inflation_pct": 0.08,
        "implementation_delay_pct": 0.06,
    },
    "commodity": {
        "margin_down_pct": 0.10,
    },
    "geopolitics": {
        "shipping_delay_pct": 0.05,
        "oem_delivery_risk_pct": 0.04,
        "tariff_vol_pct": 0.05,
    },
    "ports": {
        "port_delay_pct": 0.04,
        "port_capacity_variation_pct": 0.06,
    },
    "energy": {
        "energy_availability_down_pct": 0.05,
        "energy_price_vol_pct": 0.07,
    },
    "inflation_finance": {
        "equipment_inflation_pct": 0.07,
        "labor_inflation_pct": 0.05,
        "finance_spread_pct": 0.01,
    },
    "contractor": {
        "implementation_delay_pct": 0.05,
    }
}

# -------------------------
# Helpers
# -------------------------
def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

CANDIDATE_MOCKS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

def _load_mock_data() -> Dict[str, Any]:
    debug: List[str] = []
    for p in CANDIDATE_MOCKS:
        try:
            if p.exists():
                with open(p, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                debug.append(f"Loaded mock_data.json from {p}")
                return {"data": data, "debug": debug, "path": str(p)}
        except Exception as exc:
            debug.append(f"Failed to load {p}: {exc}")
    debug.append("No mock_data.json found; using built-in defaults.")
    defaults = {
        "steel": {"plants": [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]},
        "ports": {"ports": [
            {"id":"P1","capacity_tpa":2_000_000},
            {"id":"P2","capacity_tpa":1_800_000},
            {"id":"P3","capacity_tpa":1_600_000},
            {"id":"P4","capacity_tpa":1_400_000},
        ]},
        "energy": {"plants": [
            {"id":"E1","capacity_mw":500},
            {"id":"E2","capacity_mw":450},
            {"id":"E3","capacity_mw":400},
        ]}
    }
    return {"data": defaults, "debug": debug, "path": None}

def _parse_query(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    out = {"target_mtpa": None, "target_months": None, "max_payback_months": None, "debug": []}
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            out["target_mtpa"] = float(m.group(1))
        except:
            out["debug"].append("Failed parsing target MTPA.")
    mm = re.search(r'(\d{1,3})\s*(?:months|month)', q)
    if mm:
        try:
            out["target_months"] = int(mm.group(1))
        except:
            out["debug"].append("Failed parsing months.")
    pp = re.search(r'payback.*?(?:less than|within|<)\s*(\d+)\s*(years|year)', q)
    if pp:
        try:
            out["max_payback_months"] = int(pp.group(1)) * 12
        except:
            out["debug"].append("Failed parsing payback.")
    return out

def _aggregate_risk_factors() -> Dict[str, float]:
    p = RISK_PROFILE
    procurement_delay_pct = (
        p["weather"]["procurement_delay_pct"]
        + p["supply_chain"]["procurement_delay_pct"]
        + p["geopolitics"]["shipping_delay_pct"]
    )
    implementation_delay_pct = (
        p["weather"]["implementation_delay_pct"]
        + p["supply_chain"]["implementation_delay_pct"]
        + p["contractor"]["implementation_delay_pct"]
    )
    commissioning_delay_pct = p["weather"]["commissioning_delay_pct"]
    capex_inflation_pct = p["supply_chain"]["capex_inflation_pct"] + p["inflation_finance"]["equipment_inflation_pct"]
    margin_down_pct = p["commodity"]["margin_down_pct"] + p["energy"]["energy_price_vol_pct"] * 0.5
    energy_availability_down_pct = p["energy"]["energy_availability_down_pct"]
    port_availability_down_pct = p["ports"]["port_delay_pct"]
    return {
        "procurement_delay_pct": procurement_delay_pct,
        "implementation_delay_pct": implementation_delay_pct,
        "commissioning_delay_pct": commissioning_delay_pct,
        "capex_inflation_pct": capex_inflation_pct,
        "margin_down_pct": margin_down_pct,
        "energy_availability_down_pct": energy_availability_down_pct,
        "port_availability_down_pct": port_availability_down_pct,
    }

def run_simulation(query: str) -> Dict[str, Any]:
    parsed = _parse_query(query)
    debug: List[str] = parsed.get("debug", [])

    loaded = _load_mock_data()
    data = loaded.get("data", {})
    debug += loaded.get("debug", [])
    if loaded.get("path"):
        debug.append(f"Using mock file: {loaded.get('path')}")

    plants = (data.get("steel") or {}).get("plants") or []
    ports = (data.get("ports") or {}).get("ports") or []
    energy_plants = (data.get("energy") or {}).get("plants") or []

    if len(plants) < 4:
        plants = [
            {"id":"SP1","name":"Steel Plant 1","current_capacity_tpa":1_200_000},
            {"id":"SP2","name":"Steel Plant 2","current_capacity_tpa":900_000},
            {"id":"SP3","name":"Steel Plant 3","current_capacity_tpa":700_000},
            {"id":"SP4","name":"Steel Plant 4","current_capacity_tpa":600_000},
        ]

    if not ports:
        ports = [
            {"id":"P1","capacity_tpa":2_000_000},
            {"id":"P2","capacity_tpa":1_800_000},
            {"id":"P3","capacity_tpa":1_600_000},
            {"id":"P4","capacity_tpa":1_400_000},
        ]

    if not energy_plants:
        energy_plants = [
            {"id":"E1","capacity_mw":500},
            {"id":"E2","capacity_mw":450},
            {"id":"E3","capacity_mw":400},
        ]

    total_port_capacity = sum(int(p.get("capacity_tpa", 0)) for p in ports)
    used_port = PORT_UTILIZATION * total_port_capacity
    group_port_share = used_port * PORT_GROUP_SHARE_OF_USED
    spare_port = total_port_capacity - used_port
    available_port_for_steel = spare_port + group_port_share

    total_energy_capacity = sum(float(e.get("capacity_mw", 0)) for e in energy_plants)
    used_energy = ENERGY_UTILIZATION * total_energy_capacity
    grid_energy_share = used_energy * ENERGY_GRID_SHARE_OF_USED
    group_energy_share = used_energy - grid_energy_share
    spare_energy = total_energy_capacity - used_energy
    available_energy_for_steel = spare_energy + group_energy_share

    num_plants = min(4, len(plants))
    dist_mtpa = USER_DISTRIBUTION_MTPA[:num_plants]
    added_tpa_list = [int(round(m * 1_000_000)) for m in dist_mtpa]

    breakdown: List[Dict[str, Any]] = []
    total_added_tpa = 0
    base_capex = 0.0
    base_margin = 0.0

    for idx in range(num_plants):
        p = plants[idx]
        added = added_tpa_list[idx]
        mtpa_added = added / 1_000_000.0
        capex = _capex_for_mtpa(mtpa_added)
        margin = _annual_margin_for_tpa(added)
        payback_months = None if margin == 0 else (capex / margin) * 12.0
        hires_units = max(1, int(round(mtpa_added * 10)))
        breakdown.append({
            "id": p.get("id"),
            "name": p.get("name", p.get("id", "")),
            "current_capacity_tpa": int(p.get("current_capacity_tpa", 0)),
            "added_tpa": int(added),
            "added_mtpa": round(mtpa_added, 3),
            "new_capacity_tpa": int(p.get("current_capacity_tpa", 0) + added),
            "capex_usd": int(round(capex)),
            "annual_margin_usd": int(round(margin)),
            "base_payback_months": None if payback_months is None else round(payback_months, 1),
            "hiring_estimate": {
                "operators": hires_units * 5,
                "maintenance": hires_units * 2,
                "engineers": hires_units * 1,
                "project_managers": 1
            }
        })
        total_added_tpa += added
        base_capex += capex
        base_margin += margin

    total_added_mtpa = total_added_tpa / 1_000_000.0
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)
    port_required_tpa = int(round(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE))

    planning = 3
    procurement_base = max(2, int(round(2 + total_added_mtpa * 4)))
    implementation_base = max(3, int(round(4 + total_added_mtpa * 6)))
    commissioning_base = max(1, int(round(implementation_base * 0.25)))
    stabilization_base = max(1, int(round(commissioning_base * 0.5)))
    estimated_total_months_base = planning + procurement_base + implementation_base + commissioning_base + stabilization_base

    risk = _aggregate_risk_factors()
    procurement_delay_pct = risk["procurement_delay_pct"]
    implementation_delay_pct = risk["implementation_delay_pct"]
    commissioning_delay_pct = risk["commissioning_delay_pct"]
    capex_inflation_pct = risk["capex_inflation_pct"]
    margin_down_pct = risk["margin_down_pct"]
    energy_avail_down_pct = risk["energy_availability_down_pct"]
    port_avail_down_pct = risk["port_availability_down_pct"]

    procurement_adj = max(1, int(round(procurement_base * (1 + procurement_delay_pct))))
    implementation_adj = max(1, int(round(implementation_base * (1 + implementation_delay_pct))))
    commissioning_adj = max(1, int(round(commissioning_base * (1 + commissioning_delay_pct))))
    stabilization_adj = max(1, int(round(stabilization_base * (1 + commissioning_delay_pct * 0.5))))
    estimated_total_months_risk = planning + procurement_adj + implementation_adj + commissioning_adj + stabilization_adj

    risk_adj_capex = base_capex * (1 + capex_inflation_pct)
    risk_adj_margin = base_margin * (1 - margin_down_pct)
    aggregated_payback_months_risk = None
    if risk_adj_margin > 0:
        aggregated_payback_months_risk = (risk_adj_capex / risk_adj_margin) * 12.0

    available_energy_for_steel_risk = max(0.0, available_energy_for_steel * (1 - energy_avail_down_pct))
    available_port_for_steel_risk = max(0.0, available_port_for_steel * (1 - port_avail_down_pct))

    validations = {"checks": [], "passed": True}
    if parsed.get("target_mtpa") is not None:
        target_mtpa = parsed["target_mtpa"]
        if abs(total_added_mtpa - target_mtpa) / max(1e-9, target_mtpa) <= 0.02:
            validations["checks"].append({"name": "Target MTPA", "status": "pass", "detail": f"Added {total_added_mtpa:.3f} MTPA meets requested {target_mtpa} MTPA"})
        else:
            validations["checks"].append({"name": "Target MTPA", "status": "fail", "detail": f"Added {total_added_mtpa:.3f} MTPA does not match requested {target_mtpa} MTPA"})
            validations["passed"] = False

    if parsed.get("max_payback_months") is not None and aggregated_payback_months_risk is not None:
        if aggregated_payback_months_risk <= parsed["max_payback_months"]:
            validations["checks"].append({"name": "Payback", "status": "pass", "detail": f"Risk-adjusted payback {aggregated_payback_months_risk:.1f} months <= requested {parsed['max_payback_months']} months"})
        else:
            validations["checks"].append({"name": "Payback", "status": "fail", "detail": f"Risk-adjusted payback {aggregated_payback_months_risk:.1f} months exceeds requested {parsed['max_payback_months']} months"})
            validations["passed"] = False

    if energy_required_mw <= available_energy_for_steel_risk + 1e-9:
        validations["checks"].append({"name": "Energy", "status": "pass", "detail": f"Needs {energy_required_mw:.2f} MW; available {available_energy_for_steel_risk:.2f} MW after risk adjustments"})
    else:
        validations["checks"].append({"name": "Energy", "status": "fail", "detail": f"Needs {energy_required_mw:.2f} MW; available {available_energy_for_steel_risk:.2f} MW after risk adjustments"})
        validations["passed"] = False

    if port_required_tpa <= available_port_for_steel_risk + 1e-9:
        validations["checks"].append({"name": "Ports", "status": "pass", "detail": f"Requires {port_required_tpa:,} tpa; available {int(available_port_for_steel_risk):,} tpa after risk adjustments"})
    else:
        validations["checks"].append({"name": "Ports", "status": "fail", "detail": f"Requires {port_required_tpa:,} tpa; available {int(available_port_for_steel_risk):,} tpa after risk adjustments"})
        validations["passed"] = False

    per_plant_schedule = []
    sorted_breakdown = sorted(breakdown, key=lambda x: x.get("capex_usd", 0), reverse=True)
    offset = 0
    for p in sorted_breakdown:
        share = p["added_tpa"] / (total_added_tpa or 1)
        proc = max(1, int(round(procurement_adj * share)))
        impl = max(1, int(round(implementation_adj * share)))
        comm = max(1, int(round(commissioning_adj * share)))
        start = offset + 1
        online = start + proc + impl + comm
        per_plant_schedule.append({
            "plant": p["name"],
            "start_month_planning": start,
            "procurement_window_months": proc,
            "implementation_window_months": impl,
            "commissioning_window_months": comm,
            "expected_online_month": online
        })
        offset += max(1, int(round(impl * 0.5)))

    actions = [
        "Phase A (ROI-first): Target highest-ROI plants with automation & modular cells to accelerate early cash flow.",
        "Lock long-lead equipment via frame contracts and pre-paying options to mitigate supply-chain delays.",
        "Negotiate short-term PPAs and add WHR / battery buffering to improve energy certainty during ramp.",
        "Reserve temporary berth capacity and 3PL arrangements to protect commercial cargo SLAs during peak imports.",
        "Create a PMO with risk gates and contingency budget for commodity price volatility.",
    ]

    rationale_bullets: List[str] = []
    rationale_bullets.append("Staging (Phase A) reduces capital at-risk and accelerates earliest cash generation.")
    rationale_bullets.append("Frame contracts + supplier pre-qualification reduce procurement critical-path uncertainty.")
    rationale_bullets.append("Energy program (PPAs + WHR) lowers exposure to grid shortfalls and tariff shocks, shortening payback.")
    rationale_bullets.append("Logistics & port leasing protects commercial throughput while enabling increased raw-material flow.")
    rationale_bullets.append("Risk adjustments applied: procurement, implementation and capex inflation; these drive the risk-adjusted timeline & payback.")

    for chk in validations["checks"]:
        status = chk["status"].upper()
        rationale_bullets.append(f"Validation — {chk['name']}: {status} — {chk['detail']}")

    mitigations: List[str] = []
    for chk in validations["checks"]:
        if chk["status"] == "fail":
            if chk["name"] == "Payback":
                mitigations.append("Staged capex, renegotiate pricing, or increase product margin via premium SKUs.")
            if chk["name"] == "Energy":
                mitigations.append("Secure short-term PPA, deploy temporary generation or reduce peak loads via process tuning.")
            if chk["name"] == "Ports":
                mitigations.append("Contract 3PL, lease temporary berth capacity, or stage material arrivals.")
            if chk["name"] == "Schedule":
                mitigations.append("Parallelize engineering and procurement, add installation crews, accept phased delivery.")
            if chk["name"] == "Target MTPA":
                mitigations.append("Redistribute increases or accept phased completion to meet timeline.")

    if mitigations:
        rationale_bullets.append("Mitigations / Alternatives:")
        rationale_bullets += mitigations

    confidence = START_CONFIDENCE
    for chk in validations["checks"]:
        if chk["status"] == "fail":
            confidence -= 12
    confidence -= int(round(risk["capex_inflation_pct"] * 10))
    confidence -= int(round(risk["margin_down_pct"] * 10))
    confidence = max(confidence, MIN_CONFIDENCE)

    result = {
        "recommendation": {
            "headline": f"Risk-adjusted recommendation: +{total_added_mtpa:.3f} MTPA (staged, ROI-first)",
            "summary": f"Prioritize ROI-first Phase A to generate early cash flow; apply procurement and energy mitigations to protect schedule and payback.",
            "metrics": {
                "added_mtpa": round(total_added_mtpa, 3),
                "investment_usd_base": int(round(base_capex)),
                "investment_usd_risk_adjusted": int(round(risk_adj_capex)),
                "estimated_payback_months_base": None if base_margin == 0 else round((base_capex / base_margin) * 12.0, 1),
                "estimated_payback_months_risk": None if risk_adj_margin == 0 else round(aggregated_payback_months_risk, 1),
                "energy_required_mw": round(energy_required_mw, 2),
                "port_throughput_required_tpa": int(port_required_tpa),
            },
            "actions": actions,
            "distribution": [{"plant": d["name"], "added_mtpa": d["added_mtpa"], "capex_usd": d["capex_usd"], "base_payback_months": d["base_payback_months"]} for d in breakdown]
        },
        "roadmap": {
            "phases": [
                {"phase": "Planning", "months_base": planning, "months_risk": planning, "notes": "Engineering, permits, PMO setup"},
                {"phase": "Procurement", "months_base": procurement_base, "months_risk": procurement_adj, "notes": "Frame contracts, long-lead orders"},
                {"phase": "Implementation", "months_base": implementation_base, "months_risk": implementation_adj, "notes": "Installation & integration"},
                {"phase": "Commissioning", "months_base": commissioning_base, "months_risk": commissioning_adj, "notes": "Cold / hot commissioning"},
                {"phase": "Stabilization", "months_base": stabilization_base, "months_risk": stabilization_adj, "notes": "Ramp & optimization"},
            ],
            "per_plant_schedule": per_plant_schedule,
            "estimated_total_months_base": estimated_total_months_base,
            "estimated_total_months_risk": estimated_total_months_risk
        },
        "rationale": {"bullets": rationale_bullets},
        "validations": validations,
        "metrics": {
            "total_capex_usd_base": int(round(base_capex)),
            "total_capex_usd_risk": int(round(risk_adj_capex)),
            "total_annual_margin_usd_base": int(round(base_margin)),
            "total_annual_margin_usd_risk": int(round(risk_adj_margin)),
            "aggregated_payback_months_risk": None if aggregated_payback_months_risk is None else round(aggregated_payback_months_risk, 1),
            "energy_required_mw": round(energy_required_mw, 2),
            "available_energy_for_steel_risk_mw": round(available_energy_for_steel_risk, 2),
            "port_required_tpa": int(port_required_tpa),
            "available_port_for_steel_risk_tpa": int(available_port_for_steel_risk),
            "estimated_total_months_risk": estimated_total_months_risk,
        },
        "em_summaries": {
            "steel_info": {"plant_distribution": breakdown},
            "ports_info": {"total_port_capacity_tpa": total_port_capacity, "used_port_tpa": int(used_port)},
            "energy_info": {"total_energy_capacity_mw": total_energy_capacity, "used_energy_mw": used_energy},
        },
        "confidence_pct": max(0, int(round(confidence))),
        "notes": {"debug": debug, "operational_flow_doc": OPERATIONAL_FLOW_DOC}
    }

    return result

if __name__ == "__main__":
    q = "What is the recommended approach for increasing Group X’s steel production by approximately 2 MTPA, including the upgrades required, expected investment, timeline and estimated payback?"
    import pprint
    pprint.pprint(run_simulation(q))
