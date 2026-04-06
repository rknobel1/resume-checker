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
from parser import parse_resume, parse_job_description
from scoring import score_resume_against_jd
from suggestion_engine import generate_suggestions, plan_mode_reply
from pdf_utils import extract_text_from_pdf_bytes
from bullet_scorer import score_bullet


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
    grouped_entries.extend(resume_data.get("experience_groups", []) or [])
    grouped_entries.extend(resume_data.get("project_groups", []) or [])

    # fallback for older parser output
    if not grouped_entries:
        grouped_entries = [
            {
                "section": "experience",
                "header": "Experience Entry 1",
                "bullets": resume_data.get("experience_bullets", []) or [],
            },
            {
                "section": "projects",
                "header": "Projects Entry 1",
                "bullets": resume_data.get("project_bullets", []) or [],
            },
        ]

    bullet_idx = 0

    for entry in grouped_entries:
        section_name = entry.get("section", "experience")
        entry_bullets = [b for b in (entry.get("bullets", []) or []) if b and b.strip()]

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
    experience_groups_raw = resume_data.get("experience_groups", []) or []
    project_groups_raw = resume_data.get("project_groups", []) or []

    experience_groups = [
        ParsedResumeEntry(
            section=group.get("section", "experience"),
            header=group.get("header", "Experience Entry"),
            subheader=group.get("subheader"),
            bullets=[b for b in (group.get("bullets", []) or []) if b and b.strip()],
        )
        for group in experience_groups_raw
    ]

    project_groups = [
        ParsedResumeEntry(
            section=group.get("section", "projects"),
            header=group.get("header", "Projects Entry"),
            subheader=group.get("subheader"),
            bullets=[b for b in (group.get("bullets", []) or []) if b and b.strip()],
        )
        for group in project_groups_raw
    ]

    parser_notes = []
    used_fallback_grouping = False

    synthetic_headers = {
        "Experience Entry 1",
        "Projects Entry 1",
    }

    if any(g.header in synthetic_headers for g in experience_groups + project_groups):
        used_fallback_grouping = True
        parser_notes.append(
            "Some entries may have been grouped using fallback headers because the parser could not confidently detect all role or project headers."
        )

    sections_found = list((resume_data.get("sections") or {}).keys())

    if not experience_groups and (resume_data.get("experience_text") or "").strip():
        parser_notes.append("Experience text was found, but no structured experience groups were extracted.")

    if not project_groups and (resume_data.get("projects_text") or "").strip():
        parser_notes.append("Project text was found, but no structured project groups were extracted.")

    return ParsedResumeSummary(
        summary_text=resume_data.get("summary", "") or "",
        skills=resume_data.get("skills", []) or [],
        sections_found=sections_found,
        experience_groups=experience_groups,
        project_groups=project_groups,
        education_text=resume_data.get("education_text", "") or "",
        certifications_text=resume_data.get("certifications_text", "") or "",
        experience_group_count=len(experience_groups),
        project_group_count=len(project_groups),
        used_fallback_grouping=used_fallback_grouping,
        parser_notes=parser_notes,
    )


def build_parsed_resume_summary(resume_data: dict) -> ParsedResumeSummary:
    projects = [
        ParsedProjectEntry(
            title=group.get("title", "") or "Untitled Project",
            metadata=group.get("metadata"),
            tech_stack=group.get("tech_stack"),
            bullets=[b for b in (group.get("bullets", []) or []) if b and b.strip()],
        )
        for group in (resume_data.get("project_groups", []) or [])
    ]

    experience = [
        ParsedExperienceEntry(
            organization=group.get("organization"),
            role=group.get("role", "") or "Experience Entry",
            dates=group.get("dates"),
            bullets=[b for b in (group.get("bullets", []) or []) if b and b.strip()],
        )
        for group in (resume_data.get("experience_groups", []) or [])
    ]

    notes = []
    if not projects and (resume_data.get("projects_text") or "").strip():
        notes.append("Project text was found, but no structured projects were extracted.")
    if not experience and (resume_data.get("experience_text") or "").strip():
        notes.append("Experience text was found, but no structured experience entries were extracted.")

    return ParsedResumeSummary(
        summary_text=resume_data.get("summary", "") or "",
        skills=resume_data.get("skills", []) or [],
        sections_found=list((resume_data.get("sections") or {}).keys()),
        projects=projects,
        experience=experience,
        education_text=resume_data.get("education_text", "") or "",
        certifications_text=resume_data.get("certifications_text", "") or "",
        project_count=len(projects),
        experience_count=len(experience),
        parser_notes=notes,
    )


def build_analyze_response(resume_text: str, job_description: str) -> AnalyzeResponse:
    resume_data = parse_resume(resume_text)
    jd_debug = parse_job_description(job_description)
    score_result = score_resume_against_jd(resume_data, job_description)

    weak_bullets, weak_bullet_details, bullet_reasons = analyze_weak_bullets(resume_data)

    suggestions = generate_suggestions(
        weak_bullets=weak_bullets,
        job_description=job_description,
        missing_skills=score_result.missing_required + score_result.missing_preferred,
        bullet_reasons=bullet_reasons,
        max_suggestions=5,
    )

    debug = DebugInfo(
        resume_skills=resume_data.get("skills", []),
        jd_required_skills=jd_debug.get("required_skills", []),
        jd_preferred_skills=jd_debug.get("preferred_skills", []),
        jd_all_skills=jd_debug.get("all_skills", []),
    )

    parsed_resume = build_parsed_resume_summary(resume_data)

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

        return build_analyze_response(resume_text, job_description)

    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_resume(payload: AnalyzeRequest):
    try:
        return build_analyze_response(payload.resume_text, payload.job_description)
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