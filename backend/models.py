from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
import re


class AnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str


class Suggestion(BaseModel):
    id: str
    section: str
    original_text: str
    proposed_text: str
    reason: str
    estimated_score_impact: float
    confidence: float

class RequirementMatch(BaseModel):
    requirement: str
    category: str
    importance: str
    matched: bool
    score: float
    evidence_score: int
    best_evidence: Optional[str] = None
    notes: Optional[str] = None

class ScoreBreakdown(BaseModel):
    overall_score: float
    required_coverage: float
    preferred_coverage: float
    semantic_alignment: float
    evidence_strength: float
    bullet_quality: float
    formatting: float
    title_alignment: float
    matched_requirements: List[RequirementMatch] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    missing_preferred: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    improvement_priorities: List[str] = Field(default_factory=list)


class DebugInfo(BaseModel):
    resume_skills: List[str] = Field(default_factory=list)
    jd_required_skills: List[str] = Field(default_factory=list)
    jd_preferred_skills: List[str] = Field(default_factory=list)
    jd_all_skills: List[str] = Field(default_factory=list)

class WeakBullet(BaseModel):
    id: str
    text: str
    section: str
    reasons: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    score_breakdown: ScoreBreakdown
    missing_keywords: List[str] = Field(default_factory=list)

    # Backward-compatible field for current frontend
    weak_bullets: List[str] = Field(default_factory=list)

    # Better structured field for future use
    weak_bullet_details: List[WeakBullet] = Field(default_factory=list)

    suggestions: List[Suggestion] = Field(default_factory=list)

    # Optional during development
    debug: Optional[DebugInfo] = None

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class PlanModeRequest(BaseModel):
    bullet_id: str
    bullet_text: str
    current_bullet: Optional[str] = None
    bullet_reasons: List[str] = Field(default_factory=list)
    job_description: str
    user_message: str
    conversation_history: List[ChatMessage] = Field(default_factory=list)

class PlanModeResponse(BaseModel):
    mode: Literal["question", "options"]
    reply: str
    question: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    current_bullet: str

class Requirement(BaseModel):
    text: str
    category: Literal[
        "skill",
        "tool",
        "responsibility",
        "domain",
        "education",
        "certification",
        "experience",
    ]
    importance: Literal["required", "preferred"]
    normalized_key: Optional[str] = None

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v):
        if not isinstance(v, str):
            return v

        v = v.strip().lower()

        aliases = {
            "exp": "experience",
            "years_experience": "experience",
            "years of experience": "experience",
            "qualification": "education",
            "qualifications": "education",
            "technology": "tool",
            "technologies": "tool",
            "framework": "tool",
            "frameworks": "tool",
            "soft_skill": "skill",
        }

        # normalize obvious alias first
        v = aliases.get(v, v)

        allowed = {
            "skill",
            "tool",
            "responsibility",
            "domain",
            "education",
            "certification",
            "experience",
        }

        if v in allowed:
            return v

        # Handle combined labels like "experience|skill" or "domain/responsibility"
        parts = re.split(r"[|/,;]+", v)
        parts = [aliases.get(p.strip(), p.strip()) for p in parts if p.strip()]
        parts = [p for p in parts if p in allowed]

        if not parts:
            return "skill"

        # Prefer the more concrete / ATS-useful label
        priority = [
            "experience",
            "education",
            "certification",
            "tool",
            "skill",
            "responsibility",
            "domain",
        ]

        for p in priority:
            if p in parts:
                return p

        return parts[0]


class JobDescriptionStructured(BaseModel):
    job_title: Optional[str] = None
    seniority: Optional[str] = None
    min_years_experience: Optional[int] = None
    requirements: List[Requirement] = Field(default_factory=list)


class ResumeBulletEvidence(BaseModel):
    bullet: str
    section: str
    matched_requirement: Optional[str] = None
    semantic_score: float = 0.0
    evidence_score: int = 0  # 0-5