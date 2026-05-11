import json
import re
from typing import List, Optional, Dict
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


def stringify_list_of_strings(list: List[str]) -> str:
    return ", ".join(list) if list else "None"


def build_rewrite_prompt(
    bullet: str,
    chat_history: List[dict],
    required_lines: List[str],
    preferred_lines: List[str],
    required_skills: List[str],
    preferred_skills: List[str],
    missing_skills: List[str],
    why_flagged: Optional[str] = None,
) -> str:
    missing_skills_text = stringify_list_of_strings(missing_skills)
    required_lines_text = stringify_list_of_strings(required_lines)
    preferred_lines_text = stringify_list_of_strings(preferred_lines)
    required_skills_text = stringify_list_of_strings(required_skills)
    preferred_skills_text = stringify_list_of_strings(preferred_skills)

    history_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history[-20:]
    )

    return f"""
You are improving a resume bullet for ATS alignment. Your task is to generate 3 suggestions to improve the given bullet point and more closely align to the job description.

Rules:
- Use only the original bullet, current draft, and gathered facts.
- Do not invent metrics, tools, outcomes, responsibilities, or scope.
- Generate exactly 3 options.
- Make them concise, action-oriented, and ATS-friendly.
- Return valid JSON only.

JSON Format:
{{
  "reply": "short assistant reply",
  "options": [
    "option 1",
    "option 2",
    "option 3"
  ],
  "current_bullet": "best current bullet"
}}

Use ONLY the following information.

Resume bullet:
{bullet}

Current chat history with the user: 
{history_text}

Missing skills from the job description:
{missing_skills_text}

Why this bullet was flagged:
{why_flagged or "General weakness / low ATS alignment"}

The following is a summary of the key points of the job description.

Required specifications:
{required_lines_text}

Preferred specifications:
{preferred_lines_text}

Required skills: 
{required_skills_text}

Preferred skills:
{preferred_skills_text}
""".strip()


def generate_suggestions(
    bullet: str,
    jd_json_summary: dict,
    missing_skills: Optional[List[str]] = None,
    bullet_reasons: Optional[List[str] | str] = None,
    chat_history: Optional[List[dict]] = None,
) -> List[Suggestion]:
    missing_skills = missing_skills or []
    chat_history = chat_history or []

    if isinstance(bullet_reasons, list):
        why_flagged = "; ".join(bullet_reasons)
    else:
        why_flagged = bullet_reasons

    prompt = build_rewrite_prompt(
        bullet=bullet,
        chat_history=chat_history,
        required_lines=jd_json_summary.get("required_lines", []),
        preferred_lines=jd_json_summary.get("preferred_lines", []),
        required_skills=jd_json_summary.get("required_skills", []),
        preferred_skills=jd_json_summary.get("preferred_skills", []),
        missing_skills=missing_skills,
        why_flagged=why_flagged,
    )

    try:
        raw = ask_ollama(prompt, task="rewrite_generation")
        parsed = extract_json(raw)

        options = parsed.get("options", [])
        if not isinstance(options, list):
            options = []

        options = [str(opt).strip() for opt in options[:3] if str(opt).strip()]

        suggestions: List[Suggestion] = []

        for idx, option in enumerate(options, start=1):
            suggestions.append(
                Suggestion(
                    id=f"sugg-{idx}",
                    section="experience",
                    original_text=bullet,
                    proposed_text=option,
                    reason=parsed.get(
                        "reply",
                        "Improved wording for clarity and ATS alignment.",
                    ),
                    estimated_score_impact=estimate_score_impact(
                        original_text=bullet,
                        proposed_text=option,
                        missing_skills=missing_skills,
                    ),
                    confidence=0.75,
                )
            )

        return suggestions

    except Exception:
        return [
            Suggestion(
                id="sugg-1",
                section="experience",
                original_text=bullet,
                proposed_text=bullet,
                reason="Model could not confidently rewrite this bullet yet.",
                estimated_score_impact=0.0,
                confidence=0.0,
            )
        ]


