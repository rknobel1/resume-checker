import json
import re
from typing import Dict, Any
from models import JobDescriptionStructured
from ollama_client import ask_ollama

PROMPT = """
You are an expert recruiter and ATS parser.

Extract the job description into strict JSON.

Rules:
- Separate required vs preferred requirements.
- Normalize duplicate skills where appropriate.
- Include responsibilities as requirements when they describe expected work.
- Do not invent requirements not present in the job description.
- Return only valid JSON.
- Use "experience" for explicit years-of-experience or "experience with X" requirements.

JSON schema:
{
  "job_title": "string or null",
  "seniority": "intern|junior|mid|senior|staff|lead|manager|null",
  "min_years_experience": "integer or null",
  "requirements": [
    {
      "text": "Python",
      "category": "skill|tool|responsibility|domain|education|certification|experience",
      "importance": "required|preferred",
      "normalized_key": "python"
    }
  ]
}
"""

def _safe_json_loads(text: str) -> Dict[str, Any]:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)

def structure_job_description(job_description: str) -> JobDescriptionStructured:
    prompt = f"""
{PROMPT}

Job description:
{job_description}

Return ONLY valid JSON.
""".strip()

    response = ask_ollama(prompt)
    data = _safe_json_loads(response)
    return JobDescriptionStructured(**data)