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

    all_bullets = resume_data.get("all_bullets", []) or []

    for idx, bullet in enumerate(all_bullets, start=1):
        s = score_bullet(bullet)
        reasons = []

        if s["score"] < 58 or s.get("fragment_penalty", 0.0) >= 0.15:
            if s["starts_weak"] >= 1.0:
                reasons.append("Starts with a weak phrase")
            elif s["starts_strong"] == 0.0 and s.get("fragment_penalty", 0.0) >= 0.15:
                reasons.append("Reads more like a fragment than an action-focused bullet")

            if s["has_metric"] == 0.0 and s["impact"] == 0.0:
                reasons.append("Could show clearer measurable results or outcome")

            if s["has_tool"] == 0.0:
                reasons.append("Could be more explicit about tools or technologies used")

            if s["ownership"] == 0.0 and s["starts_strong"] == 0.0:
                reasons.append("Ownership or direct contribution is not very explicit")

            if s["specificity"] < 0.45:
                reasons.append("Bullet is somewhat vague or underspecified")

        if reasons:
            bullet_id = f"weak-{idx}"
            weak_bullets.append(bullet)
            weak_bullet_details.append(
                WeakBullet(
                    id=bullet_id,
                    text=bullet,
                    section="experience",
                    reasons=reasons,
                )
            )
            bullet_reasons[bullet] = "; ".join(reasons)

    return weak_bullets, weak_bullet_details, bullet_reasons


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

    return AnalyzeResponse(
        score_breakdown=score_result,
        missing_keywords=score_result.missing_required + score_result.missing_preferred,
        weak_bullets=weak_bullets,
        weak_bullet_details=weak_bullet_details,
        suggestions=suggestions,
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