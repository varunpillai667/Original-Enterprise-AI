"""
Decision Orchestrator (budget-aware)
LOCAL Node → Enterprise Manager → Group Manager
Improvements:
- If EM returns no candidates due to a strict CapEx filter, re-run EM without the budget
  to retrieve top candidates and return a descriptive result that flags the budget violation.
- Provides clearer errors and a 'budget_flag' boolean in the result when budget prevented selection.
"""
from local_node import ingest_data
from enterprise_manager import evaluate_plants
from group_manager import orchestrate

def run_simulation(query: str, capex_limit_usd=None):
    data = ingest_data()

    # First attempt: respect optional capex limit when evaluating plants
    em_candidates = evaluate_plants(data, budget_usd=capex_limit_usd) if capex_limit_usd is not None else evaluate_plants(data)
    budget_flag = False

    # If no candidates found (likely because budget filter removed them), get candidates without budget for diagnostics
    if not em_candidates:
        budget_flag = True
        em_candidates = evaluate_plants(data, budget_usd=None)  # full candidate list for diagnostics

    if not em_candidates:
        raise RuntimeError("No EM candidates available for evaluation. Check mock_data.json content.")

    # Orchestrate to pick final candidate (GM applies cross-enterprise constraints)
    result = orchestrate(em_candidates, data, capex_limit_usd)
    result["query"] = query
    result["timestamp"] = data["timestamp"]
    result["data_snapshot"] = {"energy": data["energy"], "ports": data["ports"]}
    result["budget_flag"] = budget_flag

    # If budget_flag true, add a human-readable note
    if budget_flag:
        result["summary"] = result.get("summary", "") + " NOTE: initial CapEx limit filtered out all candidates; recommendation shows top candidate (budget exceeded)."

    return result

def explain_decision(query: str, result):
    exp = f"""### **Explainable Decision Flow**

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

    for k, v in result.get("explainability", {}).items():
        exp += f"- **{k}:** {v}\n"

    # Add budget warning if present
    if result.get("budget_flag", False):
        exp += "\n**Budget Note:** The provided CapEx limit filtered out all EM candidates; presenting top candidate and flagging budget constraint.\n"

    exp += f"\n---\n**System Summary:** {result.get('summary','')}"
    return exp
