import re
from typing import List, Optional, Tuple
from embeddings import embed_texts, cosine_similarity


METRIC_RE = re.compile(
    r"(\d+%|\d+x|\d+\+? users|\d+\+? customers|\$\d+|\d+\s*(ms|sec|seconds|minutes|hours|days|months|years))",
    re.IGNORECASE
)

STRONG_ACTIONS = [
    "built", "developed", "implemented", "designed", "led",
    "owned", "created", "optimized", "deployed", "architected",
    "engineered", "launched", "improved", "automated", "migrated",
]

STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "to", "for", "in", "with",
    "on", "using", "via", "by", "from", "experience", "knowledge",
    "ability", "strong", "plus", "preferred", "required"
}


def has_metric(text: str) -> bool:
    return bool(METRIC_RE.search(text))


def normalize_text(text: str) -> str:
    t = text.lower()
    t = t.replace("c++", "cpp")
    t = t.replace("c#", "csharp")
    t = t.replace("node.js", "nodejs")
    t = t.replace("next.js", "nextjs")
    t = t.replace("scikit-learn", "sklearn")
    t = re.sub(r"[^a-z0-9\s+#./-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def token_set(text: str) -> set[str]:
    return {
        tok for tok in normalize_text(text).split()
        if tok and tok not in STOPWORDS
    }


def requirement_aliases(requirement_text: str) -> List[str]:
    req = normalize_text(requirement_text)

    alias_map = {
        "python": ["python"],
        "sql": ["sql"],
        "aws": ["aws", "amazon web services"],
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
        "react": ["react", "reactjs", "react.js"],
        "nextjs": ["nextjs", "next.js"],
        "nodejs": ["nodejs", "node", "node.js"],
        "postgresql": ["postgresql", "postgres"],
        "mongodb": ["mongodb", "mongo"],
        "pytorch": ["pytorch", "torch"],
        "tensorflow": ["tensorflow", "tf"],
        "sklearn": ["sklearn", "scikit-learn", "scikit learn"],
        "cpp": ["cpp", "c++"],
        "csharp": ["csharp", "c#"],
        "rest api": ["rest api", "restful api", "api", "apis"],
        "machine learning": ["machine learning", "ml"],
        "data analysis": ["data analysis", "analytics"],
    }

    aliases = [req]
    for canonical, vals in alias_map.items():
        if canonical in req:
            aliases.extend(vals)

    # unique while keeping order
    seen = set()
    out = []
    for a in aliases:
        a = normalize_text(a)
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def alias_overlap_score(requirement_text: str, candidate_text: str) -> float:
    candidate_norm = normalize_text(candidate_text)
    candidate_tokens = token_set(candidate_text)

    best = 0.0
    for alias in requirement_aliases(requirement_text):
        alias_tokens = [t for t in alias.split() if t not in STOPWORDS]
        if not alias_tokens:
            continue

        if len(alias_tokens) == 1:
            score = 1.0 if alias_tokens[0] in candidate_tokens else 0.0
        else:
            if alias in candidate_norm:
                score = 1.0
            else:
                overlap = len(set(alias_tokens) & candidate_tokens) / len(set(alias_tokens))
                score = overlap

        best = max(best, score)

    return best


def classify_evidence_strength(
    bullet: str,
    requirement_text: str,
    semantic_score: float = 0.0
) -> int:
    bullet_l = normalize_text(bullet)

    alias_score = alias_overlap_score(requirement_text, bullet)
    metric = has_metric(bullet)
    strong_action = any(bullet_l.startswith(v) for v in STRONG_ACTIONS)
    tool_context = any(tok in bullet_l for tok in ["using", "with", "via", "in", "built", "developed"])
    req_tokens = token_set(requirement_text)
    bullet_tokens = token_set(bullet)
    token_overlap = (len(req_tokens & bullet_tokens) / max(len(req_tokens), 1)) if req_tokens else 0.0

    match_signal = max(alias_score, token_overlap, semantic_score)

    if match_signal < 0.35 and not tool_context:
        return 0
    if match_signal >= 0.35 and not strong_action:
        return 1
    if match_signal >= 0.50 and strong_action and not metric:
        return 3
    if match_signal >= 0.65 and strong_action and tool_context and not metric:
        return 4
    if match_signal >= 0.65 and strong_action and metric:
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

    blended_scores = []

    for bullet, vec in zip(bullets, bullet_vecs):
        semantic = float(cosine_similarity(req_vec, vec))
        alias_score = alias_overlap_score(requirement_text, bullet)

        # blend exact-ish skill overlap with semantic similarity
        blended = (semantic * 0.7) + (alias_score * 0.3)
        blended_scores.append(blended)

    best_idx = max(range(len(blended_scores)), key=lambda i: blended_scores[i])
    best_score = float(blended_scores[best_idx])

    if best_score < threshold:
        return None, best_score

    return bullets[best_idx], best_score