import re
from typing import Dict, List, Tuple, Set, Optional


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

BULLET_START_RE = re.compile(r"^([-*•])\s+(.*)$")

DATE_HINT_RE = re.compile(
    r"\b("
    r"\d{4}\s*[-–]\s*(?:\d{4}|present|current)|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{4}\s*[-–]\s*(?:present|current|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{4})|"
    r"present|current"
    r")\b",
    re.IGNORECASE,
)

TECH_STACK_TOKEN_HINTS = {
    "python", "pytorch", "tensorflow", "keras", "numpy", "pandas",
    "react", "nextjs", "next.js", "typescript", "javascript",
    "node", "node.js", "express", "fastapi", "sql", "postgres",
    "mongodb", "docker", "kubernetes", "aws", "webgl", "pixijs",
    "pixi.js", "wasm", "cuda", "tkinter", "onnx", "onnxruntime",
    "framer", "prettymidi", "qml", "c", "c++", "cpp", "java"
}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"(?<=[A-Za-z])\n(?=[a-z])", "", text)
    text = text.replace("▪", "•").replace("◦", "•").replace("‣", "•")
    text = re.sub(r"[ \t]+", " ", text)
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


def _is_bullet_line(line: str) -> bool:
    return bool(BULLET_START_RE.match(line.strip()))


