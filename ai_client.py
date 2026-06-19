from __future__ import annotations

import os

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


class AIClientError(RuntimeError):
    pass


def ask_llama(
    question: str,
    context: str,
    columns: list[str],
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> str:

    key = api_key or os.getenv("NVIDIA_API_KEY")

    if not key:
        raise AIClientError("Missing NVIDIA_API_KEY")

    try:
        from openai import OpenAI
    except ImportError:
        raise AIClientError(
            "Install openai package: pip install openai"
        )

    client = OpenAI(
        base_url=NVIDIA_BASE_URL,
        api_key=key,
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.1,
        max_tokens=1000,
        messages=[
            {
                "role": "system",
                "content": f"""
You are a data analyst.

Available columns:
{', '.join(columns)}

If user requests visualization,
return ONLY JSON.

Examples:

{{
  "action":"visualize",
  "chart":"bar",
  "x":"COUNTRY",
  "y":"SALES",
  "title":"Sales by Country"
}}

{{
  "action":"visualize",
  "chart":"scatter",
  "x":"SALES",
  "y":"PROFIT",
  "title":"Sales vs Profit"
}}

Use ONLY columns from the available list.

For non-visualization questions,
answer normally.
"""
            },
            {
                "role": "user",
                "content": f"{context}\n\nQuestion: {question}"
            }
        ]
    )

    return response.choices[0].message.content