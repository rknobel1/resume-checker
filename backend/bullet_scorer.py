import re
from typing import Dict, List, Optional


WEAK_STARTS = {
    "helped", "worked on", "responsible for", "tasked with", "assisted",
    "participated in", "involved in", "was part of"
}

STRONG_VERBS = {
    "built", "developed", "designed", "implemented", "optimized", "led",
    "launched", "deployed", "automated", "architected", "improved", "scaled",
    "engineered", "created", "trained", "fine-tuned", "analyzed", "debugged",
    "directed", "organized", "maintained", "reduced", "increased", "achieved",
    "delivered", "coordinated", "managed", "owned", "produced", "generated",
    "rendered", "preprocessed", "represented"
}

OWNERSHIP_VERBS = {
    "led", "owned", "designed", "architected", "engineered", "built",
    "developed", "implemented", "created", "directed", "organized",
    "trained", "fine-tuned", "managed", "coordinated", "maintained",
    "deployed", "launched", "preprocessed", "analyzed", "debugged"
}

IMPACT_WORDS = {
    "reduced", "increased", "improved", "saved", "grew", "cut", "boosted",
    "achieved", "enabled", "accelerated", "optimized", "scaled"
}

TECH_HINTS = {
    # backend / infra
    "python", "sql", "aws", "docker", "kubernetes", "fastapi",
    "node", "node.js", "next.js", "react", "typescript", "javascript",
    "postgres", "postgresql", "mongodb", "mysql", "airflow", "spark",
    "tensorflow", "pytorch", "torch", "sklearn", "scikit-learn",

    # data / ml
    "pandas", "numpy", "lstm", "gan", "patchgan", "maestro",
    "onnxruntime", "onnxruntime-web",

    # frontend / graphics
    "webgl", "pixijs", "pixi.js", "tkinter",

    # general
    "api", "apis", "rest", "graphql"
}

METRIC_RE = re.compile(
    r"("
    r"\d+%|"
    r"\$\d+(?:[.,]\d+)?|"
    r"\d+(?:\.\d+)?\s*(?:ms|millisecond|milliseconds|s|sec|secs|second|seconds|"
    r"minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)|"
    r"\d+(?:,\d{3})*(?:\+)?|"
    r"<\s*\d+(?:\.\d+)?\s*(?:ms|s|sec|secs|second|seconds)"
    r")",
    re.IGNORECASE
)


def _normalize(text: str) -> str:
    t = text.lower().strip()
    t = t.replace("ﬁ", "fi")
    t = t.replace("node.js", "node.js")
    t = t.replace("nextjs", "next.js")
    t = t.replace("reactjs", "react")
    t = t.replace("pixi js", "pixijs")
    return t


def _first_word(text: str) -> str:
    m = re.match(r"^\W*([a-zA-Z][a-zA-Z\-]*)", text)
    return m.group(1).lower() if m else ""


def _contains_tool(text: str) -> bool:
    low = _normalize(text)
    return any(hint in low for hint in TECH_HINTS)


def _has_metric(text: str) -> bool:
    return bool(METRIC_RE.search(text))


def _has_impact_signal(text: str, has_metric: bool) -> bool:
    low = _normalize(text)
    if has_metric:
        return True
    return any(word in low for word in IMPACT_WORDS)


def _has_ownership_signal(text: str) -> bool:
    low = _normalize(text)
    first = _first_word(low)
    if first in OWNERSHIP_VERBS:
        return True

    ownership_phrases = [
        "led", "owned", "designed", "architected", "engineered",
        "built", "developed", "implemented", "created", "organized",
        "directed", "coordinated", "managed"
    ]
    return any(p in low for p in ownership_phrases)


def _specificity_score(words: List[str], has_metric: bool, has_tool: bool) -> float:
    base = min(len(words) / 18.0, 1.0)

    # reward compact-but-specific bullets
    if has_metric:
        base += 0.15
    if has_tool:
        base += 0.10

    return min(base, 1.0)


def _fragment_penalty(text: str) -> float:
    """
    Penalize bullets that look like fragments rather than action statements.
    Example: '< 1 second Largest Contentful Paint through optimized asset loading'
    """
    first = _first_word(text)
    if not first:
        return 0.2

    if first not in STRONG_VERBS and first not in OWNERSHIP_VERBS:
        # allow noun-style result bullets with metrics, but slight penalty
        if _has_metric(text):
            return 0.08
        return 0.18

    return 0.0


def score_bullet(bullet: str, context_bullets: List[str] | None = None) -> Dict[str, float]:
    original = bullet.strip()
    text = _normalize(original)
    words = [w for w in re.split(r"\s+", text) if w]

    context_bullets = [b.strip() for b in (context_bullets or []) if b and b.strip()]
    other_context = " ".join(b for b in context_bullets if b.strip() != original)

    first = _first_word(text)
    starts_strong = 1.0 if first in STRONG_VERBS else 0.0
    starts_weak = 1.0 if any(text.startswith(v) for v in WEAK_STARTS) else 0.0

    has_metric_local = 1.0 if _has_metric(original) else 0.0
    has_tool_local = 1.0 if _contains_tool(original) else 0.0
    ownership = 1.0 if _has_ownership_signal(original) else 0.0
    impact = 1.0 if _has_impact_signal(original, has_metric=bool(has_metric_local)) else 0.0

    has_metric_context = 1.0 if other_context and _has_metric(other_context) else 0.0
    has_tool_context = 1.0 if other_context and _contains_tool(other_context) else 0.0

    # effective score gets partial credit from sibling bullets
    has_metric_effective = max(has_metric_local, 0.5 * has_metric_context)
    has_tool_effective = max(has_tool_local, 0.6 * has_tool_context)

    specificity = _specificity_score(
        words,
        bool(has_metric_local or has_metric_context),
        bool(has_tool_local or has_tool_context),
    )
    fragment_penalty = _fragment_penalty(original)

    score = (
        starts_strong * 0.16 +
        (1.0 - starts_weak) * 0.14 +
        has_metric_effective * 0.18 +
        has_tool_effective * 0.16 +
        specificity * 0.14 +
        ownership * 0.12 +
        impact * 0.10
    ) * 100.0

    score -= fragment_penalty * 100.0
    score = max(0.0, min(100.0, score))

    return {
        "score": round(score, 2),
        "starts_strong": starts_strong,
        "starts_weak": starts_weak,

        # keep original local-only fields
        "has_metric": has_metric_local,
        "has_tool": has_tool_local,
        "specificity": round(specificity, 3),
        "ownership": ownership,
        "impact": impact,
        "fragment_penalty": round(fragment_penalty, 3),

        # new context fields
        "has_metric_context": has_metric_context,
        "has_tool_context": has_tool_context,
        "has_metric_effective": round(has_metric_effective, 3),
        "has_tool_effective": round(has_tool_effective, 3),
    }


def score_bullets(bullets: List[str]) -> float:
    if not bullets:
        return 0.0
    return round(sum(score_bullet(b, context_bullets=bullets)["score"] for b in bullets) / len(bullets), 2)