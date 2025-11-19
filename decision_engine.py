"""
Decision Orchestrator:
LOCAL Node → Enterprise Manager → Group Manager
Matches your whitepaper and diagrams.
"""
from local_node import ingest_data
from enterprise_manager import evaluate_plants
from group_manager import orchestrate


def run_simulation(query: str, capex_limit_usd=None):
    data = ingest_data()
    em_candidates = evaluate_plants(data, budget_usd=capex_limit_usd)

    result = orchestrate(em_candidates, data, capex_limit_usd)
    result["query"] = query
    result["timestamp"] = data["timestamp"]
    result["data_snapshot"] = {
        "energy": data["energy"],
        "ports": data["ports"]
    }

    return result


def explain_decision(query: str, result):
    exp = f"""
### **Explainable Decision Flow**

1️⃣ **CEO query interpreted:** *{query}*

2️⃣ **Group Manager** evaluated cross-company constraints  
   - Energy availability  
   - Port throughput  

3️⃣ **Enterprise Manager (Steel)** ranked plants based on:  
   - Spare capacity  
   - CapEx requirement  
   - ROI  
   - Energy demand

4️⃣ **Selected Plant:**  
   - **{result['recommended_plant']}**
   - Expected increase: **{result['expected_increase_pct']}**
   - Energy required: **{result['energy_required_mw']} MW**

### **Explainability Factors**
"""

    for k, v in result["explainability"].items():
        exp += f"- **{k}:** {v}\n"

    exp += f"""

---

### **System Summary**
{result['summary']}
"""

    return exp
