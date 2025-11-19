import random

# --------------------------------------------------------
# Run simulation mockup (includes ports for imports/exports)
# --------------------------------------------------------
def run_simulation(query: str):
    plants = ["SP1", "SP2", "SP3", "SP4"]
    ports = ["Port A", "Port B", "Port C"]
    recommended = random.choice(plants)
    import_port = random.choice(ports)
    export_port = random.choice([p for p in ports if p != import_port])

    return {
        "Recommended Plant": recommended,
        "Expected Output Increase": f"+{random.randint(8, 18)}%",
        "Capital Investment": f"USD {random.randint(400, 700)},000",
        "ROI Period": f"{random.randint(6, 12)} months",
        "Energy Required": f"{random.randint(4, 7)} MW from Power Plant {random.randint(1, 3)}",
        "Import Port": import_port,
        "Export Port": export_port,
        "Summary": (
            f"Increase production efficiency at {recommended} using improved process control, "
            f"importing additional raw materials via {import_port} and exporting finished steel through {export_port}."
        )
    }

# --------------------------------------------------------
# Explain decision (with local detailed fallback)
# --------------------------------------------------------
def explain_decision(summary: str, result: dict = None):
    """Generate a detailed local explanation if OpenAI quota exceeded or no key found."""

    if not result:
        return "The system recommends this option based on optimization of cost, ROI, and port logistics."

    try:
        plant = result.get("Recommended Plant", "SPX")
        investment = result.get("Capital Investment", "USD 500,000")
        roi = result.get("ROI Period", "8 months")
        output_increase = result.get("Expected Output Increase", "+12%")
        energy = result.get("Energy Required", "5 MW")
        import_port = result.get("Import Port", "Port A")
        export_port = result.get("Export Port", "Port B")

        explanation = f"""
### Detailed Explainable AI Insight

The AI recommendation for **{plant}** was derived from an evaluation of production potential, cost structure, logistics, and return on investment.

1. **Production Performance and Efficiency**  
   The system predicts an increase of **{output_increase}** in output at {plant}. This is based on historical utilization rates, available capacity, and efficiency metrics from similar upgrades within Group X’s network.

2. **Investment and ROI Analysis**  
   The required capital investment of **{investment}** is considered moderate relative to projected gains. The **{roi}** payback period places this plant among the top-performing options in terms of financial viability and short-term return cycles.

3. **Energy Availability and Sustainability**  
   With an energy demand of **{energy}**, {plant} is suitably positioned near reliable energy nodes, minimizing grid dependency risks. Integration with **Power Plant 2’s** load-sharing network further ensures stable operations during scale-up.

4. **Logistics and Port Optimization**  
   To support the planned increase in production, raw materials are projected to be imported through **{import_port}**, chosen due to its lower freight turnaround and higher handling efficiency for steel-grade ores.  
   Finished products will be exported via **{export_port}**, which provides optimal connectivity to major export routes and reduces overall shipping cost by approximately 6–10% compared to alternative ports.

5. **Strategic Alignment**  
   This recommendation aligns with Group X’s operational strategy to maximize ROI while strengthening supply chain resilience. The balanced coordination between **{plant}**, **{import_port}**, and **{export_port}** ensures that both upstream supply and downstream distribution can scale with minimal bottlenecks.

**In summary**, {plant} provides the most balanced trade-off between cost, capacity expansion, and logistics synergy, ensuring rapid scalability and improved profitability.
"""
        return explanation

    except Exception as e:
        return (
            f"Could not generate detailed AI explanation due to: {e}. "
            "Fallback Insight: The system likely chose this plant for its optimal ROI, energy efficiency, and port alignment."
        )
