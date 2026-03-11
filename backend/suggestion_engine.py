import json
import re
from typing import List, Optional
from models import Suggestion
from ollama_client import ask_ollama


def extract_json(text: str) -> dict:
    """
    More robust best-effort JSON extraction for local models.
    Tries:
    1. full response as JSON
    2. fenced ```json block
    3. first balanced {...} object
    """
    text = text.strip()

    # 1. direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. fenced json block
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    # 3. first non-greedy object
    obj = re.search(r"\{.*?\}", text, re.DOTALL)
    if obj:
        return json.loads(obj.group(0))

    raise ValueError("No JSON object found in model output")


def estimate_score_impact(
    original_text: str,
    proposed_text: str,
    missing_skills: List[str],
) -> float:
    """
    Heuristic estimate computed in code, not trusted to the model.
    """
    orig_low = original_text.lower()
    prop_low = proposed_text.lower()

    gain = 0.0

    # added missing skill language
    for skill in missing_skills[:5]:
        if skill.lower() not in orig_low and skill.lower() in prop_low:
            gain += 2.0

    # stronger verb at start
    strong_verbs = (
        "built", "developed", "designed", "implemented", "optimized",
        "improved", "created", "automated", "led", "deployed", "analyzed",
        "engineered", "launched", "reduced", "increased", "migrated", "owned"
    )
    first_word = prop_low.split()[0] if prop_low.split() else ""
    if first_word in strong_verbs:
        gain += 1.0

    # metric presence
    if not re.search(r"\d+%|\d+\b", orig_low) and re.search(r"\d+%|\d+\b", prop_low):
        gain += 1.5

    return round(min(gain, 8.0), 1)


def build_rewrite_prompt(
    bullet: str,
    job_description: str,
    missing_skills: List[str],
    why_flagged: Optional[str] = None,
) -> str:
    missing_skills_text = ", ".join(missing_skills[:8]) if missing_skills else "None"

    return f"""
You are improving a resume bullet for ATS alignment.

Rules:
- Do not invent tools, metrics, responsibilities, outcomes, team size, or scope.
- Only use facts already present in the bullet.
- You may improve wording, clarity, ordering, and action verbs.
- If a relevant keyword from the target role is already implied by the bullet, you may phrase it more explicitly.
- Do not add a metric unless the original bullet already contains measurable evidence.
- Keep it concise and professional.
- Return valid JSON only.

Target missing skills:
{missing_skills_text}

Why this bullet was flagged:
{why_flagged or "General weakness / low ATS alignment"}

Required JSON format:
{{
  "proposed_text": "string",
  "reason": "string",
  "confidence": 0.0
}}

Resume bullet:
{bullet}

Job description:
{job_description}
""".strip()


def generate_suggestions(
    weak_bullets: List[str],
    job_description: str,
    missing_skills: Optional[List[str]] = None,
    bullet_reasons: Optional[dict] = None,
    max_suggestions: int = 5,
) -> List[Suggestion]:
    suggestions: List[Suggestion] = []
    missing_skills = missing_skills or []
    bullet_reasons = bullet_reasons or {}

    for idx, bullet in enumerate(weak_bullets[:max_suggestions], start=1):
        prompt = build_rewrite_prompt(
            bullet=bullet,
            job_description=job_description,
            missing_skills=missing_skills,
            why_flagged=bullet_reasons.get(bullet),
        )

        try:
            raw = ask_ollama(prompt)
            parsed = extract_json(raw)

            proposed_text = parsed.get("proposed_text", bullet).strip()
            reason = parsed.get("reason", "Improved wording for clarity and ATS alignment.").strip()
            confidence = float(parsed.get("confidence", 0.7))

            suggestions.append(
                Suggestion(
                    id=f"sugg-{idx}",
                    section="experience",
                    original_text=bullet,
                    proposed_text=proposed_text,
                    reason=reason,
                    estimated_score_impact=estimate_score_impact(
                        original_text=bullet,
                        proposed_text=proposed_text,
                        missing_skills=missing_skills,
                    ),
                    confidence=confidence,
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

def build_plan_mode_prompt(
    bullet_text: str,
    job_description: str,
    user_message: str,
    history: List[str],
) -> str:
    history_text = "\n".join(history[-8:])

    return f"""
You are helping a user strengthen a resume bullet.

Rules:
- Ask one focused question at a time if key details are missing.
- Do not invent facts.
- Prioritize discovering, in this order:
  1. scope
  2. tools/technologies
  3. ownership
  4. measurable outcome
- Once enough detail exists, stop asking questions and provide exactly 3 improved bullet options.
- Keep responses concise and practical.

Output format:
- If more detail is needed, output:
QUESTION: <one focused question>

- If enough detail is available, output:
OPTION 1: <bullet>
OPTION 2: <bullet>
OPTION 3: <bullet>

Current weak bullet:
{bullet_text}

Job description:
{job_description}

Conversation so far:
{history_text}

Latest user message:
{user_message}
""".strip()


def plan_mode_reply(
    bullet_text: str,
    job_description: str,
    user_message: str,
    history: List[str],
) -> str:
    prompt = build_plan_mode_prompt(
        bullet_text=bullet_text,
        job_description=job_description,
        user_message=user_message,
        history=history,
    )
    return ask_ollama(prompt)