def _looks_like_tech_stack_line(line: str) -> bool:
    line = line.strip()
    if not line or _is_bullet_line(line):
        return False

    if "," not in line:
        return False

    parts = [p.strip().lower() for p in line.split(",") if p.strip()]
    if len(parts) < 2:
        return False

    tech_hits = 0
    for part in parts:
        tokens = [t for t in re.split(r"[/\s]+", part) if t]
        if part in TECH_STACK_TOKEN_HINTS or any(tok in TECH_STACK_TOKEN_HINTS for tok in tokens):
            tech_hits += 1

    return tech_hits >= max(2, len(parts) // 2)


def _looks_like_metadata_line(line: str) -> bool:
    low = line.lower().strip()
    if not low:
        return False

    metadata_words = [
        "hackathon",
        "place",
        "award",
        "solo",
        "team",
        "web application",
        "mobile application",
        "desktop application",
        "research project",
        "genai project",
        "ai project",
        "internship project",
        "capstone",
    ]

    if any(word in low for word in metadata_words):
        return True

    if DATE_HINT_RE.search(line):
        return True

    # catches things like: "Hackathon 2022 - 2nd place"
    if re.search(r"\b\d{4}\b", line) and any(word in low for word in ["hackathon", "place", "award"]):
        return True

    return False


def _split_inline_title_and_metadata(line: str) -> Tuple[str, Optional[str]]:
    line = line.strip()
    if not line:
        return "", None

    # Split things like:
    # "My Portfolio Web Application"
    # "Learning Music through Machine Learning Solo GenAI Project"
    # "Anime Recommendation System Hackathon 2022 - 2nd place"
    # "Fractal Simulator Solo Research Project"
    patterns = [
        r"^(.*?)(Hackathon.*)$",
        r"^(.*?)(Solo\s+GenAI\s+Project.*)$",
        r"^(.*?)(Solo\s+Research\s+Project.*)$",
        r"^(.*?)(Research\s+Project.*)$",
        r"^(.*?)(Web\s+Application.*)$",
        r"^(.*?)(Mobile\s+Application.*)$",
        r"^(.*?)(Desktop\s+Application.*)$",
        r"^(.*?)(Capstone.*)$",
    ]

    for pattern in patterns:
        m = re.match(pattern, line, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            metadata = m.group(2).strip()
            if title:
                return title, metadata

    return line, None


def _looks_like_project_title(line: str) -> bool:
    line = line.strip()
    if not line:
        return False

    if _is_bullet_line(line):
        return False

    if _looks_like_tech_stack_line(line):
        return False

    # allow lines that contain inline metadata like
    # "Anime Recommendation System Hackathon 2022 - 2nd place"
    title_part, _ = _split_inline_title_and_metadata(line)
    check_line = title_part.strip() if title_part.strip() else line

    if _looks_like_metadata_line(check_line):
        return False

    words = check_line.split()
    if not words:
        return False

    # titles should be relatively short
    if len(words) > 12:
        return False

    stopwords = {
        "and", "or", "of", "in", "for", "to", "with", "through", "on", "at", "by", "the", "a", "an"
    }

    alpha_words = [w for w in words if re.search(r"[A-Za-z]", w)]
    if not alpha_words:
        return False

    strong_words = []
    for w in alpha_words:
        cleaned = re.sub(r"[^A-Za-z0-9+#.-]", "", w)
        if not cleaned:
            continue
        low = cleaned.lower()
        if low in stopwords:
            continue
        strong_words.append(cleaned)

    if not strong_words:
        return False

    capitalized_or_special = 0
    for w in strong_words:
        if w[:1].isupper() or any(ch.isdigit() for ch in w) or "+" in w or "#" in w:
            capitalized_or_special += 1

    return capitalized_or_special >= max(1, len(strong_words) - 1)


def extract_project_groups(section_text: str) -> List[Dict]:
    if not section_text.strip():
        return []

    lines = split_lines(section_text)
    groups: List[Dict] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # skip stray bullets before a title
        if _is_bullet_line(line):
            i += 1
            continue

        # require an actual project-title-like line to start a group
        if not _looks_like_project_title(line):
            i += 1
            continue

        title_line = line
        metadata = None
        tech_stack = None
        bullets: List[str] = []

        title_line, inline_metadata = _split_inline_title_and_metadata(title_line)
        if inline_metadata:
            metadata = inline_metadata

        i += 1

        # collect optional metadata / tech stack lines until bullets begin
        while i < len(lines):
            candidate = lines[i].strip()

            if not candidate:
                i += 1
                continue

            if _is_bullet_line(candidate):
                break

            # if we hit another title before bullets, treat previous project as empty-header project
            if _looks_like_project_title(candidate):
                break

            if _looks_like_tech_stack_line(candidate):
                if tech_stack:
                    tech_stack = f"{tech_stack}, {candidate}"
                else:
                    tech_stack = candidate
            elif _looks_like_metadata_line(candidate):
                if metadata:
                    metadata = f"{metadata} {candidate}"
                else:
                    metadata = candidate
            else:
                # fallback: if it is a short line, treat as metadata; otherwise attach to metadata too
                if metadata:
                    metadata = f"{metadata} {candidate}"
                else:
                    metadata = candidate

            i += 1

        # collect bullets for this project
        while i < len(lines):
            current_line = lines[i].strip()

            if not current_line:
                i += 1
                continue

            if not _is_bullet_line(current_line):
                break

            bullet_match = BULLET_START_RE.match(current_line)
            current_parts = [bullet_match.group(2).strip()]
            i += 1

            while i < len(lines):
                next_line = lines[i].strip()

                if not next_line:
                    i += 1
                    continue

                if _is_bullet_line(next_line):
                    break

                # critical fix:
                # if the next line looks like a new project title,
                # stop the current bullet and let outer loop start a new project
                if _looks_like_project_title(next_line):
                    break

                # allow wrapped bullet lines to continue normally
                current_parts.append(next_line)
                i += 1

            bullets.append(" ".join(current_parts).strip())

            # after a bullet, if next line is a new title-ish non-bullet line, stop this project
            if i < len(lines):
                next_line = lines[i].strip()
                if next_line and not _is_bullet_line(next_line) and _looks_like_project_title(next_line):
                    break

        groups.append({
            "section": "projects",
            "title": title_line,
            "metadata": metadata,
            "tech_stack": tech_stack,
            "bullets": bullets,
        })

    return [g for g in groups if g["title"] or g["bullets"]]


def extract_bullets(section_text: str) -> List[str]:
    if not section_text.strip():
        return []

    lines = split_lines(section_text)
    bullets: List[str] = []
    current: List[str] = []

    for line in lines:
        m = BULLET_START_RE.match(line)
        if m:
            if current:
                bullets.append(" ".join(current).strip())
            current = [m.group(2).strip()]
        else:
            if current:
                current.append(line.strip())

    if current:
        bullets.append(" ".join(current).strip())

    return bullets


def extract_experience_groups(section_text: str) -> List[Dict]:
    if not section_text.strip():
        return []

    lines = split_lines(section_text)
    groups: List[Dict] = []
    i = 0

    while i < len(lines):
        if _is_bullet_line(lines[i]):
            i += 1
            continue

        header_lines: List[str] = []

        while i < len(lines) and not _is_bullet_line(lines[i]):
            header_lines.append(lines[i].strip())
            i += 1

            if len(header_lines) >= 3:
                break

        organization = None
        role = ""
        dates = None

        if len(header_lines) >= 3:
            organization = header_lines[0]
            role = header_lines[1]
            dates = header_lines[2]
        elif len(header_lines) == 2:
            organization = header_lines[0]
            role = header_lines[1]
        elif len(header_lines) == 1:
            role = header_lines[0]

        bullets: List[str] = []

        while i < len(lines):
            bullet_match = BULLET_START_RE.match(lines[i])
            if not bullet_match:
                break

            current_parts = [bullet_match.group(2).strip()]
            i += 1

            while i < len(lines) and not _is_bullet_line(lines[i]):
                next_line = lines[i].strip()

                # if this looks like the start of the next experience entry, stop
                if len(next_line.split()) <= 8 and not next_line.endswith(".") and not _looks_like_tech_stack_line(next_line):
                    capitalized = sum(1 for w in next_line.split() if w[:1].isupper())
                    if capitalized >= max(1, len(next_line.split()) - 1):
                        break

                current_parts.append(next_line)
                i += 1

            bullets.append(" ".join(current_parts).strip())

            if i < len(lines) and not _is_bullet_line(lines[i]):
                break

        if role or bullets:
            groups.append({
                "section": "experience",
                "organization": organization,
                "role": role or "Experience Entry",
                "dates": dates,
                "bullets": bullets,
            })

    return groups


def normalize_for_matching(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s+.#/-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_canonical_skills(text: str) -> List[str]:
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

    summary_text = sections.get("Summary", "")
    skills_text = sections.get("Skills", "")
    experience_text = sections.get("Experience", "")
    projects_text = sections.get("Projects", "")
    education_text = sections.get("Education", "")
    certifications_text = sections.get("Certifications", "")

    experience_groups = extract_experience_groups(experience_text)
    project_groups = extract_project_groups(projects_text)

    experience_bullets = [b for g in experience_groups for b in g["bullets"]]
    project_bullets = [b for g in project_groups for b in g["bullets"]]

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

        "summary": summary_text,
        "skills_text": skills_text,
        "experience_text": experience_text,
        "projects_text": projects_text,
        "education_text": education_text,
        "certifications_text": certifications_text,
        "section_completeness": 80.0,
        "email": "",
        "has_tables": False,
        "has_images": False,
        "current_or_recent_title": "",

        "experience_groups": experience_groups,
        "project_groups": project_groups,

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