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
# Explain decision (with local fallback)
# --------------------------------------------------------
def explain_decision(summary: str, result: dict = None):
    """Generate a local explanation if OpenAI quota exceeded or no key found."""

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

        # Local heuristic explanation
        explanation = (
            f"The AI selected **{plant}** because it can achieve an estimated {output_increase} increase in output "
            f"with a moderate investment of {investment} and an ROI period of {roi}. "
            f"Energy needs of {energy} align well with available power resources, while logistics are optimized through "
            f"the import of raw materials via {import_port} and exports through {export_port}. "
            f"This recommendation balances cost, speed, and supply chain efficiency, ensuring smooth throughput from import to export."
        )

        return explanation

    except Exception as e:
        return (
            f"Could not generate full AI explanation due to: {e}. "
            "Fallback Insight: The system likely chose this plant for optimal ROI, minimal upgrade cost, "
            "and efficient logistics across its connected ports."
        )
