# =========================
# File: decision_engine.py
# =========================
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List

# Executive decision engine with realistic external/internal factor handling.
# Output is a single, plain result (no debug traces, no "risk-adjusted" wording).

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

USER_DISTRIBUTION_MTPA = [0.8, 0.6, 0.4, 0.2]  # distribution across 4 plants

OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"

# Deterministic Option-A risk multipliers (used internally; not exposed)
RISK_PROFILE = {
    "weather": {"procurement_delay_pct": 0.04, "implementation_delay_pct": 0.06, "commissioning_delay_pct": 0.03},
    "supply_chain": {"procurement_delay_pct": 0.10, "capex_inflation_pct": 0.08, "implementation_delay_pct": 0.06},
    "commodity": {"margin_down_pct": 0.10},
    "geopolitics": {"shipping_delay_pct": 0.05},
    "ports": {"port_delay_pct": 0.04},
    "energy": {"energy_availability_down_pct": 0.05, "energy_price_vol_pct": 0.07},
    "inflation_finance": {"equipment_inflation_pct": 0.07, "labor_inflation_pct": 0.05},
    "contractor": {"implementation_delay_pct": 0.05},
}

# Defensive mock-data paths
CANDIDATE_MOCKS = [
    Path(__file__).parent / "mock_data.json",
    Path("/mnt/data/Original-Enterprise-AI-main/mock_data.json"),
    Path("/mnt/data/mock_data.json"),
]

def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

def _load_mock_data() -> Dict[str, Any]:
    for p in CANDIDATE_MOCKS:
        try:
            if p.exists():
                with open(p, "r", encoding="utf-8") as fh:
                    return {"data": json.load(fh)}
        except Exception:
            pass
    # defaults
    return {"data": {
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
    }}

def _parse_query(query: str) -> Dict[str, Any]:
    q = (query or "").lower()
    out = {"target_mtpa": None, "target_months": None, "max_payback_months": None}
    m = re.search(r'(\d+(\.\d+)?)\s*mtpa', q)
    if m:
        try:
            out["target_mtpa"] = float(m.group(1))
        except:
            pass
    mm = re.search(r'(\d{1,3})\s*(?:months|month)', q)
    if mm:
        try:
            out["target_months"] = int(mm.group(1))
        except:
            pass
    pp = re.search(r'payback.*?(?:less than|within|<)\s*(\d+)\s*(years|year)', q)
    if pp:
        try:
            out["max_payback_months"] = int(pp.group(1)) * 12
        except:
            pass
    return out

