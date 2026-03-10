import json
import re
from typing import List
from models import Suggestion
from ollama_client import ask_ollama


def extract_json(text: str) -> dict:
    """
    Best-effort JSON extraction for local models.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def build_rewrite_prompt(bullet: str, job_description: str) -> str:
    return f"""
You are improving a resume bullet for ATS alignment.

Rules:
- Do not invent tools, metrics, responsibilities, or outcomes.
- Only use details present in the bullet.
- You may improve wording, clarity, and action verbs.
- Keep it concise and professional.
- Return valid JSON only.

Required JSON format:
{{
  "proposed_text": "string",
  "reason": "string",
  "estimated_score_impact": 0,
  "confidence": 0.0
}}

Resume bullet:
{bullet}

Job description:
{job_description}
""".strip()


def generate_suggestions(weak_bullets: List[str], job_description: str) -> List[Suggestion]:
    suggestions: List[Suggestion] = []

    for idx, bullet in enumerate(weak_bullets[:5], start=1):
        prompt = build_rewrite_prompt(bullet, job_description)

        try:
            raw = ask_ollama(prompt)
            parsed = extract_json(raw)

            suggestions.append(
                Suggestion(
                    id=f"sugg-{idx}",
                    section="experience",
                    original_text=bullet,
                    proposed_text=parsed["proposed_text"],
                    reason=parsed["reason"],
                    estimated_score_impact=float(parsed.get("estimated_score_impact", 2.0)),
                    confidence=float(parsed.get("confidence", 0.7)),
                )
            )
        except Exception:
            suggestions.append(
                Suggestion(
                    id=f"sugg-{idx}",
                    section="experience",
                    original_text=bullet,
                    proposed_text=bullet,
                    reason="Model could not confidently rewrite this bullet yet.",
                    estimated_score_impact=0.0,
                    confidence=0.0,
                )
            )

    return suggestions


def plan_mode_reply(bullet_text: str, job_description: str, user_message: str, history: List[str]) -> str:
    history_text = "\n".join(history[-8:])

    prompt = f"""
You are helping a user strengthen a resume bullet.

Rules:
- Ask one focused question at a time.
- Do not invent facts.
- Prioritize discovering:
  1. scope
  2. tools/technologies
  3. ownership
  4. measurable outcome
- If enough detail is available, propose 2 improved bullet options.

Current weak bullet:
{bullet_text}

Job description:
{job_description}

Conversation so far:
{history_text}

Latest user message:
{user_message}
""".strip()

    return ask_ollama(prompt)