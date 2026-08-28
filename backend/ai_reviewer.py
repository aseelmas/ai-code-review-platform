import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def generate_ai_review(issue: dict) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are a senior Python code reviewer.

Analyze the following static-analysis finding.

Rule: {issue.get("rule")}
Severity: {issue.get("severity")}
Line: {issue.get("line")}
Message: {issue.get("message")}

Return ONLY valid JSON with exactly these fields:

{{
  "explanation": "Short explanation of why the issue matters.",
  "risk": "Short description of the risk.",
  "recommendation": "Practical recommendation.",
  "suggested_fix": "A short Python code example showing a safer alternative."
}}

Do not include markdown fences.
Do not include text outside the JSON.
"""

    response = client.responses.create(
        model="gpt-5.4",
        input=prompt,
    )

    try:
        return json.loads(response.output_text)
    except json.JSONDecodeError:
        return {
            "explanation": response.output_text,
            "risk": "Unable to parse structured AI response.",
            "recommendation": "Review the generated explanation manually.",
            "suggested_fix": "",
        }