def build_plan_mode_prompt(
    bullet_text: str,
    current_bullet: str,
    bullet_reasons: List[str],
    job_description: str,
    user_message: str,
    history: List[dict],
) -> str:
    history_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in history[-20:]
    )
    reasons_text = "; ".join(bullet_reasons) if bullet_reasons else "General weakness"

    return f"""
You are helping a user strengthen a resume bullet for ATS alignment.

Rules:
- Do not invent facts, metrics, scope, tools, outcomes, or ownership.
- Ask only one focused question at a time if important details are missing.
- Prioritize discovering, in this order:
  1. scope
  2. tools/technologies
  3. ownership
  4. measurable outcome
- If the user asks a vague follow-up such as:
  - "what technologies?"
  - "like what?"
  - "examples?"
  - "which ones?"
  - "can you list common technologies because I forgot?"
  then do NOT generate bullet options.
- For vague follow-ups, do NOT list generic technologies unless they are clearly supported by the bullet or prior conversation.
- If the user seems unsure or forgot details, help them remember by asking a narrower clarification question tied to the bullet.
- Never use generic examples as a substitute for clarification.
- Keep the response concise and practical.
- Return valid JSON only.

Decide between these modes:

1. Use "question" when important bullet details are still missing.
2. Use "clarify" when the user's latest message is vague, ambiguous, forgetful, or asks for examples not grounded in the bullet/context.
3. Use "ready" only when enough grounded detail exists to write strong bullets without inventing facts.

If more detail is needed, return:
{{
  "mode": "question",
  "reply": "short assistant reply",
  "question": "one focused question",
  "options": [],
  "current_bullet": "{current_bullet}"
}}

If the user is asking for clarification/examples but the answer is not grounded enough, return:
{{
  "mode": "clarify",
  "reply": "short assistant reply",
  "question": "one focused clarification question tied to the bullet",
  "options": [],
  "current_bullet": "{current_bullet}"
}}

If enough detail exists, return:
{{
  "mode": "ready",
  "reply": "short assistant reply",
  "question": null,
  "options": [],
  "current_bullet": "{current_bullet}"
}}

Original weak bullet:
{bullet_text}

Current draft bullet:
{current_bullet}

Why it was flagged:
{reasons_text}

Job description:
{job_description}

Conversation so far:
{history_text}

Latest user message:
{user_message}
""".strip()


def plan_mode_reply(
    bullet_text: str,
    current_bullet: str,
    bullet_reasons: List[str],
    jd_json_summary: dict,
    user_message: str,
    history: List[dict],
) -> dict:

    try:
        prompt = build_plan_mode_prompt(
            bullet_text=bullet_text,
            current_bullet=current_bullet,
            bullet_reasons=bullet_reasons,
            job_description=jd_json_summary.get("job_description"),
            user_message=user_message,
            history=history,
        )
        raw = ask_ollama(prompt, task="plan_mode")
        parsed = extract_json(raw)

        mode = parsed.get("mode", "question")
        reply = str(parsed.get("reply", "")).strip() or "Let’s improve this bullet."
        question = parsed.get("question")
        next_bullet = str(parsed.get("current_bullet", current_bullet)).strip()

        if mode not in {"question", "clarify", "ready"}:
            mode = "question"

        if mode != "ready": 
            return {
                "mode": mode,
                "reply": reply,
                "question": question,
                "options": [],
                "current_bullet": next_bullet or current_bullet,
            }
        
        suggestions = generate_suggestions(
            bullet=next_bullet or current_bullet,
            jd_json_summary=jd_json_summary,
            missing_skills=(
                jd_json_summary.get("missing_required", [])
                + jd_json_summary.get("missing_preferred", [])
            ),
            bullet_reasons=bullet_reasons,
            chat_history=history,
        )

        options = [s.proposed_text for s in suggestions]

        return {
            "mode": "options",
            "reply": "Here are three stronger options.",
            "question": None,
            "options": options,
            "current_bullet": next_bullet or current_bullet,
        }

    except Exception as e:
        return {
            "mode": "question",
            "reply": "I couldn’t parse the planning response cleanly, so let’s continue with a simpler follow-up.",
            "question": "What was the main result, tool, or measurable impact of this work?",
            "options": [],
            "current_bullet": current_bullet,
            "debug_error": str(e),
        }