import re
from typing import List, Dict, Any, Optional, Tuple
from embeddings import embed_texts, cosine_similarity


METRIC_RE = re.compile(
    r"(\d+%|\d+x|\d+\+? users|\d+\+? customers|\$\d+|\d+\s*(ms|sec|seconds|minutes|hours|days|months|years))",
    re.IGNORECASE
)


def has_metric(text: str) -> bool:
    return bool(METRIC_RE.search(text))


def classify_evidence_strength(bullet: str, requirement_text: str) -> int:
    bullet_l = bullet.lower()
    req_l = requirement_text.lower()

    mentioned = req_l in bullet_l
    metric = has_metric(bullet)
    strong_action = any(
        bullet_l.startswith(v) for v in [
            "built", "developed", "implemented", "designed", "led",
            "owned", "created", "optimized", "deployed", "architected"
        ]
    )
    tool_context = any(tok in bullet_l for tok in ["using", "with", "via", "in "])

    if not mentioned and not tool_context:
        return 0
    if mentioned and not strong_action:
        return 1
    if mentioned and strong_action and not metric:
        return 3
    if mentioned and strong_action and tool_context and not metric:
        return 4
    if mentioned and strong_action and metric:
        return 5
    return 2


def best_match_for_requirement(
    requirement_text: str,
    bullets: List[str],
    threshold: float = 0.35
) -> Tuple[Optional[str], float]:
    if not bullets:
        return None, 0.0

    req_vec = embed_texts([requirement_text])[0]
    bullet_vecs = embed_texts(bullets)

    scores = [cosine_similarity(req_vec, b) for b in bullet_vecs]
    best_idx = max(range(len(scores)), key=lambda i: scores[i])
    best_score = float(scores[best_idx])

    if best_score < threshold:
        return None, best_score
    return bullets[best_idx], best_score