from pydantic import BaseModel, Field, ValidationError

from models import WeakBullet
from ollama_client import ask_ollama
from bullet_scorer import score_bullet

import json

class AIWeakBulletFinding(BaseModel):
    bullet_index: int = Field(..., ge=0)
    reasons: list[str]


class AIWeakBulletResponse(BaseModel):
    weak_bullets: list[AIWeakBulletFinding]


def analyze_weak_bullets(resume_data: dict):
    weak_bullets = []
    weak_bullet_details = []

    grouped_entries = []

    for exp in resume_data.get("Experience", []) or []:
        grouped_entries.append({
            "section": "experience",
            "header": exp.get("Title", "Experience Entry"),
            "bullets": exp.get("Details", []) or [],
        })

    for project in resume_data.get("Projects", []) or []:
        grouped_entries.append({
            "section": "projects",
            "header": project.get("Title", "Project Entry"),
            "bullets": project.get("Details", []) or [],
        })

    bullet_idx = 0

    for entry in grouped_entries:
        section_name = entry.get("section", "experience")
        entry_bullets = [
            b.strip()
            for b in (entry.get("bullets", []) or [])
            if isinstance(b, str) and b.strip()
        ]

        for bullet in entry_bullets:
            bullet_idx += 1
            s = score_bullet(bullet, context_bullets=entry_bullets)
            reasons = []

            if s["score"] < 58 or s.get("fragment_penalty", 0.0) >= 0.15:
                if s["starts_weak"] >= 1.0:
                    reasons.append("Starts with a weak phrase")
                elif s["starts_strong"] == 0.0 and s.get("fragment_penalty", 0.0) >= 0.15:
                    reasons.append("Reads more like a fragment than an action-focused bullet")

                if s["has_metric"] == 0.0 and s["impact"] == 0.0:
                    if s.get("has_metric_context", 0.0) >= 1.0:
                        reasons.append("Result is clearer elsewhere in this role/project; this bullet could stand on its own more")
                    else:
                        reasons.append("Could show clearer measurable results or outcome")

                if s["has_tool"] == 0.0:
                    if s.get("has_tool_context", 0.0) >= 1.0:
                        reasons.append("Tools are implied elsewhere in this role/project; consider repeating them here for clarity")
                    else:
                        reasons.append("Could be more explicit about tools or technologies used")

                if s["ownership"] == 0.0 and s["starts_strong"] == 0.0:
                    reasons.append("Ownership or direct contribution is not very explicit")

                if s["specificity"] < 0.45:
                    reasons.append("Bullet is somewhat vague or underspecified")

            if reasons:
                bullet_id = f"weak-{bullet_idx}"
                weak_bullets.append(bullet)
                weak_bullet_details.append(
                    WeakBullet(
                        id=bullet_id,
                        text=bullet,
                        section=section_name,
                        reasons=reasons,
                    )
                )
                

    return weak_bullets, weak_bullet_details


def identify_weak_bullets_ai(section: str, header: str, details: str, bullets: list[str]) -> AIWeakBulletResponse:
    bullet_text = "\n".join(
        f"{i}. {bullet}"
        for i, bullet in enumerate(bullets)
    )

    prompt = f"""
You are an expert level ATS reviewer.
Your task is to find weak resume bullets from one {section} entry.

Entry title:
{header}

Additional information:
{details}

Bullets:
{bullet_text}

Identify only the weak bullets.

A weak bullet may:
- be vague
- lack measurable impact
- lack ownership
- read like a fragment
- fail to explain tools, methods, or outcome
- be weaker than the surrounding bullets in the same entry

Return JSON only in this exact shape:

{{
  "weak_bullets": [
    {{
      "bullet_index": 0,
      "reasons": ["Could show clearer measurable results or outcome"]
    }}
  ]
}}

Rules:
- bullet_index must match the bullet number above.
- Do not rewrite bullets.
- Do not invent new bullet text.
- Use short reason strings.
- If no bullets are weak, return {{"weak_bullets": []}}.
"""

    raw = ask_ollama(prompt, task="weak_bullets")

    try:
        data = json.loads(raw)
        return AIWeakBulletResponse.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return AIWeakBulletResponse(weak_bullets=[])


def analyze_weak_bullets_with_ai(resume_data: dict):
    weak_bullets = []
    weak_bullet_details = []

    grouped_entries = []

    for exp in resume_data.get("Experience", []) or []:
        grouped_entries.append({
            "section": "experience",
            "header": exp.get("Title", "Experience Entry"),
            "details": exp.get("Dates", ""),
            "bullets": exp.get("Details", []) or [],
        })

    for project in resume_data.get("Projects", []) or []:
        grouped_entries.append({
            "section": "projects",
            "header": project.get("Title", "Project Entry"),
            "details": project.get("Technologies", ""),
            "bullets": project.get("Details", []) or [],
        })

    global_bullet_idx = 0
    
    for entry in grouped_entries:
        section_name = entry.get("section", "experience")
        header = entry.get("header", "Entry")
        details = entry.get("details", "")
        entry_bullets = [
            b.strip()
            for b in (entry.get("bullets", []) or [])
            if isinstance(b, str) and b.strip()
        ]

        ai_result = identify_weak_bullets_ai(
            section=section_name,
            header=header,
            details=details,
            bullets=entry_bullets,
        )

        weak_indexes = {
            finding.bullet_index: finding.reasons
            for finding in ai_result.weak_bullets
            if 0 <= finding.bullet_index < len(entry_bullets)
        }

        for local_idx, bullet in enumerate(entry_bullets):
            global_bullet_idx += 1

            if local_idx not in weak_indexes:
                continue

            bullet_id = f"weak-{global_bullet_idx}"
            reasons = weak_indexes[local_idx]

            weak_bullets.append(bullet)
            weak_bullet_details.append(
                WeakBullet(
                    id=bullet_id,
                    text=bullet,
                    section=section_name,
                    reasons=reasons,
                )
            )  

    return weak_bullets, weak_bullet_details