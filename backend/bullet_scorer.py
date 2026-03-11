import re
from typing import Dict, List


WEAK_STARTS = {
    "helped", "worked on", "responsible for", "tasked with", "assisted"
}

STRONG_VERBS = {
    "built", "developed", "designed", "implemented", "optimized", "led",
    "launched", "deployed", "automated", "architected", "improved", "scaled"
}

TECH_HINTS = {
    "python", "sql", "aws", "docker", "kubernetes", "react", "fastapi",
    "node", "postgres", "airflow", "spark", "tensorflow", "pytorch"
}


def score_bullet(bullet: str) -> Dict[str, float]:
    text = bullet.strip().lower()
    words = text.split()

    starts_strong = 1.0 if any(text.startswith(v) for v in STRONG_VERBS) else 0.0
    starts_weak = 1.0 if any(text.startswith(v) for v in WEAK_STARTS) else 0.0
    has_metric = 1.0 if re.search(r"\d|%|\$", bullet) else 0.0
    has_tool = 1.0 if any(t in text for t in TECH_HINTS) else 0.0
    specificity = min(len(words) / 22.0, 1.0)
    ownership = 1.0 if any(w in text for w in ["led", "owned", "designed", "architected"]) else 0.0
    impact = 1.0 if any(w in text for w in ["reduced", "increased", "improved", "saved", "grew", "cut"]) else 0.0

    score = (
        starts_strong * 0.20 +
        (1.0 - starts_weak) * 0.15 +
        has_metric * 0.20 +
        has_tool * 0.15 +
        specificity * 0.10 +
        ownership * 0.10 +
        impact * 0.10
    ) * 100.0

    return {
        "score": round(score, 2),
        "starts_strong": starts_strong,
        "starts_weak": starts_weak,
        "has_metric": has_metric,
        "has_tool": has_tool,
        "specificity": specificity,
        "ownership": ownership,
        "impact": impact,
    }


def score_bullets(bullets: List[str]) -> float:
    if not bullets:
        return 0.0
    return round(sum(score_bullet(b)["score"] for b in bullets) / len(bullets), 2)