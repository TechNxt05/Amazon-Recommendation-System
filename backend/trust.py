# backend/trust.py
# Hybrid trust pipeline with lazy imports and precomputed-cache support.

import re
import time
import os
import json
import csv
import traceback
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple, Optional

import numpy as np

# -----------------------
# Config
# -----------------------
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
USE_LLM = False            # Turn True only when you wire an LLM and llm_call_fn
LLM_NAME = "gemini"        # placeholder
PROMO_KEYWORDS = [
    "must buy", "best ever", "buy now", "100% recommended",
    "paid review", "sponsored", "free product", "amazing product",
    "highly recommend", "five stars", "check seller"
]

# -----------------------
# Lazy imports helpers
# -----------------------
def _get_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise ImportError(f"SentenceTransformer unavailable: {e}") from e
    return SentenceTransformer(EMBED_MODEL_NAME)

def _get_isolation_forest():
    try:
        from sklearn.ensemble import IsolationForest
    except Exception as e:
        raise ImportError(f"IsolationForest unavailable: {e}") from e
    return IsolationForest

# -----------------------
# Basic heuristics
# -----------------------
def heuristic_score_text(text: str) -> float:
    if not isinstance(text, str) or len(text.strip()) == 0:
        return 0.0
    t = text.strip()
    score = 0.0
    if len(t) < 20:
        score += 0.25
    exm = len(re.findall(r"!+", t))
    score += min(0.2, exm * 0.12)
    words = t.split()
    if words:
        allcaps = sum(1 for w in words if w.isupper() and len(w) > 1)
        score += min(0.12, 0.03 * allcaps)
    low = t.lower()
    for kw in PROMO_KEYWORDS:
        if kw in low:
            score += 0.35
    if re.search(r"(http|www\.)", t):
        score += 0.2
    return max(0.0, min(score, 1.0))

# -----------------------
# Embedding + anomaly detection
# -----------------------
def compute_anomaly_scores_for_reviews(review_texts: List[str]) -> List[float]:
    if not review_texts:
        return []
    try:
        model = _get_sentence_transformer()
        IsolationForest = _get_isolation_forest()
        emb = model.encode(review_texts, convert_to_numpy=True, show_progress_bar=False)
        iso = IsolationForest(contamination=0.05, random_state=42)
        iso.fit(emb)
        raw = iso.decision_function(emb)  # higher = more normal
        arr = np.array(raw, dtype=float)
        rng = arr.max() - arr.min()
        if rng == 0:
            norm = np.zeros_like(arr)
        else:
            norm = (arr - arr.min()) / rng
        anomaly = 1.0 - norm
        return anomaly.tolist()
    except Exception:
        # safe fallback to zeros if libs/models missing
        return [0.0] * len(review_texts)

