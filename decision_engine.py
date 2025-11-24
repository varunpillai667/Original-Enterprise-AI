# =========================
# File: decision_engine.py
# =========================
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List

OPERATIONAL_FLOW_DOC = "/mnt/data/Operational Flow.docx"

CAPEX_PER_MTPA_USD = 420_000_000
MARGIN_PER_TON_USD = 120
MW_PER_MTPA = 2.5
CARGO_TONNE_PER_STEEL_TONNE = 0.15

PER_PLANT_MTPA = [
    {"id": "SP1", "name": "Steel Plant 1", "added_mtpa": 0.8},
    {"id": "SP2", "name": "Steel Plant 2", "added_mtpa": 0.6},
    {"id": "SP3", "name": "Steel Plant 3", "added_mtpa": 0.4},
    {"id": "SP4", "name": "Steel Plant 4", "added_mtpa": 0.2},
]

PORT_UTILIZATION = 0.70
PORT_GROUP_SHARE_OF_USED = 1.0 / 3.0
ENERGY_UTILIZATION = 0.75
ENERGY_GRID_SHARE_OF_USED = 3.0 / 4.0

RISK_PROFILE = {
    "procurement_delay_pct": 0.14,
    "implementation_delay_pct": 0.12,
    "commissioning_delay_pct": 0.03,
    "capex_inflation_pct": 0.15,
    "margin_down_pct": 0.12,
    "energy_availability_down_pct": 0.05,
    "port_availability_down_pct": 0.04
}

START_CONFIDENCE = 88
MIN_CONFIDENCE = 40

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

def _capex_for_mtpa(mtpa: float) -> float:
    return mtpa * CAPEX_PER_MTPA_USD

def _annual_margin_for_tpa(tpa: int) -> float:
    return tpa * MARGIN_PER_TON_USD

def _energy_mw_for_mtpa(mtpa: float) -> float:
    return mtpa * MW_PER_MTPA

def _try_load_docx(path: str) -> Dict[str, Any]:
    try:
        from docx import Document
    except Exception:
        return {}
    try:
        p = Path(path)
        if not p.exists():
            return {}
        doc = Document(path)
        text = "\n".join(par.text for par in doc.paragraphs if par.text)
        extracted = {}
        m_ports = re.search(r'ports.*?(\d+[\d,]*)\s*tpa', text, re.I | re.S)
        if m_ports:
            extracted.setdefault("ports", {})["total_port_capacity_tpa"] = int(m_ports.group(1).replace(",",""))
        m_energy = re.search(r'power.*?(\d+)\s*MW', text, re.I | re.S)
        if m_energy:
            extracted.setdefault("energy", {})["total_energy_capacity_mw"] = int(m_energy.group(1))
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
    doc_values = _try_load_docx(OPERATIONAL_FLOW_DOC)
    if doc_values:
        data = DEFAULT_DATA.copy()
        if "steel" in doc_values:
            data["steel"]["plants"] = doc_values["steel"].get("plants", data["steel"]["plants"])
        if "ports" in doc_values:
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
    return DEFAULT_DATA

