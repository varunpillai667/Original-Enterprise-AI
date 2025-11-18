import json
import os
import openai

# Secure API key retrieval (for Streamlit Cloud secrets)
openai.api_key = os.getenv("OPENAI_API_KEY")

def run_simulation():
    with open("mock_data.json") as f:
        data = json.load(f)

    plants = data["steel_plants"]

    for p in plants:
        p["efficiency_score"] = round(p["utilization"] / (p["capex_estimate_usd"] / 1e6), 3)

    best = max(plants, key=lambda x: x["efficiency_score"])

    recommendation = {
        "recommended_plant": best["plant_id"],
        "expected_output_increase": "+14%",
        "capex": f"USD {best['capex_estimate_usd']:,}",
        "roi_period": f"{best['roi_months']} months",
        "energy_required_mw": 5,
        "port_dependency": "Port 2",
        "narrative": f"Expand production at {best['plant_id']} using a compact rolling line. "
                     f"Investment {best['capex_estimate_usd']:,} USD expected ROI in {best['roi_months']} months."
    }
    return recommendation


def explain_decision(summary):
    """Generates a GPT-based explanation."""
    if not openai.api_key:
        return "⚠️ OpenAI API key not found. Please set it in Streamlit Secrets."

    prompt = f"Explain this business recommendation in executive language: {summary}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an enterprise AI assistant for manufacturing and energy optimization."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ Error generating explanation: {e}"
