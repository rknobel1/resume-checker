import re
from typing import Dict, List, Set
from models import ScoreBreakdown


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "you", "your", "are", "was",
    "have", "has", "will", "from", "into", "onto", "our", "their", "they",
    "them", "who", "what", "when", "where", "how", "using", "use", "used",
    "a", "an", "to", "of", "in", "on", "as", "by", "or", "be", "is", "at"
}

SKILL_HINTS = {
    "python", "java", "javascript", "typescript", "sql", "aws", "azure", "gcp",
    "docker", "kubernetes", "react", "next.js", "node", "fastapi", "pytorch",
    "tensorflow", "machine learning", "data analysis", "excel", "tableau",
    "power bi", "git", "linux", "api", "nlp", "llm"
}

WEAK_PHRASES = {
    "worked on",
    "helped with",
    "responsible for",
    "assisted with",
    "participated in",
    "involved in",
}


def tokenize(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"[a-zA-Z0-9\.\+#\-]+", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def unique_tokens(text: str) -> Set[str]:
    return set(tokenize(text))


def extract_skill_keywords(text: str) -> Set[str]:
    text_low = text.lower()
    found = set()

    for skill in SKILL_HINTS:
        if skill in text_low:
            found.add(skill)

    return found


def keyword_overlap_score(resume_text: str, jd_text: str) -> float:
    r = unique_tokens(resume_text)
    j = unique_tokens(jd_text)
    if not j:
        return 0.0
    overlap = len(r & j) / len(j)
    return min(overlap * 100, 100.0)


def skills_match_score(resume_text: str, jd_text: str) -> float:
    resume_skills = extract_skill_keywords(resume_text)
    jd_skills = extract_skill_keywords(jd_text)
    if not jd_skills:
        return 70.0
    return (len(resume_skills & jd_skills) / len(jd_skills)) * 100.0


def experience_alignment_score(resume_sections: Dict, jd_text: str) -> float:
    exp_text = resume_sections.get("experience", "") + "\n" + resume_sections.get("projects", "")
    score = keyword_overlap_score(exp_text, jd_text)

    # Small bonus for having both sections
    if resume_sections.get("experience"):
        score += 5
    if resume_sections.get("projects"):
        score += 5

    return min(score, 100.0)


def achievement_strength_score(bullets: List[str]) -> float:
    if not bullets:
        return 20.0

    metric_count = 0
    strong_verb_count = 0

    strong_verbs = {
        "built", "developed", "designed", "implemented", "optimized",
        "improved", "created", "automated", "led", "deployed", "analyzed"
    }

    for bullet in bullets:
        low = bullet.lower()
        if re.search(r"\b\d+%|\b\d+\b", low):
            metric_count += 1
        if any(low.startswith(v) for v in strong_verbs):
            strong_verb_count += 1

    metric_ratio = metric_count / len(bullets)
    verb_ratio = strong_verb_count / len(bullets)

    score = (metric_ratio * 60) + (verb_ratio * 40)
    return min(score, 100.0)


def section_completeness_score(sections: Dict) -> float:
    desired = ["skills", "experience", "projects", "education"]
    present = sum(1 for s in desired if sections.get(s))
    return (present / len(desired)) * 100.0


def ats_formatting_score(resume_text: str) -> float:
    score = 90.0

    if "|" in resume_text:
        score -= 10
    if "\t" in resume_text:
        score -= 5
    if len(resume_text.splitlines()) < 8:
        score -= 20

    return max(min(score, 100.0), 0.0)


def find_missing_keywords(resume_text: str, jd_text: str, top_k: int = 15) -> List[str]:
    resume_tokens = unique_tokens(resume_text)
    jd_tokens = unique_tokens(jd_text)

    missing = [tok for tok in jd_tokens if tok not in resume_tokens and tok not in STOPWORDS]
    missing = sorted(missing, key=len, reverse=True)
    return missing[:top_k]


def find_weak_bullets(bullets: List[str]) -> List[str]:
    weak = []
    for bullet in bullets:
        low = bullet.lower()
        if any(phrase in low for phrase in WEAK_PHRASES):
            weak.append(bullet)
        elif len(bullet.split()) < 7:
            weak.append(bullet)
    return weak[:10]


def score_resume(resume_data: Dict, jd_data: Dict) -> Dict:
    sections = resume_data["sections"]
    bullets = resume_data["all_bullets"]

    resume_text = "\n".join(sections.values())
    jd_text = jd_data["raw_text"]

    keyword = keyword_overlap_score(resume_text, jd_text)
    skills = skills_match_score(resume_text, jd_text)
    experience = experience_alignment_score(sections, jd_text)
    achievement = achievement_strength_score(bullets)
    completeness = section_completeness_score(sections)
    ats = ats_formatting_score(resume_text)

    overall = (
        keyword * 0.25
        + skills * 0.20
        + experience * 0.20
        + achievement * 0.15
        + completeness * 0.10
        + ats * 0.10
    )

    return {
        "score_breakdown": ScoreBreakdown(
            keyword_relevance=round(keyword, 1),
            skills_match=round(skills, 1),
            experience_alignment=round(experience, 1),
            achievement_strength=round(achievement, 1),
            section_completeness=round(completeness, 1),
            ats_formatting=round(ats, 1),
            overall_score=round(overall, 1),
        ),
        "missing_keywords": find_missing_keywords(resume_text, jd_text),
        "weak_bullets": find_weak_bullets(bullets),
    }