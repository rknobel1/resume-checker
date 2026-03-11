from typing import Dict, List, Tuple, Optional
from models import (
    JobDescriptionStructured,
    RequirementMatch,
    ScoreBreakdown,
)
from jd_structurer import structure_job_description
from evidence_scorer import best_match_for_requirement, classify_evidence_strength
from bullet_scorer import score_bullets
from embeddings import embed_texts, cosine_similarity
import re

def is_work_authorization_requirement(req_text: str) -> bool:
    t = req_text.lower()

    patterns = [
        "green card",
        "u.s. citizenship",
        "us citizenship",
        "citizenship",
        "work authorization",
        "authorized to work",
        "employment authorization",
        "visa sponsorship",
        "sponsorship",
        "eligible to work",
        "permanent resident",
        "right to work",
    ]

    return any(p in t for p in patterns)

def extract_resume_lines(resume_data: Dict) -> List[str]:
    """
    Extract searchable lines from the whole resume
    (skills, projects, experience, education).
    """

    lines = []

    # existing bullets
    lines.extend(extract_resume_bullets(resume_data))

    for key in ["skills_text", "experience_text", "projects_text", "education_text"]:
        text = resume_data.get(key)
        if not text:
            continue

        for line in str(text).split("\n"):
            line = line.strip()
            if line:
                lines.append(line)

    return lines

def normalize_skill_text(text: str) -> str:
    t = text.lower()

    # normalize unicode plus
    t = t.replace("＋", "+")

    # normalize spaced variants first
    t = re.sub(r"\bc\s*\+\s*\+\b", "cpp", t)
    t = re.sub(r"\bc\s*#\b", "csharp", t)

    t = t.replace("c++", "cpp")
    t = t.replace("c#", "csharp")
    t = t.replace("node.js", "nodejs")
    t = t.replace("next.js", "nextjs")
    t = t.replace("scikit-learn", "sklearn")
    t = t.replace("git/github", "git github")
    t = t.replace("jupyter lab", "jupyterlab")

    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def requirement_aliases(requirement_text: str) -> List[str]:
    req = normalize_skill_text(requirement_text)

    alias_map = {
        "numpy": ["numpy"],
        "matplotlib": ["matplotlib"],
        "docker": ["docker"],
        "aws": ["aws", "amazon web services"],
        "jupyter lab": ["jupyterlab", "jupyter lab", "jupyter notebook", "notebook"],
        "git github": ["git", "github", "gitlab"],
        "cpp": ["cpp", "c++"],
        "python": ["python"],
        "pytorch": ["pytorch", "torch"],
        "tensorflow": ["tensorflow", "tf"],
        "scikit learn": ["scikit learn", "sklearn"],
    }

    for canonical, aliases in alias_map.items():
        if canonical in req:
            return aliases

    return [req]


def is_skill_like_requirement(req_text: str, category: str) -> bool:
    if (category or "").lower() in {"skills", "tools", "technologies", "technical"}:
        return True

    text = normalize_skill_text(req_text)

    known_skills = [
        "numpy", "matplotlib", "docker", "aws", "git", "github",
        "jupyterlab", "python", "cpp", "pytorch", "tensorflow",
        "sql", "javascript", "typescript", "sklearn", "nodejs", "nextjs",
    ]

    tokens = set(text.split())

    # Exact token presence is enough to treat it as a skill requirement
    if any(skill in tokens for skill in known_skills):
        return True

    # Also allow very short requirements to count as skill-like
    return len(tokens) <= 4


def exact_skill_match(requirement_text: str, candidates: List[str]) -> Tuple[bool, Optional[str], float, int]:
    aliases = requirement_aliases(requirement_text)
    normalized_aliases = {normalize_skill_text(alias) for alias in aliases}

    for line in candidates:
        norm_line = normalize_skill_text(line)
        line_tokens = set(norm_line.split())

        for alias_norm in normalized_aliases:
            alias_tokens = alias_norm.split()

            # single-token skills like cpp, python, docker
            if len(alias_tokens) == 1 and alias_tokens[0] in line_tokens:
                return True, line, 1.0, 5

            # multi-token alias fallback
            if alias_norm in norm_line:
                return True, line, 1.0, 5

    return False, None, 0.0, 0

