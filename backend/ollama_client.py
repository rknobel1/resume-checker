import os
from typing import Optional

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL_DEFAULT", "qwen2.5:14b-instruct")
JD_STRUCTURER_MODEL = os.getenv("OLLAMA_MODEL_JD", DEFAULT_MODEL)
REWRITE_MODEL = os.getenv("OLLAMA_MODEL_REWRITE", DEFAULT_MODEL)
PLAN_MODE_MODEL = os.getenv("OLLAMA_MODEL_PLAN", DEFAULT_MODEL)


def get_model_for_task(task: Optional[str] = None) -> str:
    task = (task or "").strip().lower()

    task_model_map = {
        "jd_structuring": JD_STRUCTURER_MODEL,
        "rewrite_generation": REWRITE_MODEL,
        "plan_mode": PLAN_MODE_MODEL,
    }

    return task_model_map.get(task, DEFAULT_MODEL)


def ask_ollama(
    prompt: str,
    model: Optional[str] = None,
    *,
    task: Optional[str] = None,
    timeout: int = 120,
) -> str:
    selected_model = model or get_model_for_task(task)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": selected_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "format": "json"
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"].strip()