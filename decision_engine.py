# decision_engine.py
# Updated for OpenAI Python SDK v1.0+
# Energy references corrected to use Power Plants instead of Ports.

from openai import OpenAI
import os
import random

# Initialize OpenAI client using Streamlit Secrets
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------------------------------------------------------
# 1️⃣ Run the enterprise decision simulation
# -----------------------------------------------------------------------------
def run_simulation():
    """
    Simulates an enterprise AI decision — for example, identifying
    which steel plant to expand production at, based on simplified logic.
    """
    plants = ["SP1", "SP2", "SP3", "SP4"]
    recommended = random.choice(plants)

    decisions = {
        "SP1": {
            "Expected Output Increase": "+12%",
            "Capital Investment": "USD 700,000",
            "ROI Period": "8 months",
            "Energy Required": "4 MW from Power Plant 1",
            "Summary": "Upgrade SP1 with a semi-automated casting unit to boost production by 12%."
        },
        "SP2": {
            "Expected Output Increase": "+9%",
            "Capital Investment": "USD 550,000",
            "ROI Period": "9 months",
            "Energy Required": "3 MW from Power Plant 2",
            "Summary": "Modernize SP2 with a new annealing section; moderate cost, stable ROI."
        },
        "SP3": {
            "Expected Output Increase": "+14%",
            "Capital Investment": "USD 600,000",
            "ROI Period": "7 months",
            "Energy Required": "5 MW from Power Plant 3",
            "Summary": "Expand production at SP3 using a compact rolling line. Investment 600,000 USD expected ROI in 7 months."
        },
        "SP4": {
            "Expected Output Increase": "+10%",
            "Capital Investment": "USD 450,000",
            "ROI Period": "10 months",
            "Energy Required": "4 MW from Power Plant 2",
            "Summary": "Optimize SP4 with an energy-efficient reheating furnace to cut cost and improve yield."
        }
    }

    selected_decision = decisions[recommended]
    return {
        "Recommended Plant": recommended,
        "Expected Output Increase": selected_decision["Expected Output Increase"],
        "Capital Investment": selected_decision["Capital Investment"],
        "ROI Period": selected_decision["ROI Period"],
        "Energy Required": selected_decision["Energy Required"],
        "Summary": selected_decision["Summary"]
    }

# -----------------------------------------------------------------------------
# 2️⃣ Explain the decision using GPT
# -----------------------------------------------------------------------------
def explain_decision(decision_summary):
    """
    Uses GPT (via OpenAI API) to provide an explainable AI insight
    based on the enterprise decision summary.
    """

    try:
        prompt = f"""
        You are an AI strategy analyst.
        Explain, in clear and professional terms, why this decision makes sense
        in the context of enterprise operations, resource utilization,
        and ROI optimization.

        Decision Summary:
        {decision_summary}

        Keep the explanation concise (around 100–150 words) and suitable for an executive report.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # lightweight GPT-4 model for rapid response
            messages=[
                {"role": "system", "content": "You are an expert AI business analyst specializing in industrial optimization."},
                {"role": "user", "content": prompt}
            ]
        )

        explanation = response.choices[0].message.content.strip()
        return explanation

    except Exception as e:
        return f"⚠️ Error generating explanation: {str(e)}"
