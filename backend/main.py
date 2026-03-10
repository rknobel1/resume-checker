from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from models import (
    AnalyzeRequest,
    AnalyzeResponse,
    PlanModeRequest,
    PlanModeResponse,
)
from parser import parse_resume, parse_job_description
from scoring import score_resume
from suggestion_engine import generate_suggestions, plan_mode_reply
from pdf_utils import extract_text_from_pdf_bytes

app = FastAPI(title="Local ATS Resume App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze-pdf")
async def analyze_pdf(
    resume_pdf: UploadFile = File(...),
    job_description: str = Form(...)
):
    pdf_bytes = await resume_pdf.read()
    resume_text = extract_text_from_pdf_bytes(pdf_bytes)

    resume_data = parse_resume(resume_text)
    jd_data = parse_job_description(job_description)
    analysis = score_resume(resume_data, jd_data)

    return {
        "resume_text": resume_text,
        "score_breakdown": analysis["score_breakdown"].model_dump(),
        "missing_keywords": analysis["missing_keywords"],
        "weak_bullets": analysis["weak_bullets"],
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    resume_data = parse_resume(req.resume_text)
    jd_data = parse_job_description(req.job_description)

    analysis = score_resume(resume_data, jd_data)
    suggestions = generate_suggestions(
        weak_bullets=analysis["weak_bullets"],
        job_description=req.job_description,
    )

    return AnalyzeResponse(
        score_breakdown=analysis["score_breakdown"],
        missing_keywords=analysis["missing_keywords"],
        weak_bullets=analysis["weak_bullets"],
        suggestions=suggestions,
    )


@app.post("/plan-mode/chat", response_model=PlanModeResponse)
def plan_mode_chat(req: PlanModeRequest):
    reply = plan_mode_reply(
        bullet_text=req.bullet_text,
        job_description=req.job_description,
        user_message=req.user_message,
        history=req.conversation_history or [],
    )
    return PlanModeResponse(reply=reply)