def extract_resume_evidence(resume_data: Dict) -> Dict[str, List[str]]:
    bullets = []
    for key in ["experience_bullets", "project_bullets"]:
        value = resume_data.get(key, [])
        if isinstance(value, list):
            bullets.extend([v.strip() for v in value if v and v.strip()])

    education_lines = [
        line.strip()
        for line in (resume_data.get("education_text") or "").split("\n")
        if line.strip()
    ]

    raw_skills_text = resume_data.get("skills_text") or ""
    skills_lines = []

    for line in raw_skills_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        skills_lines.append(line)  # keep original full line too

        parts = re.split(r"[,|•;/·]", line)
        split_parts = [p.strip() for p in parts if p.strip()]
        skills_lines.extend(split_parts)

    return {
        "bullets": bullets,
        "education": education_lines,
        "skills": skills_lines,
        "all": bullets + education_lines + skills_lines,
    }


def normalize_degree_text(text: str) -> str:
    t = text.lower()
    t = t.replace("’", "'")

    # Degree variants
    t = t.replace("master's", "masters")
    t = t.replace("bachelor's", "bachelors")
    t = t.replace("doctorate", "phd")
    t = t.replace("ph.d.", "phd")
    t = t.replace("ph.d", "phd")

    t = re.sub(r"\bm\.?\s*s\.?\b", "masters", t)
    t = re.sub(r"\bb\.?\s*s\.?\b", "bachelors", t)
    t = re.sub(r"\bb\.?\s*a\.?\b", "bachelors", t)
    t = re.sub(r"\bmeng\b", "masters", t)
    t = re.sub(r"\bmsc\b", "masters", t)
    t = re.sub(r"\bmcs\b", "masters computer science", t)

    # Field aliases
    t = re.sub(r"\bcs\b", "computer science", t)
    t = re.sub(r"\bee\b", "electrical engineering", t)
    t = re.sub(r"\bstats\b", "statistics", t)
    t = re.sub(r"\bmath\b", "mathematics", t)
    t = re.sub(r"\bml\b", "machine learning", t)

    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def detect_degree_level(text: str) -> Optional[str]:
    t = normalize_degree_text(text)

    if "phd" in t:
        return "phd"
    if "masters" in t or "masters degree" in t:
        return "masters"
    if "bachelors" in t or "bachelors degree" in t:
        return "bachelors"
    return None


def degree_level_satisfies(required_level: str, candidate_level: str) -> bool:
    rank = {
        "bachelors": 1,
        "masters": 2,
        "phd": 3,
    }
    return rank.get(candidate_level, 0) >= rank.get(required_level, 0)


def extract_required_fields(requirement_text: str) -> List[str]:
    req = normalize_degree_text(requirement_text)

    fields = [
        "computer science",
        "electrical engineering",
        "mathematics",
        "statistics",
        "physics",
        "data science",
        "machine learning",
        "music technology",
        "artificial intelligence",
    ]

    matched = [field for field in fields if field in req]
    return matched


def is_related_research_field(text: str) -> bool:
    t = normalize_degree_text(text)
    related_terms = [
        "computer science",
        "engineering",
        "science",
        "mathematics",
        "statistics",
        "physics",
        "data science",
        "machine learning",
        "artificial intelligence",
    ]
    return any(term in t for term in related_terms)


def classify_education_evidence(education_line: str, requirement_text: str) -> int:
    line = normalize_degree_text(education_line)
    req = normalize_degree_text(requirement_text)

    req_level = detect_degree_level(req)
    line_level = detect_degree_level(line)

    if req_level is None or line_level is None:
        return 0

    if not degree_level_satisfies(req_level, line_level):
        return 0

    required_fields = extract_required_fields(req)

    if required_fields and any(field in line for field in required_fields):
        return 5

    if "field related to research" in req and is_related_research_field(line):
        return 4

    if is_related_research_field(line):
        return 3

    return 1