def _aggregate_risk_factors() -> Dict[str, float]:
    p = RISK_PROFILE
    procurement_delay_pct = p["weather"]["procurement_delay_pct"] + p["supply_chain"]["procurement_delay_pct"] + p["geopolitics"]["shipping_delay_pct"]
    implementation_delay_pct = p["weather"]["implementation_delay_pct"] + p["supply_chain"]["implementation_delay_pct"] + p["contractor"]["implementation_delay_pct"]
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
    loaded = _load_mock_data()
    data = loaded.get("data", {})

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

    # infra baseline
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

    # baseline additions
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

    # base durations
    planning = 3
    procurement_base = max(2, int(round(2 + total_added_mtpa * 4)))
    implementation_base = max(3, int(round(4 + total_added_mtpa * 6)))
    commissioning_base = max(1, int(round(implementation_base * 0.25)))
    stabilization_base = max(1, int(round(commissioning_base * 0.5)))
    estimated_total_months_base = planning + procurement_base + implementation_base + commissioning_base + stabilization_base

    # apply deterministic risk multipliers (internally)
    risk = _aggregate_risk_factors()
    procurement_adj = max(1, int(round(procurement_base * (1 + risk["procurement_delay_pct"]))))
    implementation_adj = max(1, int(round(implementation_base * (1 + risk["implementation_delay_pct"]))))
    commissioning_adj = max(1, int(round(commissioning_base * (1 + risk["commissioning_delay_pct"]))))
    stabilization_adj = max(1, int(round(stabilization_base * (1 + risk["commissioning_delay_pct"] * 0.5))))
    estimated_total_months_final = planning + procurement_adj + implementation_adj + commissioning_adj + stabilization_adj

    # final financials (internal math applied)
    final_capex = base_capex * (1 + risk["capex_inflation_pct"])
    final_margin = base_margin * (1 - risk["margin_down_pct"])
    final_payback_months = None
    if final_margin > 0:
        final_payback_months = (final_capex / final_margin) * 12.0

    # availability after internal adjustments
    available_energy_final = max(0.0, available_energy_for_steel * (1 - risk["energy_availability_down_pct"]))
    available_port_final = max(0.0, available_port_for_steel * (1 - risk["port_availability_down_pct"]))

    # validations (only used internally; not surfaced as debug)
    validations = {"checks": [], "passed": True}
    if parsed.get("target_mtpa") is not None:
        target_mtpa = parsed["target_mtpa"]
        if abs(total_added_mtpa - target_mtpa) / max(1e-9, target_mtpa) <= 0.02:
            validations["checks"].append({"name": "Target MTPA", "status": "pass"})
        else:
            validations["checks"].append({"name": "Target MTPA", "status": "fail"})
            validations["passed"] = False

    if parsed.get("max_payback_months") is not None and final_payback_months is not None:
        if final_payback_months <= parsed["max_payback_months"]:
            validations["checks"].append({"name": "Payback", "status": "pass"})
        else:
            validations["checks"].append({"name": "Payback", "status": "fail"})
            validations["passed"] = False

    if energy_required_mw <= available_energy_final + 1e-9:
        validations["checks"].append({"name": "Energy", "status": "pass"})
    else:
        validations["checks"].append({"name": "Energy", "status": "fail"}); validations["passed"] = False

    if port_required_tpa <= available_port_final + 1e-9:
        validations["checks"].append({"name": "Ports", "status": "pass"})
    else:
        validations["checks"].append({"name": "Ports", "status": "fail"}); validations["passed"] = False

    # per-plant schedule (staggered using final durations)
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

    # actions & rationale (concise)
    actions = [
        "Deploy MES & targeted automation at highest ROI plants to accelerate ramp.",
        "Secure frame contracts for long-lead equipment and pre-qualify suppliers.",
        "Negotiate PPAs and implement WHR & buffering to ensure energy supply during ramp.",
        "Reserve temporary port/3PL capacity to protect commercial cargo flows.",
        "Establish PMO with weekly gates, contingency budget and KPI dashboards."
    ]
    rationale = [
        "Staged deployment (ROI-first) lowers near-term capital at risk and accelerates cash flow.",
        "Procurement mitigation (frame contracts) reduces critical-path exposure to supply-chain delays.",
        "Energy and port mitigations ensure logistics and power availability for uninterrupted ramp.",
        "PMO and stage gating control cost overruns and shorten the effective timeline through parallelization."
    ]

    # confidence model (final percent)
    confidence = START_CONFIDENCE
    for chk in validations["checks"]:
        if chk["status"] == "fail":
            confidence -= 12
    confidence -= int(round((risk["capex_inflation_pct"]) * 10))
    confidence -= int(round((risk["margin_down_pct"]) * 10))
    confidence = max(confidence, MIN_CONFIDENCE)

    # Final output: clean labels (no debug, no risk wording)
    result = {
        "recommendation": {
            "headline": f"Recommendation: +{total_added_mtpa:.3f} MTPA capacity (staged across plants)",
            "summary": "Staged program prioritizing highest-ROI plants first, with procurement and energy mitigations to protect schedule and payback.",
            "metrics": {
                "added_mtpa": round(total_added_mtpa, 3),
                "investment_usd": int(round(final_capex)),
                "estimated_payback_months": None if final_payback_months is None else round(final_payback_months, 1),
                "project_timeline_months": int(round(estimated_total_months_final)),
                "confidence_pct": int(round(confidence)),
                "energy_required_mw": round(energy_required_mw, 2),
                "port_throughput_required_tpa": int(port_required_tpa),
            },
            "actions": actions,
            "distribution": [{"plant": d["name"], "added_mtpa": d["added_mtpa"], "capex_usd": d["capex_usd"], "base_payback_months": d["base_payback_months"]} for d in breakdown]
        },
        "roadmap": {
            "phases": [
                {"phase": "Planning", "months": planning, "notes": "Engineering, permits, PMO setup"},
                {"phase": "Procurement", "months": procurement_adj, "notes": "Frame contracts, long-lead orders"},
                {"phase": "Implementation", "months": implementation_adj, "notes": "Installation & integration"},
                {"phase": "Commissioning", "months": commissioning_adj, "notes": "Cold / hot commissioning"},
                {"phase": "Stabilization", "months": stabilization_adj, "notes": "Ramp & optimization"},
            ],
            "per_plant_schedule": per_plant_schedule,
            "project_timeline_months": int(round(estimated_total_months_final))
        },
        "rationale": {"bullets": rationale},
        "validations": validations,
        "metrics": {
            "total_capex_usd": int(round(final_capex)),
            "total_annual_margin_usd": int(round(final_margin)),
            "aggregated_payback_months": None if final_payback_months is None else round(final_payback_months, 1),
            "available_energy_mw": round(available_energy_final, 2),
            "available_port_tpa": int(available_port_final),
            "project_timeline_months": int(round(estimated_total_months_final))
        },
        "em_summaries": {
            "steel_info": {"plant_distribution": breakdown},
            "ports_info": {"total_port_capacity_tpa": total_port_capacity, "used_port_tpa": int(used_port)},
            "energy_info": {"total_energy_capacity_mw": total_energy_capacity, "used_energy_mw": used_energy},
        },
        "confidence_pct": int(round(confidence))
    }

    return result

# End of decision_engine.py
