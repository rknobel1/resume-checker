from typing import Dict, List, Tuple, Optional, Union
from models import (
    JobDescriptionStructured,
    RequirementMatch,
    ScoreBreakdown,
)
from evidence_scorer import best_match_for_requirement, classify_evidence_strength
from bullet_scorer import score_bullets
from embeddings import embed_texts, cosine_similarity
import re


def _clean_list(values) -> List[str]:
    """Return a flat list of non-empty strings from nested list/dict/string values."""
    cleaned: List[str] = []

    if values is None:
        return cleaned

    if isinstance(values, str):
        value = values.strip()
        return [value] if value else []

    if isinstance(values, dict):
        for value in values.values():
            cleaned.extend(_clean_list(value))
        return cleaned

    if isinstance(values, list):
        for value in values:
            cleaned.extend(_clean_list(value))
        return cleaned

    value = str(values).strip()
    return [value] if value else []


def _join_non_empty(parts: List[Optional[str]], sep: str = " | ") -> str:
    return sep.join([str(p).strip() for p in parts if p and str(p).strip()])


def _resume_summary_section_present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_resume_summary_section_present(v) for v in value)
    if isinstance(value, dict):
        return any(_resume_summary_section_present(v) for v in value.values())
    return bool(value)


def normalize_resume_data(resume_data: Dict) -> Dict:
    """
    Convert the JSON returned by build_resume_summary_prompt into the older
    parser-shaped dict expected by the scoring functions.

    The scorer originally expected keys like experience_bullets, project_bullets,
    skills_text, education_text, etc. resume_summary returns title-cased keys like
    Experience, Projects, Skills, and Education. This adapter supports both shapes.
    """
    if not isinstance(resume_data, dict):
        return {}

    # Already in the old parser format.
    old_shape_keys = {
        "experience_bullets",
        "project_bullets",
        "skills_text",
        "education_text",
        "experience_groups",
        "project_groups",
    }
    if any(key in resume_data for key in old_shape_keys):
        return resume_data

    contact_entries = resume_data.get("Contact") or []
    contact = contact_entries[0] if isinstance(contact_entries, list) and contact_entries else {}
    if not isinstance(contact, dict):
        contact = {}

    experience_groups = []
    experience_bullets = []
    experience_text_lines = []
    for item in resume_data.get("Experience") or []:
        if not isinstance(item, dict):
            continue
        title = (item.get("Title") or "").strip()
        company = (item.get("Company") or "").strip()
        dates = (item.get("Dates") or "").strip()
        bullets = _clean_list(item.get("Bullet Points") or item.get("Details"))
        header = _join_non_empty([title, company, dates])

        experience_groups.append({
            "section": "experience",
            "header": header,
            "role": title,
            "organization": company,
            "dates": dates,
            "bullets": bullets,
        })
        experience_bullets.extend(bullets)
        if header:
            experience_text_lines.append(header)
        experience_text_lines.extend(bullets)

    project_groups = []
    project_bullets = []
    projects_text_lines = []
    for item in resume_data.get("Projects") or []:
        if not isinstance(item, dict):
            continue
        title = (item.get("Title") or "").strip()
        tech_stack = _clean_list(item.get("Technologies"))
        details = _clean_list(item.get("Details"))
        tech_text = ", ".join(tech_stack)
        header = _join_non_empty([title, tech_text])

        project_groups.append({
            "section": "projects",
            "header": header,
            "title": title,
            "metadata": tech_text,
            "tech_stack": tech_text,
            "bullets": details,
        })
        project_bullets.extend(details)
        if header:
            projects_text_lines.append(header)
        projects_text_lines.extend(details)

    skills = []
    skills_text_lines = []
    for item in resume_data.get("Skills") or []:
        if isinstance(item, dict):
            category = (item.get("Category") or "").strip()
            skill_items = _clean_list(item.get("Skills"))
            skills.extend(skill_items)
            if category and skill_items:
                skills_text_lines.append(f"{category}: {', '.join(skill_items)}")
            elif skill_items:
                skills_text_lines.append(", ".join(skill_items))
        else:
            skill_items = _clean_list(item)
            skills.extend(skill_items)
            skills_text_lines.extend(skill_items)

    education_text_lines = []
    for item in resume_data.get("Education") or []:
        if not isinstance(item, dict):
            continue
        line = _join_non_empty([
            item.get("Degree"),
            item.get("University"),
            item.get("Minor") and f"Minor: {item.get('Minor')}",
            item.get("GPA") and f"GPA: {item.get('GPA')}",
            item.get("Dates"),
        ])
        if line:
            education_text_lines.append(line)

    relevant_courses = _clean_list(resume_data.get("Relevant Courses"))

    awards_text_lines = []
    for item in resume_data.get("Awards") or []:
        if isinstance(item, dict):
            awards_text_lines.append(_join_non_empty([item.get("Award"), "; ".join(_clean_list(item.get("Details")))], sep=": "))
        else:
            awards_text_lines.extend(_clean_list(item))
    awards_text_lines = [line for line in awards_text_lines if line]

    certifications_text_lines = []
    for item in resume_data.get("Certifications") or []:
        if isinstance(item, dict):
            certifications_text_lines.append(_join_non_empty([item.get("Certification"), "; ".join(_clean_list(item.get("Details")))], sep=": "))
        else:
            certifications_text_lines.extend(_clean_list(item))
    certifications_text_lines = [line for line in certifications_text_lines if line]

    present_sections = [
        section_name
        for section_name in [
            "Contact", "Summary", "Education", "Experience", "Projects", "Skills",
            "Relevant Courses", "Awards", "Certifications",
        ]
        if _resume_summary_section_present(resume_data.get(section_name))
    ]
    section_completeness = round((len(present_sections) / 9.0) * 100.0, 2)

    current_or_recent_title = ""
    if experience_groups:
        current_or_recent_title = experience_groups[0].get("role") or ""

    email = (contact.get("Email") or "").strip()

    return {
        "summary": resume_data.get("Summary", "") or "",
        "email": email,
        "phone": contact.get("Phone", "") or "",
        "website": contact.get("Website/Portfolio", "") or "",
        "social": _clean_list(contact.get("Social/Other")),
        "skills": skills,
        "skills_text": "\n".join(skills_text_lines),
        "experience_bullets": experience_bullets,
        "project_bullets": project_bullets,
        "experience_groups": experience_groups,
        "project_groups": project_groups,
        "experience_text": "\n".join(experience_text_lines),
        "projects_text": "\n".join(projects_text_lines),
        "education_text": "\n".join(education_text_lines),
        "relevant_courses_text": "\n".join(relevant_courses),
        "awards_text": "\n".join(awards_text_lines),
        "certifications_text": "\n".join(certifications_text_lines),
        "current_or_recent_title": current_or_recent_title,
        "sections": {name: True for name in present_sections},
        "section_completeness": section_completeness,
        "has_tables": False,
        "has_images": False,
    }


