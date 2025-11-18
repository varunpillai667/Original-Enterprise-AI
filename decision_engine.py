import os
import random
from openai import OpenAI

# Initialize the OpenAI client safely
def get_client():
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  No OpenAI API key found in environment.")
            return None
        return OpenAI(api_key=api_key)
    except Exception as e:
        print(f"⚠️  OpenAI client initialization failed: {e}")
        return None


client = get_client()


# ---------------------------------------------------------------------
# 1️⃣  Core Simulation Logic (mock business reasoning)
# ---------------------------------------------------------------------
def run_simulation(question: str):
    """
    Simulates how the enterprise AI framework analyzes a CEO query
    and returns an AI-driven business recommendation.
    """

    # Example mock reasoning to mimic a decision chain
    plants = ["SP1", "SP2", "SP3", "SP4"]
    recommended = random.choice(plants)
    increase = random.choice(["+8%", "+10%", "+12%", "+14%"])
    investment = random.choice(["USD 450,000", "USD 600,000", "USD 750,000"])
    roi = random.choice(["7 months", "9 months", "10 months"])
    energy = f"{random.randint(4, 7)} MW from Power Plant {random.randint(1, 3)}"

    summary = (
        f"Expand production at {recommended} using a compact rolling line "
        f"and improved process automation. Investment {investment} "
        f"expected ROI in {roi}."
    )

    return {
        "Recommended Plant": recommended,
        "Expected Output Increase": increase,
        "Capital Investment": investment,
        "ROI Period": roi,
        "Energy Required": energy,
        "Summary": summary
    }


# ---------------------------------------------------------------------
# 2️⃣  Explainable AI Layer
# ---------------------------------------------------------------------
def explain_decision(summary: str):
    """
    Uses GPT to generate an explainable summary of the AI's reasoning.
    Provides a local fallback if API quota or connectivity fails.
    """

    prompt = (
        "You are an enterprise AI analyst. Explain in simple, "
        "clear language why the following operational recommendation "
        "makes business sense:\n\n"
        f"Recommendation: {summary}\n\n"
        "Structure your answer as:\n"
        "- Key Reasoning\n"
        "- Expected Impact\n"
        "- Strategic Fit\n"
    )

    # If OpenAI client is unavailable, return fallback
    if not client:
        return (
            "⚠️  OpenAI client unavailable — using fallback.\n\n"
            f"The recommendation '{summary}' likely focuses on improving efficiency "
            "and increasing capacity with minimal capital investment. "
            "It balances resource optimization and operational ROI."
        )

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )
        return response.output[0].content[0].text.strip()

    except Exception as e:
        print(f"⚠️  Error generating AI explanation: {e}")
        return (
            f"⚠️  Could not generate AI explanation.\n"
            f"Reason: {str(e)}\n\n"
            f"Fallback Insight: The system probably selected this plant based on "
            "capacity utilization, low upgrade cost, and fastest payback potential."
        )