# -----------------------
# Graph / temporal heuristics
# -----------------------
def graph_temporal_flags(reviews_meta: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
    flags: List[str] = []
    if not reviews_meta:
        return 0.0, flags
    times = [int(r.get('unixReviewTime') or 0) for r in reviews_meta]
    if not any(times):
        return 0.0, flags
    days = [time.strftime('%Y-%m-%d', time.localtime(t)) if t > 0 else "NA" for t in times]
    day_counts = Counter(days)
    max_day_frac = max(day_counts.values()) / len(days)
    if max_day_frac > 0.3:
        flags.append("temporal_burst")
    users = [r.get('user_id') or r.get('reviewerID') or 'unknown' for r in reviews_meta]
    unique_frac = (len(set(users)) / len(users)) if users else 1.0
    if unique_frac < 0.2:
        flags.append("low_user_diversity")
    penalty = 0.0
    if "temporal_burst" in flags:
        penalty += 0.35
    if "low_user_diversity" in flags:
        penalty += 0.35
    return min(penalty, 1.0), flags

# -----------------------
# Optional LLM wrapper (robust parse)
# -----------------------
def llm_check_review_text(text: str, llm_call_fn) -> Optional[Tuple[float, str]]:
    if not USE_LLM or llm_call_fn is None:
        return None
    prompt = f"""
You are an assistant that classifies whether a product review is likely fake (spam/promotional) or genuine.
Return strict JSON ONLY with keys:
{{"label":"fake" or "real", "confidence":0.0-1.0, "reason":"1-2 sentence justification"}}
Review:
\"\"\"{text}\"\"\"
"""
    try:
        raw = llm_call_fn(prompt, max_tokens=180)
        if isinstance(raw, dict) and "label" in raw and "confidence" in raw:
            label = raw.get("label", "real")
            conf = float(raw.get("confidence", 0.5))
            fake_prob = conf if str(label).lower().startswith("fake") else 1.0 - conf
            return fake_prob, raw.get("reason", "")
        txt = raw if isinstance(raw, str) else (raw.get("output", "") if isinstance(raw, dict) else str(raw))
        import re as _re, json as _json
        m = _re.search(r"\{.*\}", txt, _re.S)
        if m:
            parsed = _json.loads(m.group(0))
            label = parsed.get("label", "real")
            conf = float(parsed.get("confidence", 0.5))
            fake_prob = conf if str(label).lower().startswith("fake") else 1.0 - conf
            return fake_prob, parsed.get("reason", "")
    except Exception:
        return None
    return None

# -----------------------
# Main pipeline for structured reviews
# -----------------------
def product_trust_pipeline(reviews_meta_texts: List[Dict[str, Any]], llm_call_fn=None) -> Tuple[float, List[str], Dict[str, Any]]:
    texts = [r.get('review_text') or r.get('review') or "" for r in reviews_meta_texts]
    heur_scores = [heuristic_score_text(t) for t in texts]
    anomaly_scores = compute_anomaly_scores_for_reviews(texts)
    per_review_susp = []
    for h, a in zip(heur_scores, anomaly_scores):
        score = 0.6 * a + 0.4 * h
        per_review_susp.append(min(1.0, float(score)))
    temporal_penalty, graph_flags = graph_temporal_flags(reviews_meta_texts)
    llm_flags = []
    if USE_LLM and llm_call_fn is not None:
        idxs = sorted(range(len(per_review_susp)), key=lambda i: per_review_susp[i], reverse=True)[:3]
        for i in idxs:
            if 0.25 < per_review_susp[i] < 0.85:
                res = llm_check_review_text(texts[i], llm_call_fn)
                if res:
                    fake_prob, reason = res
                    llm_flags.append({"idx": i, "fake_prob": float(fake_prob), "reason": reason})
                    per_review_susp[i] = 0.6 * per_review_susp[i] + 0.4 * float(fake_prob)
    avg_susp = float(np.mean(per_review_susp)) if per_review_susp else 0.0
    combined = avg_susp + temporal_penalty * 0.8
    combined = min(1.0, combined)
    trust_score = round(1.0 - combined, 3)
    flags = []
    if avg_susp > 0.5:
        flags.append("many_suspicious_reviews")
    flags += graph_flags
    if llm_flags:
        flags.append("llm_checked")
    details = {
        "per_review_suspicion": per_review_susp,
        "avg_suspicion": avg_susp,
        "temporal_penalty": temporal_penalty,
        "llm_flags": llm_flags,
        "graph_flags": graph_flags
    }
    return trust_score, flags, details

# -----------------------
# CSV heuristic fallback for ASIN scanning
# -----------------------
def _heuristic_trust_from_reviews(asin: str, reviews_path_candidates: Optional[List[str]] = None) -> Dict[str, Any]:
    candidates = reviews_path_candidates or [
        "backend/data/reviews.csv",
        "data/reviews.csv",
        "backend/data/electronics_small.csv",
        "backend/data/electronics_small_reviews.csv"
    ]
    reviews_path = next((p for p in candidates if os.path.exists(p)), None)
    if not reviews_path:
        return {"asin": asin, "score": 0.5, "rationale": "No reviews file found; neutral score.", "evidence": [], "model": "heuristic"}

    MAX_SCAN = 20000
    matched = 0
    sum_rating = 0.0
    helpful_sum = 0
    short_reviews = 0
    examples = []
    with open(reviews_path, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            if i > MAX_SCAN:
                break
            asin_col = None
            for c in ("asin", "product_id", "productId", "productID"):
                if c in r:
                    asin_col = c
                    break
            if asin_col and str(r.get(asin_col, "")).strip() != asin:
                continue
            matched += 1
            try:
                sum_rating += float(r.get("rating") or r.get("overall") or 0.0)
            except:
                pass
            txt = (r.get("review_text") or r.get("reviewText") or r.get("review") or "")
            if len(txt) < 30:
                short_reviews += 1
            hv = r.get("vote") or r.get("helpful_votes") or r.get("helpful")
            try:
                helpful_sum += int(str(hv).split("/")[0]) if hv else 0
            except:
                pass
            if len(examples) < 3 and txt:
                examples.append({"review": txt[:500], "rating": r.get("rating") or r.get("overall")})
    if matched == 0:
        return {"asin": asin, "score": 0.5, "rationale": "No reviews for ASIN; neutral.", "evidence": [], "model": "heuristic"}
    avg_rating = sum_rating / matched if matched else 3.0
    short_frac = short_reviews / matched
    helpful_avg = helpful_sum / matched if matched else 0.0
    s = (avg_rating - 1.0) / 4.0
    s *= (0.6 + 0.4 * min(matched, 50) / 50.0)
    s += 0.12 * min(helpful_avg / 5.0, 1.0)
    if short_frac > 0.6:
        s *= 0.85
    s = max(0.0, min(1.0, s))
    return {
        "asin": asin,
        "score": round(s, 3),
        "rationale": f"heuristic(avg_rating={avg_rating:.2f}, reviews={matched}, short_frac={short_frac:.2f})",
        "evidence": examples,
        "model": "heuristic"
    }

# -----------------------
# Precomputed trust cache loader
# -----------------------
_TRUST_CACHE: Dict[str, Any] = None

def _load_trust_cache() -> Dict[str, Any]:
    global _TRUST_CACHE
    if _TRUST_CACHE is None:
        path = os.path.join("backend", "models", "trust_scores.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    _TRUST_CACHE = json.load(f)
            except Exception:
                _TRUST_CACHE = {}
        else:
            _TRUST_CACHE = {}
    return _TRUST_CACHE

# -----------------------
# LLM stub (replace to wire LLM)
# -----------------------
def call_llm_for_fake_review(asin: str) -> Dict[str, Any]:
    # Replace with real LLM call implementation if you wire Gemini/HF etc.
    return {"asin": asin, "score": 0.5, "rationale": "LLM not configured.", "evidence": [], "model": "none"}

# -----------------------
# Public wrapper expected by app.py
# -----------------------
def product_trust_score(arg) -> Dict[str, Any]:
    """
    Unified wrapper returning a dict:
      - If arg is str: treat as ASIN and return dict (precomputed -> LLM -> CSV heuristic)
      - If arg is list[str] or list[dict]: run pipeline and return dict
    """
    try:
        # if list of dicts with metadata -> pipeline
        if isinstance(arg, list) and len(arg) > 0 and isinstance(arg[0], dict):
            trust, flags, details = product_trust_pipeline(arg, llm_call_fn=None if not USE_LLM else call_llm_for_fake_review)
            return {
                "asin": None,
                "score": trust,
                "rationale": f"pipeline heuristic, flags={flags}",
                "evidence": details.get("per_review_suspicion", [])[:3],
                "model": "pipeline",
                "details": details
            }

        # if list of strings -> treat as texts
        if isinstance(arg, list) and all(isinstance(x, str) for x in arg):
            structured = [{"review_text": r} for r in arg]
            trust, flags, details = product_trust_pipeline(structured, llm_call_fn=None if not USE_LLM else call_llm_for_fake_review)
            return {
                "asin": None,
                "score": trust,
                "rationale": f"pipeline on texts, flags={flags}",
                "evidence": details.get("per_review_suspicion", [])[:3],
                "model": "pipeline",
                "details": details
            }

        # if string -> ASIN path
        if isinstance(arg, str):
            asin = arg.strip()
            # 1) try LLM if enabled
            if USE_LLM:
                out = call_llm_for_fake_review(asin)
                if isinstance(out, dict) and "score" in out:
                    out.setdefault("asin", asin)
                    out.setdefault("model", LLM_NAME)
                    return out
            # 2) try precomputed cache
            cache = _load_trust_cache()
            if asin in cache:
                return cache[asin]
            # 3) fallback to CSV heuristic
            return _heuristic_trust_from_reviews(asin)

        # unsupported input
        return {"asin": None, "score": 0.5, "rationale": "Unsupported input to product_trust_score", "evidence": [], "model": "fallback"}

    except Exception as e:
        tb = traceback.format_exc()
        return {"asin": None, "score": 0.5, "rationale": "error computing trust", "error": str(e)[:200], "trace": tb.splitlines()[-3:], "model": "error"}
