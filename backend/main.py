from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import traceback

from models import (
    AnalyzeResponse,
    PlanModeRequest,
    PlanModeResponse,
    DebugInfo,
    ParsedProjectEntry,
    ParsedExperienceEntry,
    ParsedResumeSummary,
)

from scoring import score_resume_against_jd, score_resume_against_jd_ai
from suggestion_engine import plan_mode_reply
from pdf_utils import extract_text_from_pdf_bytes
from build_json_summaries import build_resume_json_summary, build_jd_json_summary
from finding_weak_bullets import analyze_weak_bullets, analyze_weak_bullets_with_ai

app = FastAPI(title="Local ATS Resume App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def build_analyze_response_from_json(resume_json_summary: dict, jd_json_summary: dict, scoring_mode_ai: bool, weak_bullet_mode_ai: bool) -> AnalyzeResponse:
    
    if scoring_mode_ai:
        score_result = score_resume_against_jd_ai(resume_json_summary, jd_json_summary)
        print("Scoring results with AI")
    else: 
        score_result = score_resume_against_jd(resume_json_summary, jd_json_summary)
        print("Scoring results deterministically")

    if weak_bullet_mode_ai:
        weak_bullets, weak_bullet_details = analyze_weak_bullets_with_ai(resume_json_summary)
        print("Finding weak bullets with AI")
    else:
        weak_bullets, weak_bullet_details = analyze_weak_bullets(resume_json_summary)
        print("Finding weak bullets deterministically")

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
        parsed_resume=parsed_resume,
        jd_json_summary = jd_json_summary,
        debug=debug,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze-pdf", response_model=AnalyzeResponse)
async def analyze_pdf(
    resume_pdf: UploadFile = File(...),
    job_description: str = Form(...),
    scoring_mode_ai: bool = Form(True),
    weak_bullet_mode_ai: bool = Form(True)
):
    try:
        pdf_bytes = await resume_pdf.read()
        resume_text = extract_text_from_pdf_bytes(pdf_bytes)

        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
        
        resume_json_summary = build_resume_json_summary(parsed_text=resume_text)
        print("Parsed Resume")

        jd_json_summary = build_jd_json_summary(parsed_text=job_description)
        jd_json_summary["job_description"] = job_description
        print("Parsed Job Description")

        analysis = build_analyze_response_from_json(resume_json_summary, jd_json_summary, scoring_mode_ai, weak_bullet_mode_ai)
        print("Built analysis")
        
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
            jd_json_summary=req.jd_json_summary,
            user_message=req.user_message,
            history=[msg.model_dump() for msg in req.conversation_history],
        )
        return PlanModeResponse(**result)
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))