def jd_summary_to_structured(jd_data: Dict) -> JobDescriptionStructured:
    """
    Convert the initial JD JSON summary into the structured shape used by the scorer.

    Expected input shape:
    {
        "required_lines": [...],
        "preferred_lines": [...],
        "other_lines": [...],
        "required_skills": [...],
        "preferred_skills": [...],
        "all_skills": [...],
    }
    """
    if not isinstance(jd_data, dict):
        jd_data = {}

    def clean_items(values) -> List[str]:
        return [
            item.strip()
            for item in _clean_list(values)
            if item and item.strip()
        ]

    requirements = []
    seen = set()

    def add_requirement(text: str, importance: str, category: str = "skill") -> None:
        text = (text or "").strip()
        if not text:
            return

        key = (importance, normalize_skill_text(text))
        if key in seen:
            return

        seen.add(key)
        requirements.append({
            "text": text,
            "category": category,
            "importance": importance,
            "normalized_key": normalize_skill_text(text),
        })

    for skill in clean_items(jd_data.get("required_skills")):
        add_requirement(skill, "required", "skill")

    for line in clean_items(jd_data.get("required_lines")):
        add_requirement(line, "required", "responsibility")

    for skill in clean_items(jd_data.get("preferred_skills")):
        add_requirement(skill, "preferred", "skill")

    for line in clean_items(jd_data.get("preferred_lines")):
        add_requirement(line, "preferred", "responsibility")

    # If the parser only populated all_skills, treat them as required so scoring still works.
    if not requirements:
        for skill in clean_items(jd_data.get("all_skills")):
            add_requirement(skill, "required", "skill")

    return JobDescriptionStructured(
        job_title=jd_data.get("job_title"),
        seniority=jd_data.get("seniority"),
        min_years_experience=jd_data.get("min_years_experience"),
        requirements=requirements,
    )

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

    for key in [
        "summary",
        "skills_text",
        "experience_text",
        "projects_text",
        "education_text",
        "relevant_courses_text",
        "awards_text",
        "certifications_text",
    ]:
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
        for text in [
            resume_data.get("education_text"),
            resume_data.get("relevant_courses_text"),
            resume_data.get("certifications_text"),
        ]
        for line in (text or "").split("\n")
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
    for key in [
        "summary",
        "skills_text",
        "experience_text",
        "projects_text",
        "education_text",
        "relevant_courses_text",
        "awards_text",
        "certifications_text",
    ]:
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


def score_resume_against_jd(resume_data: Dict, jd_data: Union[Dict, str]) -> ScoreBreakdown:
    resume_data = normalize_resume_data(resume_data)

    # Prefer the already-extracted JD JSON summary. Keep string support as a
    # defensive fallback, but do not make a second LLM structuring call.
    if isinstance(jd_data, dict):
        jd = jd_summary_to_structured(jd_data)
        job_description_text = jd_data.get("job_description") or "\n".join(
            _clean_list([
                jd_data.get("required_lines"),
                jd_data.get("preferred_lines"),
                jd_data.get("other_lines"),
                jd_data.get("required_skills"),
                jd_data.get("preferred_skills"),
            ])
        )
    else:
        job_description_text = jd_data or ""
        jd = jd_summary_to_structured({
            "required_lines": [job_description_text],
            "job_description": job_description_text,
        })
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
                        evidence = classify_evidence_strength(best_text, req.text, semantic_score)

            else:
                # For normal requirements, search across the whole resume
                best_text, semantic_score = best_match_for_requirement(req.text, full_candidates)
                if best_text is not None and semantic_score >= 0.55:
                    matched = True
                    best_evidence = best_text
                    evidence = classify_evidence_strength(best_text, req.text, semantic_score)

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
    semantic_alignment = semantic_alignment_score(resume_data, job_description_text)
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