def _build_per_plant_upgrade(plant: Dict[str,Any], added_mtpa: float) -> Dict[str,Any]:
    added_tpa = int(round(added_mtpa * 1_000_000))
    capex = int(round(_capex_for_mtpa(added_mtpa)))
    pkg = []
    hires = {"engineers":0,"maintenance":0,"operators":0,"project_managers":1}
    months_procurement = max(3, int(round(3 + added_mtpa * 4)))
    months_implementation = max(6, int(round(6 + added_mtpa * 8)))
    months_commission = max(1, int(round(months_implementation * 0.2)))
    if added_mtpa >= 0.7:
        pkg = [
            "Install modular EAF cells (scalable modules)",
            "Hot Rolling / downstream interface checks and upgrades",
            "Waste Heat Recovery (WHR) + substation upgrade",
            "Full MES & process automation",
            "Stockyard automation and pellet feeders"
        ]
        hires = {"engineers":8,"maintenance":16,"operators":40,"project_managers":2}
    elif added_mtpa >= 0.4:
        pkg = [
            "Add modular EAF cell(s) or increase BOF interface capacity",
            "Targeted automation (MES modules)",
            "Stockyard / feeders & pellet handling upgrades",
            "Substation capacity check and local WHR where cost-effective"
        ]
        hires = {"engineers":6,"maintenance":12,"operators":30,"project_managers":1}
    else:
        pkg = [
            "Process tuning, OEE program, targeted automation",
            "Add small modular EAF skids or upgrade throughput",
            "Optimize internal logistics and material handling"
        ]
        hires = {"engineers":4,"maintenance":8,"operators":20,"project_managers":1}
    schedule = {
        "procurement_months": months_procurement,
        "implementation_months": months_implementation,
        "commissioning_months": months_commission,
        "expected_time_to_online_months": months_procurement + months_implementation + months_commission
    }
    capex_breakdown = {
        "EAF_modules_usd": int(round(capex * 0.55)),
        "automation_usd": int(round(capex * 0.12)),
        "raw_handling_usd": int(round(capex * 0.10)),
        "electrical_upgrade_usd": int(round(capex * 0.12)),
        "contingency_usd": int(round(capex * 0.11)),
    }
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
    data = _load_data()
    plants = data.get("steel",{}).get("plants", [])
    ports = data.get("ports",{}).get("ports", [])
    energy_plants = data.get("energy",{}).get("plants", [])

    per_plant_results = []
    total_added_mtpa = 0.0
    total_capex = 0
    total_added_tpa = 0
    total_added_margin = 0

    for idx, assignment in enumerate(PER_PLANT_MTPA):
        plant = plants[idx] if idx < len(plants) else {"id": assignment["id"], "name": assignment["name"], "current_capacity_tpa": 0}
        added_mtpa = assignment["added_mtpa"]
        entry = _build_per_plant_upgrade(plant, added_mtpa)
        per_plant_results.append(entry)
        total_added_mtpa += added_mtpa
        total_capex += entry["capex_total_usd"]
        total_added_tpa += entry["added_tpa"]
        total_added_margin += entry["expected_annual_margin_usd"]

    total_port_capacity = sum(int(p.get("capacity_tpa",0)) for p in ports) or 0
    used_port = int(round(total_port_capacity * PORT_UTILIZATION))
    group_port_share = int(round(used_port * PORT_GROUP_SHARE_OF_USED))
    spare_port = total_port_capacity - used_port
    available_port_for_project = spare_port + group_port_share
    port_requirement_tpa = int(round(total_added_tpa * CARGO_TONNE_PER_STEEL_TONNE))

    total_energy_capacity_mw = sum(float(e.get("capacity_mw",0)) for e in energy_plants) or 0.0
    used_energy_mw = total_energy_capacity_mw * ENERGY_UTILIZATION
    group_energy_share_mw = used_energy_mw * (1 - ENERGY_GRID_SHARE_OF_USED)
    spare_energy_mw = total_energy_capacity_mw - used_energy_mw
    available_energy_for_project_mw = spare_energy_mw + group_energy_share_mw
    energy_required_mw = _energy_mw_for_mtpa(total_added_mtpa)

    capex_inflation = RISK_PROFILE["capex_inflation_pct"]
    schedule_procurement_pct = RISK_PROFILE["procurement_delay_pct"]
    schedule_implementation_pct = RISK_PROFILE["implementation_delay_pct"]
    schedule_commission_pct = RISK_PROFILE["commissioning_delay_pct"]

    max_online = max(p["schedule_windows_months"]["expected_time_to_online_months"] for p in per_plant_results)
    project_timeline_months = int(round(max_online * (1 + schedule_procurement_pct + schedule_implementation_pct * 0.25)))

    final_capex_usd = int(round(total_capex * (1 + capex_inflation)))
    final_annual_margin_usd = int(round(total_added_margin * (1 - RISK_PROFILE["margin_down_pct"])))
    estimated_payback_months = None
    if final_annual_margin_usd > 0:
        estimated_payback_months = round((final_capex_usd / final_annual_margin_usd) * 12.0, 1)

    key_recommendations: List[Dict[str,Any]] = []

    key_recommendations.append({
        "step": "Program setup & governance",
        "owner": "Group PMO",
        "duration_months": 1,
        "details": [
            "Establish PMO with weekly gates and KPI dashboard",
            "Appoint SRO and plant PMs",
            "Secure contingency funding (5-10% Phase A)"
        ]
    })

    for p in per_plant_results:
        p["roi_proxy"] = (p["expected_annual_margin_usd"] / (p["capex_total_usd"] or 1))
    sorted_by_roi = sorted(per_plant_results, key=lambda x: x["roi_proxy"], reverse=True)
    phase_a = sorted_by_roi[:2]
    phase_b = sorted_by_roi[2:]

    if phase_a:
        phase_a_max_online = max(item["schedule_windows_months"]["expected_time_to_online_months"] for item in phase_a)
    else:
        phase_a_max_online = 6

    key_recommendations.append({
        "step": "Phase A execution (ROI-first)",
        "owner": "Steel EM / Plant PMs",
        "duration_months": max(int(round(phase_a_max_online * (1 + schedule_procurement_pct + schedule_implementation_pct*0.2))), 6),
        "details": [
            "Deploy MES & automation, procure/install modular EAFs, WHR & substation upgrades",
            "Stockyard automation and frame contracts for long-lead items",
            "Prioritize early cash generation and quick commissioning"
        ],
        "plants_in_scope": [p["plant_name"] for p in phase_a]
    })

    key_recommendations.append({
        "step": "Phase B execution (remaining plants)",
        "owner": "Steel EM / Plant PMs",
        "duration_months": max(6, int(round(max(p["schedule_windows_months"]["expected_time_to_online_months"] for p in phase_b) * (1 + schedule_procurement_pct)))) if phase_b else 6,
        "details": [
            "Repeat modular installations where required and finalize finishing upgrades",
            "Scale supply chain flows and integrate MES dashboards",
            "Use Phase A learnings to compress schedule"
        ],
        "plants_in_scope": [p["plant_name"] for p in phase_b]
    })

    key_recommendations.append({
        "step": "Ports & logistics (protect commercial throughput)",
        "owner": "Ports EM / Logistics",
        "duration_months": 2,
        "details": [
            "Reserve temporary berth capacity & 3PL partners",
            "Time-window inbound shipments to avoid commercial peaks",
            "Expedited customs lanes & extra shifts during inbound peaks",
            f"Maintain commercial throughput allocation (~{int(round(total_port_capacity*0.7)):,} tpa) while using spare/3PL for project"
        ]
    })

    key_recommendations.append({
        "step": "Energy program (protect national grid supply)",
        "owner": "Energy EM / Utilities",
        "duration_months": 3,
        "details": [
            "Negotiate short-term PPAs, add WHR/captive generation",
            "Upgrade substations/switchgear, implement smart load scheduling",
            f"Keep national-grid commitments intact (~{int(round((1-ENERGY_GRID_SHARE_OF_USED)*total_energy_capacity_mw))} MW prioritized)"
        ]
    })

    key_recommendations.append({
        "step": "Procurement & supplier de-risking",
        "owner": "Group Procurement",
        "duration_months": 4,
        "details": [
            "Sign frame contracts & partial advances for long-lead items",
            "Dual-sourcing and vendor-managed inventory for consumables"
        ]
    })

    key_recommendations.append({
        "step": "Controls & commissioning",
        "owner": "PMO",
        "duration_months": 2,
        "details": [
            "Integrated commissioning plans with group-level cutovers",
            "10% schedule contingency & 8-12% capex contingency",
            "Acceptance gates: mechanical, cold, hot, performance"
        ]
    })

    per_plant_upgrades = []
    for p in per_plant_results:
        p_final_capex = int(round(p["capex_total_usd"] * (1 + RISK_PROFILE["capex_inflation_pct"])))
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

    # Build a rich rationale that explains every recommendation
    rationale_bullets: List[str] = []

    # Explain program setup
    rationale_bullets.append(
        "Program setup & governance: A central PMO and SRO ensure consistent decision-making, single version of truth, and quick escalation — critical to manage parallel plant upgrades and cross-EM coordination."
    )

    # Explain each recommendation step explicitly
    for step in key_recommendations[1:]:  # skip program setup which is already added
        name = step["step"]
        owner = step.get("owner", "Owner")
        dur = step.get("duration_months", "N/A")
        # create concise why statement derived from details
        primary_reasons = "; ".join(step["details"][:2]) if step.get("details") else ""
        rationale_bullets.append(
            f"{name} ({owner}, {dur} months): Implement because {primary_reasons}. This ensures that the project meets capacity, schedule and operational continuity targets while providing clear owners and timing."
        )

    # Add per-plant rationale
    for p in per_plant_upgrades:
        reason = (
            f"{p['plant_name']}: Upgrade package (adds {p['added_mtpa']} MTPA) selected to deliver fastest capacity per USD "
            f"— modular EAF and MES for throughput, WHR/substation work where needed. Estimated capex ${p['capex_total_usd']:,}; "
            f"main dependencies: long-lead EAF modules, electrical upgrades, and inbound port capacity."
        )
        rationale_bullets.append(reason)

    # Explain ports & energy support explicitly (how they avoid compromising commercial/grid)
    rationale_bullets.append(
        "Ports: Using spare berth capacity + reserved 3PL slots and time-windowed arrivals ensures project imports do not reduce commercial cargo throughput; expedited customs lanes and extra handling shifts preserve SLAs."
    )
    rationale_bullets.append(
        "Energy: Short-term PPAs, WHR and captive generation plus substation upgrades and smart load scheduling provide the incremental MW needed for ramp without diverting committed supply to the national grid."
    )

    # Confidence model
    confidence = START_CONFIDENCE
    if energy_required_mw > available_energy_for_project_mw:
        confidence -= 15
    if port_requirement_tpa > available_port_for_project:
        confidence -= 12
    confidence -= int(round(RISK_PROFILE["capex_inflation_pct"] * 10))
    confidence -= int(round(RISK_PROFILE["margin_down_pct"] * 10))
    confidence = max(confidence, MIN_CONFIDENCE)

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
            "project_timeline_months": int(round(project_timeline_months))
        },
        "rationale": {"bullets": rationale_bullets},
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
