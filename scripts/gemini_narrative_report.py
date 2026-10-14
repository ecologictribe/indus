import json
import pandas as pd
from google import genai
from google.genai import types

def generate_narrative_report(data_input: str, is_json: bool = True) -> str:
    """
    Takes JSON or CSV statistical data as text and generates an executive narrative report using Gemini.
    """
    system_instruction = """
You are an expert Data Analyst and Business Intelligence Communicator.
Your job is to transform raw numerical data and statistics into a high-level executive narrative.

When analyzing data:
1. Executive Summary: Provide a 2-3 sentence overarching story of the dataset.
2. Top Performers & Successes: Highlight key growth drivers and metrics exceeding targets.
3. Outliers & Risk Areas: Identify concerning trends (e.g., declining revenue, high churn rates).
4. Strategic Recommendations: Offer 2-3 actionable next steps based strictly on the metrics provided.

Formatting rules:
- Use clear Markdown headers and bullet points.
- Include exact percentage changes and financial numbers to ground the narrative.
"""

    data_format = "JSON" if is_json else "CSV"
    prompt = f"""
Analyze the following statistical dataset in {data_format} format and generate a narrative executive report:

```{data_format.lower()}
{data_input}
```
"""

    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        )
    )

    return response.text


if __name__ == "__main__":
    # Sample Statistical Dataset (JSON)
    sample_data = {
        "region": ["North America", "Europe", "Asia-Pacific", "Latin America"],
        "q1_revenue_usd": [1250000, 980000, 1420000, 450000],
        "q2_revenue_usd": [1400000, 910000, 1680000, 410000],
        "target_achievement_pct": [108.5, 91.2, 115.0, 82.0],
        "customer_churn_rate_pct": [2.1, 4.8, 1.9, 6.2],
        "marketing_spend_usd": [200000, 180000, 220000, 90000]
    }
    
    json_str = json.dumps(sample_data, indent=2)
    
    print("Generating Narrative Statistical Report using Gemini...\n")
    report = generate_narrative_report(json_str, is_json=True)
    print("=== NARRATIVE REPORT ===")
    print(report)
