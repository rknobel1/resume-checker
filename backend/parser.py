import re
from typing import Dict, List, Tuple, Set


SECTION_ALIASES = {
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "about",
        "objective",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "tech stack",
        "technologies",
        "tools",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "career history",
    ],
    "projects": [
        "projects",
        "personal projects",
        "academic projects",
        "selected projects",
    ],
    "education": [
        "education",
        "academic background",
        "academic history",
    ],
    "certifications": [
        "certifications",
        "licenses",
        "licenses & certifications",
    ],
}

# canonical skill -> aliases
SKILL_ALIASES = {
    "python": ["python"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "java": ["java"],
    "c++": ["c++"],
    "c#": ["c#"],
    ".net": [".net", "dotnet", "asp.net"],
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs"],
    "node.js": ["node.js", "nodejs", "node"],
    "express": ["express", "express.js"],
    "sql": ["sql"],
    "postgresql": ["postgresql", "postgres", "postgre"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "aws": ["aws", "amazon web services"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "git": ["git"],
    "github": ["github"],
    "rest api": ["rest api", "restful api", "rest APIs", "apis"],
    "graphql": ["graphql"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning"],
    "data analysis": ["data analysis", "data analytics"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch", "torch"],
}

REQUIRED_PATTERNS = [
    r"\brequired\b",
    r"\bmust have\b",
    r"\bminimum qualifications\b",
    r"\bqualifications\b",
    r"\brequirements\b",
]

PREFERRED_PATTERNS = [
    r"\bpreferred\b",
    r"\bnice to have\b",
    r"\bbonus\b",
    r"\bplus\b",
    r"\bpreferred qualifications\b",
]


def normalize_text(text: str) -> str:
    """
    Better normalization for pasted / PDF-extracted text.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove hyphenated line breaks: manage-\nment -> management
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Merge likely broken words across newlines: Py\nthon -> Python
    text = re.sub(r"(?<=[A-Za-z])\n(?=[a-z])", "", text)

    # Normalize bullet characters
    text = text.replace("▪", "•").replace("◦", "•").replace("‣", "•")

    # Collapse internal spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Keep line structure but remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_lines(text: str) -> List[str]:
    return [line.strip() for line in text.split("\n") if line.strip()]


def _canonical_section_header(line: str) -> str | None:
    cleaned = re.sub(r"[:\-\s]+$", "", line.strip().lower())

    for canonical, aliases in SECTION_ALIASES.items():
        if cleaned in aliases:
            return canonical

    return None


def detect_sections(text: str) -> Dict[str, str]:
    text = normalize_text(text)
    lines = text.split("\n")

    sections: Dict[str, List[str]] = {"other": []}
    current_section = "other"

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        maybe_header = _canonical_section_header(line)
        if maybe_header:
            current_section = maybe_header
            sections.setdefault(current_section, [])
            continue

        sections.setdefault(current_section, []).append(line)

    return {
        k: "\n".join(v).strip()
        for k, v in sections.items()
        if any(part.strip() for part in v)
    }


def extract_bullets(section_text: str) -> List[str]:
    """
    Handles multi-line bullets.
    """
    if not section_text.strip():
        return []

    lines = split_lines(section_text)
    bullets: List[str] = []
    current: List[str] = []

    bullet_start_pattern = re.compile(r"^([-*•])\s+(.*)$")

    for line in lines:
        m = bullet_start_pattern.match(line)
        if m:
            if current:
                bullets.append(" ".join(current).strip())
            current = [m.group(2).strip()]
        else:
            # continuation of previous bullet
            if current:
                current.append(line.strip())

    if current:
        bullets.append(" ".join(current).strip())

    return bullets


def normalize_for_matching(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s+.#/-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_canonical_skills(text: str) -> List[str]:
    """
    Phrase-first skill extraction using a skill alias dictionary.
    """
    normalized = normalize_for_matching(text)
    found: Set[str] = set()

    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            alias_norm = normalize_for_matching(alias)
            pattern = rf"(?<!\w){re.escape(alias_norm)}(?!\w)"
            if re.search(pattern, normalized):
                found.add(canonical)
                break

    return sorted(found)


def classify_jd_lines(lines: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Naive JD line classification:
    - required lines
    - preferred lines
    - other lines
    """
    required_lines = []
    preferred_lines = []
    other_lines = []

    current_mode = "other"

    for line in lines:
        low = line.lower()

        if any(re.search(p, low) for p in REQUIRED_PATTERNS):
            current_mode = "required"
            other_lines.append(line)
            continue

        if any(re.search(p, low) for p in PREFERRED_PATTERNS):
            current_mode = "preferred"
            other_lines.append(line)
            continue

        if current_mode == "required":
            required_lines.append(line)
        elif current_mode == "preferred":
            preferred_lines.append(line)
        else:
            other_lines.append(line)

    return required_lines, preferred_lines, other_lines


def parse_resume(resume_text: str) -> Dict:
    normalized = normalize_text(resume_text)
    sections = detect_sections(normalized)

    summary_text = sections.get("summary", "")
    skills_text = sections.get("skills", "")
    experience_text = sections.get("experience", "")
    projects_text = sections.get("projects", "")
    education_text = sections.get("education", "")
    certifications_text = sections.get("certifications", "")

    experience_bullets = extract_bullets(experience_text)
    project_bullets = extract_bullets(projects_text)

    all_text = "\n".join([
        summary_text,
        skills_text,
        experience_text,
        projects_text,
        education_text,
        certifications_text,
        sections.get("other", ""),
    ]).strip()

    extracted_skills = extract_canonical_skills(all_text)

    return {
        "normalized_text": normalized,
        "sections": sections,

        # new fields expected by scoring.py
        "summary": summary_text,
        "skills_text": skills_text,
        "experience_text": experience_text,
        "projects_text": projects_text,
        "education_text": education_text,
        "certifications_text": certifications_text,
        "section_completeness": 80.0,   # placeholder for now
        "email": "",                    # placeholder for now
        "has_tables": False,
        "has_images": False,
        "current_or_recent_title": "",

        # existing fields
        "experience_bullets": experience_bullets,
        "project_bullets": project_bullets,
        "all_bullets": experience_bullets + project_bullets,
        "skills": extracted_skills,
    }


def parse_job_description(job_description: str) -> Dict:
    jd = normalize_text(job_description)
    lines = split_lines(jd)

    required_lines, preferred_lines, other_lines = classify_jd_lines(lines)

    required_skills = extract_canonical_skills("\n".join(required_lines))
    preferred_skills = extract_canonical_skills("\n".join(preferred_lines))
    other_skills = extract_canonical_skills("\n".join(other_lines))

    all_skills = sorted(set(required_skills + preferred_skills + other_skills))

    return {
        "raw_text": jd,
        "lines": lines,
        "required_lines": required_lines,
        "preferred_lines": preferred_lines,
        "other_lines": other_lines,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "all_skills": all_skills,
    }