def direct_degree_match(requirement_text: str, education_lines: List[str]) -> Tuple[bool, Optional[str], float, int]:
    req = normalize_degree_text(requirement_text)
    req_level = detect_degree_level(req)

    if req_level is None:
        return False, None, 0.0, 0

    required_fields = extract_required_fields(req)

    best_line = None
    best_semantic = 0.0
    best_evidence = 0

    for line in education_lines:
        norm_line = normalize_degree_text(line)
        line_level = detect_degree_level(norm_line)

        if line_level is None:
            continue

        # Strict degree gate
        if not degree_level_satisfies(req_level, line_level):
            continue

        evidence = classify_education_evidence(line, requirement_text)
        if evidence == 0:
            continue

        if required_fields and any(field in norm_line for field in required_fields):
            semantic = 1.0
        elif "field related to research" in req and is_related_research_field(norm_line):
            semantic = 0.9
        elif is_related_research_field(norm_line):
            semantic = 0.75
        else:
            semantic = 0.0

        if semantic > best_semantic or (semantic == best_semantic and evidence > best_evidence):
            best_line = line
            best_semantic = semantic
            best_evidence = evidence

    if best_line is None:
        return False, None, 0.0, 0

    return True, best_line, best_semantic, best_evidence


def is_education_requirement(req_text: str, req_category: str) -> bool:
    if (req_category or "").lower() == "education":
        return True

    text = normalize_degree_text(req_text)
    education_markers = [
        "degree",
        "bachelors",
        "masters",
        "phd",
        "education",
    ]
    return any(marker in text for marker in education_markers)


def flatten_resume_for_semantics(resume_data: Dict) -> str:
    sections = []
    for key in ["summary", "skills_text", "experience_text", "projects_text", "education_text"]:
        value = resume_data.get(key)
        if value:
            sections.append(str(value))
    return "\n".join(sections)


def extract_resume_bullets(resume_data: Dict) -> List[str]:
    bullets = []
    for key in ["experience_bullets", "project_bullets"]:
        value = resume_data.get(key, [])
        if isinstance(value, list):
            bullets.extend([v.strip() for v in value if v and v.strip()])
    return bullets


def title_alignment_score(resume_data: Dict, jd: JobDescriptionStructured) -> float:
    jd_title = (jd.job_title or "").lower()
    resume_title = (resume_data.get("current_or_recent_title") or "").lower()

    if not jd_title or not resume_title:
        return 50.0
    if jd_title == resume_title:
        return 100.0
    if any(tok in resume_title for tok in jd_title.split()) or any(tok in jd_title for tok in resume_title.split()):
        return 75.0
    return 35.0


def formatting_score(resume_data: Dict) -> float:
    penalties = 0
    if resume_data.get("has_tables"):
        penalties += 20
    if resume_data.get("has_images"):
        penalties += 10
    if not resume_data.get("email"):
        penalties += 5
    return max(0.0, 100.0 - penalties)


def semantic_alignment_score(resume_data: Dict, job_description: str) -> float:
    resume_text = flatten_resume_for_semantics(resume_data)
    if not resume_text.strip() or not job_description.strip():
        return 0.0

    vecs = embed_texts([resume_text, job_description])
    sim = cosine_similarity(vecs[0], vecs[1])
    return round(max(0.0, min(100.0, sim * 100.0)), 2)


