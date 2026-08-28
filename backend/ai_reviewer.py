import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def generate_ai_review(issue: dict) -> str:
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

Explain:
1. Why this issue matters.
2. What risk it creates.
3. How the developer should improve it.

Keep the answer concise and practical.
"""

    response = client.responses.create(
        model="gpt-5.4",
        input=prompt,
    )

    return response.output_text