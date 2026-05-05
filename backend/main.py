from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import traceback

from models import (
    AnalyzeRequest,
    AnalyzeResponse,
    PlanModeRequest,
    PlanModeResponse,
    WeakBullet,
    DebugInfo,
    ParsedProjectEntry,
    ParsedExperienceEntry,
    ParsedResumeSummary,
)

from scoring import score_resume_against_jd
from suggestion_engine import generate_suggestions, plan_mode_reply
from pdf_utils import extract_text_from_pdf_bytes
from bullet_scorer import score_bullet
from build_json_summaries import build_resume_json_summary, build_jd_json_summary

import json


app = FastAPI(title="Local ATS Resume App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def analyze_weak_bullets(resume_data: dict):
    weak_bullets = []
    weak_bullet_details = []
    bullet_reasons = {}

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
                bullet_reasons[bullet] = "; ".join(reasons)

    return weak_bullets, weak_bullet_details, bullet_reasons

def build_parsed_resume_summary(resume_data: dict) -> ParsedResumeSummary:
    def clean_list(items):
        return [x.strip() for x in (items or []) if isinstance(x, str) and x.strip()]

    def join_entries(entries: list[dict], keys: list[str]) -> str:
        lines = []
        for entry in entries or []:
            parts = []
            for key in keys:
                value = entry.get(key)
                if isinstance(value, list):
                    value = ", ".join(clean_list(value))
                if value:
                    parts.append(str(value).strip())
            if parts:
                lines.append(" | ".join(parts))
        return "\n".join(lines)

    projects = [
        ParsedProjectEntry(
            title=project.get("Title", "") or "Untitled Project",
            metadata=None,
            tech_stack=", ".join(clean_list(project.get("Technologies", []))),
            bullets=clean_list(project.get("Details", [])),
        )
        for project in (resume_data.get("Projects", []) or [])
    ]

    experience = [
        ParsedExperienceEntry(
            organization=exp.get("Company", ""),
            role=exp.get("Title", "") or "Experience Entry",
            dates=exp.get("Dates", ""),
            bullets=clean_list(exp.get("Details", [])),
        )
        for exp in (resume_data.get("Experience", []) or [])
    ]

    skills = []
    for group in resume_data.get("Skills", []) or []:
        skills.extend(clean_list(group.get("Skills", [])))

    sections_found = [
        key for key, value in resume_data.items()
        if value not in (None, "", [], {})
    ]

    notes = []
    if not projects and resume_data.get("Projects"):
        notes.append("Project data was found, but no structured projects were extracted.")
    if not experience and resume_data.get("Experience"):
        notes.append("Experience data was found, but no structured experience entries were extracted.")

    return ParsedResumeSummary(
        summary_text=resume_data.get("Summary", "") or "",
        skills=skills,
        sections_found=sections_found,
        projects=projects,
        experience=experience,
        education_text=join_entries(
            resume_data.get("Education", []),
            ["University", "Degree", "Dates", "Minor", "GPA"],
        ),
        certifications_text=join_entries(
            resume_data.get("Certifications", []),
            ["Certification", "Details"],
        ),
        project_count=len(projects),
        experience_count=len(experience),
        parser_notes=notes,
    )


def build_analyze_response_from_json(resume_json_summary: dict, jd_json_summary: dict) -> AnalyzeResponse:
    
    score_result = score_resume_against_jd(resume_json_summary, jd_json_summary)

    weak_bullets, weak_bullet_details, bullet_reasons = analyze_weak_bullets(resume_json_summary)

    suggestions = generate_suggestions(
        weak_bullets=weak_bullets,
        job_description=jd_json_summary.get("job_description"),
        missing_skills=score_result.missing_required + score_result.missing_preferred,
        bullet_reasons=bullet_reasons,
        max_suggestions=5,
    )

    debug = DebugInfo(
        resume_skills=resume_json_summary.get("skills", []),
        jd_required_skills=jd_json_summary.get("required_skills", []),
        jd_preferred_skills=jd_json_summary.get("preferred_skills", []),
        jd_all_skills=jd_json_summary.get("all_skills", []),
    )

    parsed_resume = build_parsed_resume_summary(resume_json_summary)

    return AnalyzeResponse(
        score_breakdown=score_result,
        missing_keywords=score_result.missing_required + score_result.missing_preferred,
        weak_bullets=weak_bullets,
        weak_bullet_details=weak_bullet_details,
        suggestions=suggestions,
        parsed_resume=parsed_resume,
        debug=debug,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze-pdf", response_model=AnalyzeResponse)
async def analyze_pdf(
    resume_pdf: UploadFile = File(...),
    job_description: str = Form(...)
):
    try:
        pdf_bytes = await resume_pdf.read()
        resume_text = extract_text_from_pdf_bytes(pdf_bytes)

        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
        
        resume_json_summary = build_resume_json_summary(parsed_text=resume_text)
        print(json.dumps(resume_json_summary, indent=2))
        jd_json_summary = build_jd_json_summary(parsed_text=job_description)
        jd_json_summary["job_description"] = job_description
        print(json.dumps(jd_json_summary, indent=2))

        analysis = build_analyze_response_from_json(resume_json_summary, jd_json_summary)
        
        return analysis

    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plan-mode/chat", response_model=PlanModeResponse)
def plan_mode_chat(req: PlanModeRequest):
    try:
        result = plan_mode_reply(
            bullet_text=req.bullet_text,
            current_bullet=req.current_bullet or req.bullet_text,
            bullet_reasons=req.bullet_reasons,
            job_description=req.job_description,
            user_message=req.user_message,
            history=[msg.model_dump() for msg in req.conversation_history],
        )
        return PlanModeResponse(**result)
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))