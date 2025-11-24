# File: decision_engine.py
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List

# Executive decision engine producing exhaustive, actionable recommendations.
# The engine will attempt to read /mnt/data/Operational Flow.docx for authoritative inputs.
# If python-docx is unavailable or the file is missing, built-in defaults are used.

# Config / constants
OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"  # uploaded doc path (kept for ingestion if available)

CAPEX_PER_MTPA_USD = 420_000_000
MARGIN_PER_TON_USD = 120
MW_PER_MTPA = 2.5
CARGO_TONNE_PER_STEEL_TONNE = 0.15

# Distribution required
PER_PLANT_MTPA = [
    {"id": "SP1", "name": "Steel Plant 1", "added_mtpa": 0.8},
    {"id": "SP2", "name": "Steel Plant 2", "added_mtpa": 0.6},
    {"id": "SP3", "name": "Steel Plant 3", "added_mtpa": 0.4},
    {"id": "SP4", "name": "Steel Plant 4", "added_mtpa": 0.2},
]

# Assumed operational shares (group rules)
PORT_UTILIZATION = 0.70
PORT_GROUP_SHARE_OF_USED = 1.0 / 3.0
ENERGY_UTILIZATION = 0.75
ENERGY_GRID_SHARE_OF_USED = 3.0 / 4.0

# Risk multipliers (internal deterministic model — not surfaced)
RISK_PROFILE = {
    "procurement_delay_pct": 0.14,  # combined supply/weather/geopolitics
    "implementation_delay_pct": 0.12,
    "commissioning_delay_pct": 0.03,
    "capex_inflation_pct": 0.15,
    "margin_down_pct": 0.12,
    "energy_availability_down_pct": 0.05,
    "port_availability_down_pct": 0.04
}

START_CONFIDENCE = 88
MIN_CONFIDENCE = 40

# Defensive mock data (if no doc)
DEFAULT_DATA = {
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
        "plants":[
            {"id":"E1","capacity_mw":500},
            {"id":"E2","capacity_mw":450},
            {"id":"E3","capacity_mw":400},
        ]
    }
}

# Helpers
def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

def _try_load_docx(path: str) -> Dict[str, Any]:
    """
    Attempt to extract structured numbers from the uploaded Operational Flow.docx.
    If python-docx is not installed or parsing fails, return {} (caller will fallback).
    The function intentionally conservative: only pulls numbers if clearly found.
    """
    try:
        from docx import Document
    except Exception:
        return {}
    try:
        p = Path(path)
        if not p.exists():
            return {}
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text)
        # simple extraction heuristics
        extracted = {}
        m_ports = re.search(r'ports.*?(\d+[\d,]*)\s*tpa', text, re.I | re.S)
        if m_ports:
            extracted.setdefault("ports", {})["total_port_capacity_tpa"] = int(m_ports.group(1).replace(",",""))
        m_energy = re.search(r'power.*?(\d+)\s*MW', text, re.I | re.S)
        if m_energy:
            extracted.setdefault("energy", {})["total_energy_capacity_mw"] = int(m_energy.group(1))
        # attempt to find per-plant capacities
        plants = []
        for i in range(1,6):
            m = re.search(r'(steel plant\s*'+str(i)+r').*?(\d+[\d,]*)\s*tpa', text, re.I | re.S)
            if m:
                plants.append({"id": f"SP{i}", "name": m.group(1).strip(), "current_capacity_tpa": int(m.group(2).replace(",",""))})
        if plants:
            extracted.setdefault("steel", {})["plants"] = plants
        return extracted
    except Exception:
        return {}

