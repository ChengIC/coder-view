import os
import json
from typing import Any, Dict, Optional

import requests


def summarize_with_llm(metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    base_url = os.getenv("LLM_API_BASE")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not base_url or not api_key:
        return None

    url = base_url.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt = (
        "You are a codebase auditor. Given metrics JSON, write a structured summary "
        "covering readability, reusability, robustness, and performance. Provide key risks, "
        "prioritized recommendations, and a fairness note about heuristic limits."
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(metrics)},
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            return {"text": "No summary returned from LLM."}
        # Attempt to parse JSON; if not JSON, wrap as text
        try:
            return json.loads(content)
        except Exception:
            return {"text": content}
    except Exception as e:
        return {"error": f"LLM request failed: {e}"}