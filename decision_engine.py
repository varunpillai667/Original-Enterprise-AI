"""
Decision Orchestrator (budget-aware)
LOCAL Node → Enterprise Manager → Group Manager
Snapshot removed.
"""
from local_node import ingest_data
from enterprise_manager import evaluate_plants
from group_manager import orchestrate

def run_simulation(query: str, capex_limit_usd=None):
    data = ingest_data()

    em_candidates = evaluate_plants(data, budget_usd=capex_limit_usd) if capex_limit_usd is not None else evaluate_plants(data)
    budget_flag = False

    if not em_candidates:
        budget_flag = True
        em_candidates = evaluate_plants(data, budget_usd=None)

    if not em_candidates:
        raise RuntimeError("No EM candidates available for evaluation. Check mock_data.json content.")

    result = orchestrate(em_candidates, data, capex_limit_usd)
    result["query"] = query
    result["timestamp"] = data["timestamp"]
    result["budget_flag"] = budget_flag

    if budget_flag:
        result["summary"] = result.get("summary", "") + \
            " NOTE: initial CapEx limit filtered out all candidates; recommendation shows top candidate (budget exceeded)."

    return result


def explain_decision(query: str, result):
    exp = f"""### **Explainable Decision Flow**

1️⃣ CEO query interpreted: *{query}*

2️⃣ Group Manager evaluated constraints
3️⃣ Enterprise Manager ranked plants
4️⃣ Selected Plant: **{result['recommended_plant']}**
5️⃣ Expected increase: **{result['expected_increase_pct']}**
6️⃣ Energy required: **{result['energy_required_mw']} MW**

### Explainability Factors
"""

    for k, v in result.get("explainability", {}).items():
        exp += f"- **{k}:** {v}\n"

    if result.get("budget_flag", False):
        exp += "\n**Budget Note:** CapEx limit filtered out all top EM candidates.\n"

    exp += f"\n---\n**System Summary:** {result.get('summary','')}"

    return exp
