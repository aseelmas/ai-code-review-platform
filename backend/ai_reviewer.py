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

    Source code around the issue:

    {issue.get("code_context", "No source context provided.")}

    Return ONLY valid JSON with exactly these fields:

    {{
    "explanation": "Explain why this issue matters in the context of the provided code.",
    "risk": "Describe the concrete risk created by this code.",
    "recommendation": "Explain what the developer should change.",
    "suggested_fix": "Provide a corrected Python code example based on the supplied source code."
    }}

    Important:
    - Base your review on the supplied source code.
    - Do not invent variables or behavior unless necessary.
    - Preserve the intent of the original code when suggesting a fix.
    - Keep the response concise.
    - Do not include markdown fences.
    - Do not include text outside the JSON.
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