def score_resume_against_jd(resume_data: Dict, job_description: str) -> ScoreBreakdown:
    jd = structure_job_description(job_description)
    bullets = extract_resume_bullets(resume_data)
    resume_lines = extract_resume_lines(resume_data)
    evidence_map = extract_resume_evidence(resume_data)

    matched_requirements = []
    missing_required = []
    missing_preferred = []

    required_scores = []
    preferred_scores = []
    evidence_scores = []

    for req in jd.requirements:
        matched = False
        best_evidence = None
        semantic_score = 0.0
        evidence = 0

        # Exclude legal/work authorization requirements from ATS scoring
        if is_work_authorization_requirement(req.text):
            matched_requirements.append(
                RequirementMatch(
                    requirement=req.text,
                    category="work_authorization",
                    importance=req.importance,
                    matched=False,
                    score=0.0,
                    evidence_score=0,
                    best_evidence=None,
                    notes="Excluded from ATS scoring as legal/work-authorization requirement",
                )
            )
            continue

        if is_education_requirement(req.text, req.category):
            matched, best_evidence, semantic_score, evidence = direct_degree_match(
                req.text, evidence_map["education"]
            )

        else:
            # Search the full resume, not just bullets
            full_candidates = resume_lines

            if is_skill_like_requirement(req.text, req.category):
                # For skill/tool requirements, prefer exact matching first
                skill_candidates = evidence_map["skills"] + evidence_map["bullets"] + resume_lines

                matched, best_evidence, semantic_score, evidence = exact_skill_match(
                    req.text, skill_candidates
                )

                if not matched:
                    best_text, semantic_score = best_match_for_requirement(req.text, skill_candidates)
                    if best_text is not None and semantic_score >= 0.55:
                        matched = True
                        best_evidence = best_text
                        evidence = classify_evidence_strength(best_text, req.text)

            else:
                # For normal requirements, search across the whole resume
                best_text, semantic_score = best_match_for_requirement(req.text, full_candidates)
                if best_text is not None and semantic_score >= 0.55:
                    matched = True
                    best_evidence = best_text
                    evidence = classify_evidence_strength(best_text, req.text)

        req_score = (semantic_score * 100.0 * 0.6) + ((evidence / 5.0) * 100.0 * 0.4)
        req_score = round(req_score, 2) if matched else 0.0

        matched_requirements.append(
            RequirementMatch(
                requirement=req.text,
                category=req.category,
                importance=req.importance,
                matched=matched,
                score=req_score,
                evidence_score=evidence,
                best_evidence=best_evidence,
                notes=None if matched else "No strong evidence found in resume",
            )
        )

        if req.importance == "required":
            required_scores.append(req_score)
            if not matched:
                missing_required.append(req.text)
        else:
            preferred_scores.append(req_score)
            if not matched:
                missing_preferred.append(req.text)

        evidence_scores.append((evidence / 5.0) * 100.0)

    required_coverage = round(sum(required_scores) / max(len(required_scores), 1), 2)
    preferred_coverage = round(sum(preferred_scores) / max(len(preferred_scores), 1), 2)
    semantic_alignment = semantic_alignment_score(resume_data, job_description)
    evidence_strength = round(sum(evidence_scores) / max(len(evidence_scores), 1), 2)
    bullet_quality = score_bullets(bullets)
    formatting = formatting_score(resume_data)
    title_alignment = title_alignment_score(resume_data, jd)

    overall_score = round(
        required_coverage * 0.30 +
        preferred_coverage * 0.10 +
        semantic_alignment * 0.20 +
        evidence_strength * 0.15 +
        bullet_quality * 0.10 +
        formatting * 0.05 +
        title_alignment * 0.05 +
        min(100.0, resume_data.get("section_completeness", 80.0)) * 0.05,
        2
    )

    strengths = [
        m.requirement for m in matched_requirements
        if m.matched and m.evidence_score >= 4
    ][:5]

    improvement_priorities = missing_required[:5] + missing_preferred[:3]

    return ScoreBreakdown(
        overall_score=overall_score,
        required_coverage=required_coverage,
        preferred_coverage=preferred_coverage,
        semantic_alignment=semantic_alignment,
        evidence_strength=evidence_strength,
        bullet_quality=bullet_quality,
        formatting=formatting,
        title_alignment=title_alignment,
        matched_requirements=matched_requirements,
        missing_required=missing_required,
        missing_preferred=missing_preferred,
        strengths=strengths,
        improvement_priorities=improvement_priorities,
    )