import random

def run_simulation(query):
    """
    Simulates AI-based decision for operational optimization.
    """
    plants = ["SP1", "SP2", "SP3", "SP4"]
    ports = ["Port Alpha", "Port Bravo", "Port Foxtrot"]
    selected_plant = random.choice(plants)
    import_port = random.choice(ports)
    export_port = random.choice(ports)

    return {
        "recommended_plant": selected_plant,
        "expected_increase": f"+{random.randint(10, 20)}%",
        "investment": f"USD {random.randint(400000, 700000):,}",
        "roi_period": f"{random.randint(6, 12)} months",
        "energy": f"{random.randint(3, 6)} MW from {import_port}",
        "summary": f"Increase production at {selected_plant} using improved logistics via {import_port} and export through {export_port}."
    }


def explain_decision(query, result):
    """
    Generates detailed explanation of decision flow (without API calls).
    """
    explanation = f"""
**Operational Simulation Flow**

1️⃣ **CEO Query:** The CEO’s question – *"{query}"* – was analyzed to determine focus areas (capacity, cost, and logistics).

2️⃣ **Group Manager:** Interpreted the strategic goal and distributed the objective to enterprise-level domains.

3️⃣ **Enterprise Manager (Steel):** Evaluated all steel plants (SP1–SP4) for upgrade potential based on ROI, production, and energy efficiency.

4️⃣ **Import Port (e.g., Port Alpha):** Calculated inbound logistics feasibility and raw material availability.

5️⃣ **Steel Plant ({result['recommended_plant']}):** Simulated operational throughput increase and capex requirement.

6️⃣ **Export Port (e.g., Port Foxtrot):** Optimized outbound logistics for distribution and delivery cost.

7️⃣ **Final Recommendation:** Synthesized all layers — strategy, logistics, and operations — into a unified action plan.

---

**System Summary:**  
> The AI selected **{result['recommended_plant']}** as the optimal plant considering import/export logistics, operational cost, and fastest payback potential.
"""
    return explanation
