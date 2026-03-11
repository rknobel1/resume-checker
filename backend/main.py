from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    AnalyzeRequest,
    AnalyzeResponse,
    PlanModeRequest,
    PlanModeResponse,
)
from parser import parse_resume, parse_job_description
from scoring import score_resume_against_jd
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

        resume_data = parse_resume(resume_text)
        score_result = score_resume_against_jd(resume_data, job_description)

        return AnalyzeResponse(
            score_breakdown=score_result,
            missing_keywords=score_result.missing_required + score_result.missing_preferred,
            weak_bullets=[],
            weak_bullet_details=[],
            suggestions=[],
            debug=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyze failed: {str(e)}")


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_resume(payload: AnalyzeRequest):
    try:
        resume_data = parse_resume(payload.resume_text)
        score_result = score_resume_against_jd(resume_data, payload.job_description)

        return AnalyzeResponse(
            score_breakdown=score_result,
            missing_keywords=score_result.missing_required + score_result.missing_preferred,
            weak_bullets=[],
            weak_bullet_details=[],
            suggestions=[],
            debug=None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyze failed: {str(e)}")


@app.post("/plan-mode/chat", response_model=PlanModeResponse)
def plan_mode_chat(req: PlanModeRequest):
    try:
        reply = plan_mode_reply(
            bullet_text=req.bullet_text,
            job_description=req.job_description,
            user_message=req.user_message,
            history=req.conversation_history or [],
        )
        return PlanModeResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan mode failed: {str(e)}")