def _load_data():
    # try docx first
    doc_values = _try_load_docx(OPERATIONAL_FLOW_DOC)
    if doc_values:
        # merge with defaults, preserving extracted values
        data = DEFAULT_DATA.copy()
        # merge steel
        if "steel" in doc_values:
            data["steel"]["plants"] = doc_values["steel"].get("plants", data["steel"]["plants"])
        if "ports" in doc_values:
            # if doc provided total port capacity, expand to per-port rough split
            t = doc_values["ports"].get("total_port_capacity_tpa")
            if t:
                per = int(t // 4)
                data["ports"]["ports"] = [{"id":f"P{i+1}","capacity_tpa":per} for i in range(4)]
        if "energy" in doc_values:
            tm = doc_values["energy"].get("total_energy_capacity_mw")
            if tm:
                per = int(tm // 3)
                data["energy"]["plants"] = [{"id":f"E{i+1}","capacity_mw":per} for i in range(3)]
        return data
    # fallback
    return DEFAULT_DATA

def _build_per_plant_upgrade(plant: Dict[str,Any], added_mtpa: float) -> Dict[str,Any]:
    """
    Decision rules to pick upgrade type & scope based on plant size to add 'added_mtpa'.
    Returns actionable upgrade steps, CAPEX estimate, hires, and timeline windows (months).
    """
    # basics
    added_tpa = int(round(added_mtpa * 1_000_000))
    capex = int(round(_capex_for_mtpa(added_mtpa)))
    # Decide upgrade package by size
    # Large (>=0.7 MTPA): Full modular EAF + WHR + automation + raw material handling upgrade
    # Medium (0.4-0.7): Modular EAF cell(s) + automation + stockyard handling
    # Small (<0.4): Automation & process tuning + small modular EAF skids or capacity optimization
    pkg = []
    hires = {"engineers":0,"maintenance":0,"operators":0,"project_managers":1}
    months_procurement = max(3, int(round(3 + added_mtpa * 4)))  # heuristic
    months_implementation = max(6, int(round(6 + added_mtpa * 8)))
    months_commission = max(1, int(round(months_implementation * 0.2)))
    if added_mtpa >= 0.7:
        pkg = [
            "Install modular EAF cells (scalable modules) — largest capacity uplift",
            "Hot Rolling / downstream interface checks and minor upgrades",
            "Waste Heat Recovery (WHR) installation and substation upgrade (transformers, VFDs)",
            "Full MES + process automation (OEE uplift)",
            "Stockyard automation and pelletizing feeders for raw-material handling"
        ]
        hires = {"engineers":8,"maintenance":16,"operators":40,"project_managers":2}
    elif added_mtpa >= 0.4:
        pkg = [
            "Add modular EAF cell(s) or increase BOF interface capacity",
            "Install targeted automation (MES modules) to reduce ramp time",
            "Stockyard / feeders & pellet handling upgrades",
            "Substation capacity check and local WHR where cost-effective"
        ]
        hires = {"engineers":6,"maintenance":12,"operators":30,"project_managers":1}
    else:
        pkg = [
            "Process tuning, OEE program, targeted automation (MES modules)",
            "Add small modular EAF skids or upgrade existing line throughput",
            "Optimize logistics and material handling within the plant"
        ]
        hires = {"engineers":4,"maintenance":8,"operators":20,"project_managers":1}

    # per-plant schedule windows (staggered planning)
    schedule = {
        "procurement_months": months_procurement,
        "implementation_months": months_implementation,
        "commissioning_months": months_commission,
        "expected_time_to_online_months": months_procurement + months_implementation + months_commission
    }

    # CAPEX split heuristics (rough)
    capex_breakdown = {
        "EAF_modules_usd": int(round(capex * 0.55)),
        "automation_usd": int(round(capex * 0.12)),
        "raw_handling_usd": int(round(capex * 0.10)),
        "electrical_upgrade_usd": int(round(capex * 0.12)),
        "contingency_usd": int(round(capex * 0.11)),
    }

    # expected incremental margin uplift (annual) from added capacity
    added_margin_annual = int(round(added_tpa * MARGIN_PER_TON_USD))

    return {
        "plant_id": plant.get("id"),
        "plant_name": plant.get("name"),
        "current_capacity_tpa": int(plant.get("current_capacity_tpa",0)),
        "added_mtpa": round(added_mtpa,3),
        "added_tpa": added_tpa,
        "capex_total_usd": capex,
        "capex_breakdown_usd": capex_breakdown,
        "expected_annual_margin_usd": added_margin_annual,
        "estimated_payback_months_base": None if added_margin_annual ==0 else round((capex / added_margin_annual) * 12.0,1),
        "hiring_estimate": hires,
        "upgrade_scope": pkg,
        "schedule_windows_months": schedule
    }

def run_simulation(query: str) -> Dict[str,Any]:
    """
    Main entry. Returns a single plain result (no debug traces).
    The result contains exhaustive 'key_recommendations' and actionable per-plant upgrades
    and group-level actions for ports & energy to keep commercial cargo and grid supply uncompromised.
    """
    data = _load_data()
    plants = data.get("steel",{}).get("plants", [])
    ports = data.get("ports",{}).get("ports", [])
    energy_plants = data.get("energy",{}).get("plants", [])

    # map PER_PLANT_MTPA to actual plants by index
    per_plant_results = []
    total_added_mtpa = 0.0
    total_capex = 0
    total_added_tpa = 0
    total_added_margin = 0

    for idx, assignment in enumerate(PER_PLANT_MTPA):
        # get plant baseline; if not enough plants, fallback to generated name/id
        plant = plants[idx] if idx < len(plants) else {"id": assignment["id"], "name": assignment["name"], "current_capacity_tpa": 0}
        added_mtpa = assignment["added_mtpa"]
        entry = _build_per_plant_upgrade(plant, added_mtpa)
        per_plant_results.append(entry)
        total_added_mtpa += added_mtpa
        total_capex += entry["capex_total_usd"]
        total_added_tpa += entry["added_tpa"]
        total_added_margin += entry["expected_annual_margin_usd"]

    # group-level infrastructure computations
    total_port_capacity = sum(int(p.get("capacity_tpa",0)) for p in ports) or 0
    used_port = int(round(total_port_capacity * PORT_UTILIZATION))
    group_port_share = int(round(used_port * PORT_GROUP_SHARE_OF_USED))
    spare_port = total_port_capacity - used_port
    # Ensure spare + group_share used to support project cargo without reducing commercial throughput
    available_port_for_project = spare_port + group_port_share
    port_requirement_tpa = int(round(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE))

    total_energy_capacity_mw = sum(float(e.get("capacity_mw",0)) for e in energy_plants) or 0.0
    used_energy_mw = total_energy_capacity_mw * ENERGY_UTILIZATION
    group_energy_share_mw = used_energy_mw * (1 - ENERGY_GRID_SHARE_OF_USED)  # portion currently used by group
    spare_energy_mw = total_energy_capacity_mw - used_energy_mw
    available_energy_for_project_mw = spare_energy_mw + group_energy_share_mw
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)

    # Apply deterministic internal multipliers invisibly (capex inflation, schedule lengthening)
    capex_inflation = RISK_PROFILE["capex_inflation_pct"]
    schedule_procurement_pct = RISK_PROFILE["procurement_delay_pct"]
    schedule_implementation_pct = RISK_PROFILE["implementation_delay_pct"]
    schedule_commission_pct = RISK_PROFILE["commissioning_delay_pct"]

    # compute project timeline by aggregating per-plant windows plus group-level delays
    # We'll compute a conservative group timeline: take the max expected online months across plants, then apply group multipliers
    max_online = max(p["schedule_windows_months"]["expected_time_to_online_months"] for p in per_plant_results)
    project_timeline_months = int(round(max_online * (1 + schedule_procurement_pct + schedule_implementation_pct * 0.25)))

    # final financials
    final_capex_usd = int(round(total_capex * (1 + capex_inflation)))
    final_annual_margin_usd = int(round(total_added_margin * (1 - RISK_PROFILE["margin_down_pct"])))
    estimated_payback_months = None
    if final_annual_margin_usd > 0:
        estimated_payback_months = round((final_capex_usd / final_annual_margin_usd) * 12.0, 1)

    # Build exhaustive key recommendations (start -> end)
    # Each item is actionable: owner / estimated months / resources / dependencies
    key_recommendations: List[Dict[str,Any]] = []

    # 0. Program setup
    key_recommendations.append({
        "step": "Program setup & governance",
        "owner": "Group PMO",
        "duration_months": 1,
        "details": [
            "Establish Project Management Office (PMO) with weekly gates, KPIs (cost, schedule, energy, port throughput)",
            "Define single program SRO, appoint plant-level project managers",
            "Secure initial contingency funding (5-10% of phase A capex)"
        ]
    })

    # 1. Phase A: Highest ROI plants (select top 2 by ROI proxy)
    # Determine ROI proxy (annual_margin / capex)
    for p in per_plant_results:
        p["roi_proxy"] = (p["expected_annual_margin_usd"] / (p["capex_total_usd"] or 1))
    sorted_by_roi = sorted(per_plant_results, key=lambda x: x["roi_proxy"], reverse=True)
    phase_a = sorted_by_roi[:2]
    phase_b = sorted_by_roi[2:]

    # Phase A recommendations
    key_recommendations.append({
        "step": "Phase A execution (ROI-first)",
        "owner": "Steel EM / Plant PMs",
        "duration_months": max(int(round(x["schedule_windows_months"]["expected_time_to_online_months"] * (1 + schedule_procurement_pct + schedule_implementation_pct*0.2))), 6),
        "details": [
            "Deploy MES + targeted automation and productivity program to rapidly increase OEE",
            "Procure and install modular EAF modules at Phase A plants (prioritise plants with best ROI)",
            "Implement WHR and substation upgrades at Phase A plants to secure additional MW",
            "Execute stockyard automation and raw-material handling for Phase A plants to ensure inbound flows",
            "Lock frame contracts with key suppliers and pre-qualify 2nd-source vendors to mitigate delivery risk"
        ],
        "plants_in_scope": [p["plant_name"] for p in phase_a]
    })

    # Phase B recommendations
    key_recommendations.append({
        "step": "Phase B execution (remaining plants)",
        "owner": "Steel EM / Plant PMs",
        "duration_months": max(6, int(round(max(p["schedule_windows_months"]["expected_time_to_online_months"] for p in phase_b) * (1 + schedule_procurement_pct)))),
        "details": [
            "Repeat modular installations where required, finalize material handling & finishing upgrades",
            "Fine tune supply chain flows and integrate plant-level MES dashboards into group PMO",
            "Scale up commissioning and stabilization plans based on learnings from Phase A"
        ],
        "plants_in_scope": [p["plant_name"] for p in phase_b]
    })

    # Ports & logistics recommendations (to ensure commercial cargo uncompromised)
    key_recommendations.append({
        "step": "Ports & logistics (protect commercial throughput)",
        "owner": "Ports EM / Logistics",
        "duration_months": 2,
        "details": [
            "Reserve temporary berth capacity agreements and 3PL partners for peak import windows",
            "Schedule inbound raw-material shipments to avoid peak commercial windows (time-windowed arrivals)",
            "Implement expedited customs/clearance lanes for project-critical shipments (frame agreements with customs brokers)",
            "Deploy additional port handling shifts during peak material intake periods (no reduction to current commercial allocations)",
            f"Maintain minimum commercial throughput allocation: at least {int(round(total_port_capacity*0.7)):,} tpa is dedicated to commercial cargo; project cargo uses spare capacity and 3PL."
        ]
    })

    # Energy recommendations (to ensure national grid supply uncompromised)
    key_recommendations.append({
        "step": "Energy program (protect national grid supply)",
        "owner": "Energy EM / Utilities",
        "duration_months": 3,
        "details": [
            "Negotiate short-term PPAs for incremental MW required during ramp (prefer renewable + storage blends where feasible)",
            "Install WHR and local captive generation where ROI-positive to reduce grid draw",
            "Upgrade substations & switchgear to handle incremental loads without grid curtailments",
            "Implement smart scheduling of heavy loads (shifts) so peak grid demand not affected — maintain existing grid supply contracts for national grid unchanged",
            f"Ensure at least {int(round( (1- (ENERGY_GRID_SHARE_OF_USED)) * total_energy_capacity_mw ))} MW equivalent remains prioritized for the national grid per current commitments"
        ]
    })

    # Procurement & supply chain recommendations
    key_recommendations.append({
        "step": "Procurement & supplier de-risking",
        "owner": "Group Procurement",
        "duration_months": 4,
        "details": [
            "Sign frame contracts for long-lead items with penalty & SLAs",
            "Pay partial advance for critical modules to secure capacity slots",
            "Use dual-sourcing for critical components (transformers, drives, EAF modules)",
            "Establish vendor-managed inventory for refractory and consumables"
        ]
    })

    # PMO & program controls
    key_recommendations.append({
        "step": "Controls & commissioning",
        "owner": "PMO",
        "duration_months": 2,
        "details": [
            "Run integrated commissioning plans with group-level cutover windows",
            "Maintain a 10% contingency in schedule & 8-12% in capex budget for critical path items",
            "Set acceptance gates: mechanical completion, cold commissioning, hot commissioning, performance acceptance"
        ]
    })

    # Finalize per-plant detailed upgrades for output (clean)
    per_plant_upgrades = []
    for p in per_plant_results:
        # apply capex inflation silently
        p_final_capex = int(round(p["capex_total_usd"] * (1 + RISK_PROFILE["capex_inflation_pct"])))
        # compute final payback using a margin erosion
        annual_margin_final = int(round(p["expected_annual_margin_usd"] * (1 - RISK_PROFILE["margin_down_pct"])))
        payback_final = None
        if annual_margin_final > 0:
            payback_final = round((p_final_capex / annual_margin_final) * 12.0, 1)
        per_plant_upgrades.append({
            "plant_id": p["plant_id"],
            "plant_name": p["plant_name"],
            "current_capacity_tpa": p["current_capacity_tpa"],
            "added_mtpa": p["added_mtpa"],
            "added_tpa": p["added_tpa"],
            "upgrade_scope": p["upgrade_scope"],
            "capex_total_usd": p_final_capex,
            "capex_breakdown_usd": {k: int(round(v * (1 + RISK_PROFILE["capex_inflation_pct"]))) for k,v in p["capex_breakdown_usd"].items()},
            "hiring_estimate": p["hiring_estimate"],
            "schedule_months": p["schedule_windows_months"],
            "estimated_payback_months": payback_final
        })

    # Confidence model: penalize for any resource mismatch
    confidence = START_CONFIDENCE
    if energy_required_mw > available_energy_for_project_mw:
        confidence -= 15
    if port_requirement_tpa > available_port_for_project:
        confidence -= 12
    # penalty for capex inflation + margin erosion
    confidence -= int(round(RISK_PROFILE["capex_inflation_pct"] * 10))
    confidence -= int(round(RISK_PROFILE["margin_down_pct"] * 10))
    confidence = max(confidence, MIN_CONFIDENCE)

    # Build final result (clean labels; no debug)
    result = {
        "recommendation": {
            "headline": f"Comprehensive recommendation to add +{total_added_mtpa:.3f} MTPA across Group X steel plants",
            "summary": "Staged program (Phase A ROI-first) with detailed per-plant upgrades and supporting ports & energy programs to ensure commercial cargo and national-grid supply remain uncompromised.",
            "metrics": {
                "added_mtpa": round(total_added_mtpa,3),
                "investment_usd": int(round(final_capex_usd)),
                "estimated_payback_months": estimated_payback_months,
                "project_timeline_months": int(round(project_timeline_months)),
                "confidence_pct": int(round(confidence)),
                "energy_required_mw": round(energy_required_mw,2),
                "port_throughput_required_tpa": int(port_requirement_tpa)
            },
            "key_recommendations": key_recommendations,
            "per_plant_upgrades": per_plant_upgrades
        },
        "roadmap": {
            "phases": [
                {"phase":"Program setup","months":1},
                {"phase":"Phase A (ROI-first)","months": key_recommendations[1]["duration_months"]},
                {"phase":"Phase B (remaining)","months": key_recommendations[2]["duration_months"]},
                {"phase":"Ports & Logistics readiness","months": key_recommendations[3]["duration_months"]},
                {"phase":"Energy readiness","months": key_recommendations[4]["duration_months"]},
                {"phase":"Procurement & de-risking","months": key_recommendations[5]["duration_months"]},
                {"phase":"Controls & Commissioning","months": key_recommendations[6]["duration_months"]},
            ],
            "per_plant_schedule": [ {k: v for k,v in p.items() if k in ("plant","start_month_planning","procurement_window_months","implementation_window_months","commissioning_window_months","expected_online_month")} for p in [] ],  # not used here; app will show per_plant_upgrades schedule
            "project_timeline_months": int(round(project_timeline_months))
        },
        "rationale": {
            "bullets": [
                "Phase A targets the highest ROI plants to accelerate cash flow and reduce capital at risk.",
                "Modular EAF and MES investments deliver fastest capacity gains per USD of capex.",
                "Ports program ensures project shipments do not reduce commercial cargo capacity via 3PL and temporary berth agreements.",
                "Energy program combines PPAs, WHR and substation upgrades to avoid drawing additional capacity from the national grid.",
                "Procurement frame contracts and dual-sourcing mitigate long-lead and geopolitical supplier risk."
            ]
        },
        "em_summaries": {
            "steel": per_plant_upgrades,
            "ports": {
                "total_port_capacity_tpa": total_port_capacity,
                "available_for_project_tpa": int(round(available_port_for_project)),
                "required_for_project_tpa": int(round(port_requirement_tpa))
            },
            "energy": {
                "total_energy_capacity_mw": int(round(total_energy_capacity_mw)),
                "available_for_project_mw": float(round(available_energy_for_project_mw,2)),
                "required_for_project_mw": float(round(energy_required_mw,2))
            }
        },
        "confidence_pct": int(round(confidence))
    }

    return result

# quick test when run directly (no printing of debug)
if __name__ == "__main__":
    q = ("What is the recommended approach for increasing Group X’s steel production by approximately 2 MTPA, "
         "including the upgrades required across steel plants, the expected investment, the realistic implementation timeline, "
         "and the estimated period in which the investment can be recovered?")
    import pprint
    pprint.pprint(run_simulation(q))
