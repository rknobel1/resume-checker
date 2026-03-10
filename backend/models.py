from pydantic import BaseModel, Field
from typing import List, Optional


class AnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str


class ScoreBreakdown(BaseModel):
    keyword_relevance: float
    skills_match: float
    experience_alignment: float
    achievement_strength: float
    section_completeness: float
    ats_formatting: float
    overall_score: float


class Suggestion(BaseModel):
    id: str
    section: str
    original_text: str
    proposed_text: str
    reason: str
    estimated_score_impact: float
    confidence: float


class AnalyzeResponse(BaseModel):
    score_breakdown: ScoreBreakdown
    missing_keywords: List[str]
    weak_bullets: List[str]
    suggestions: List[Suggestion]


class PlanModeRequest(BaseModel):
    bullet_text: str
    job_description: str
    user_message: str
    conversation_history: Optional[List[str]] = Field(default_factory=list)


class PlanModeResponse(BaseModel):
    reply: str