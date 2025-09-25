# app.py
# Main Flask app wiring all modules together.
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
import csv
import time
import traceback
import pandas as pd

# Application-specific imports (assumed to exist in your project)
# - recommender.get_candidates_by_prompt(prompt, top_n)
# - recommender.compute_scalar_scores(cands, w_price)
# - gemini_client.generate_bundle(prompt, candidates)
# - trust.product_trust_score(reviews_or_asin)  # optional ML implementation
# - embeddings.build_index(csv_path) and load_index_and_meta()
from recommender import get_candidates_by_prompt, compute_scalar_scores
from gemini_client import generate_bundle
# Note: we will lazy-import product_trust_score inside trust endpoint to be defensive.
from embeddings import build_index, load_index_and_meta

app = Flask(__name__)

# Allow only local dev origin(s). Change or widen as needed in production.
CORS(app, origins=["http://localhost:3001", "http://127.0.0.1:3001"], supports_credentials=True)

# Simple startup: if index missing, try to build from data/products.csv
if not os.path.exists("models/faiss_index.idx"):
    print("Faiss index not found. Attempting to build (requires data/products.csv)...")
    try:
        build_index("data/products.csv")
    except Exception as e:
        print("Index build failed:", e)

# helper: load reviews csv (simple local store)
def load_reviews_for_asin(asin):
    # expects data/reviews.csv with columns asin, review_text
    try:
        path = "data/reviews.csv"
        if not os.path.exists(path):
            return []
        df = pd.read_csv(path, dtype=str)
        if "asin" not in df.columns:
            return []
        revs = df[df["asin"].astype(str).str.strip() == str(asin).strip()]["review_text"].dropna().astype(str).tolist()
        return revs
    except Exception as e:
        print("load_reviews_for_asin error:", e)
        return []

@app.route("/api/recommend", methods=["GET"])
def recommend():
    """
    Query parameters:
      - prompt: text prompt (default: "laptop")
      - slider: 0..100 used to weight price importance (default: 30)
      - top_n: optional number of candidates to consider (default: 200)
    Returns top 20 results (JSON list of dicts with asin, title, price, score).
    """
    try:
        prompt = request.args.get("prompt", "laptop")
        slider = float(request.args.get("slider", 30))
        top_n = int(request.args.get("top_n", 200))
        w_price = max(0.0, min(1.0, slider / 100.0))

        print(f"[RECOMMEND] prompt={prompt!r} slider={slider} top_n={top_n} w_price={w_price:.3f}")
        cands = get_candidates_by_prompt(prompt, top_n=top_n)
        scored = compute_scalar_scores(cands, w_price=w_price)

        # Ensure the scored object is a DataFrame-like with columns asin,title,price,score
        cols = ["asin", "title", "price", "score"]
        for c in cols:
            if c not in scored.columns:
                scored[c] = None

        out = scored[cols].head(20).to_dict(orient="records")
        return jsonify(out)
    except Exception as e:
        tb = traceback.format_exc()
        print("[RECOMMEND ERROR]", e, "\n", tb)
        return jsonify({"error": "Failed to compute recommendations", "detail": str(e)}), 500

@app.route("/api/generate_bundle", methods=["POST"])
def gen_bundle():
    """
    Safe wrapper around gemini_client.generate_bundle:
    - Logs and returns detailed error responses (no server crash).
    - Normalizes the bundle to a list of ASINs/dicts.
    """
    try:
        body = request.json or {}
        prompt_text = body.get("prompt", "study setup under ₹15000")
        budget = body.get("budget", None)
        print(f"[BUNDLE] request prompt={prompt_text!r} budget={budget}")

        # call into your gemini client
        try:
            gemini_res = generate_bundle(prompt_text, [], budget=budget)
        except Exception as e_gem:
            # log full traceback for debugging the generate_bundle implementation
            tb = traceback.format_exc()
            print("[BUNDLE][generate_bundle] ERROR:", e_gem)
            print(tb)
            return jsonify({
                "error": "generate_bundle failed",
                "detail": str(e_gem),
                "trace": tb.splitlines()[-8:]
            }), 500

        # defensive normalization:
        if not isinstance(gemini_res, dict):
            print("[BUNDLE] Warning: generate_bundle returned non-dict; normalizing.")
            gemini_res = {"bundle": gemini_res}

        bundle = gemini_res.get("bundle", [])
        if bundle is None:
            bundle = []

        # load products table (best-effort)
        products = None
        for ppath in ("backend/models/products.pkl", "models/products.pkl", "backend/data/products.csv", "data/products.csv"):
            try:
                if os.path.exists(ppath):
                    if ppath.endswith(".pkl"):
                        products = pd.read_pickle(ppath)
                    elif ppath.endswith(".csv"):
                        products = pd.read_csv(ppath)
                    break
            except Exception:
                products = None

        enriched = []
        for item in bundle:
            asin = None
            if isinstance(item, dict):
                asin = item.get("asin") or item.get("ASIN")
            elif isinstance(item, str):
                asin = item
            if not asin:
                # try to extract asin-like text heuristically
                continue

            title = "Unknown"
            price = None
            try:
                if products is not None:
                    row = products[products["asin"].astype(str) == str(asin)]
                    if len(row) > 0:
                        if "title" in row.columns:
                            title = str(row["title"].iloc[0])
                        if "price" in row.columns:
                            try:
                                price = float(row["price"].iloc[0])
                            except Exception:
                                price = None
            except Exception:
                pass

            # trust: call product_trust_score if available, else fallback
            try:
                from trust import product_trust_score as _pts
                reviews = load_reviews_for_asin(asin)
                if reviews:
                    trust_score, flags = _pts(reviews)
                else:
                    try:
                        trust_score, flags = _pts(asin)
                    except Exception:
                        trust_score, flags = 0.5, {"note": "trust function failed with asin"}
            except Exception as e_trust:
                trust_score, flags = 0.5, {"note": "trust unavailable", "error": str(e_trust)[:200]}

            enriched.append({"asin": asin, "title": title, "price": price, "trust": trust_score, "flags": flags})

        return jsonify({
            "raw_gemini": gemini_res,
            "bundle": enriched,
            "justification": gemini_res.get("justification", "")
        })
    except Exception as e:
        tb = traceback.format_exc()
        print("[BUNDLE][TOP LEVEL ERROR]", e, "\n", tb)
        return jsonify({
            "error": "Bundle generation failed",
            "detail": str(e),
            "trace": tb.splitlines()[-8:]
        }), 500


@app.route("/api/trust", methods=["GET"])
@app.route("/api/trust/<asin>", methods=["GET"])
def trust_endpoint(asin=None):
    """
    Robust trust endpoint:
      - Attempts to call a ML-based product_trust_score if available.
      - Falls back to a lightweight CSV heuristic if ML fails or isn't present.
      - Returns JSON with keys: asin, score (0..1), explain (string), optionally ml_error.
    """
    asin = asin or request.args.get("asin") or None
    if asin is None:
        return jsonify({"error": "No ASIN provided"}), 400

    ml_err = None

    # 1) Try ML-based trust implementation (lazy import)
    try:
        from trust import product_trust_score as product_trust_score_fn  # lazy import
        try:
            # product_trust_score may accept a list of reviews OR asin; handle both possibilities
            # If you prefer a different call signature, adapt here.
            reviews = load_reviews_for_asin(asin)
            if reviews:
                result = product_trust_score_fn(reviews)
            else:
                try:
                    result = product_trust_score_fn(asin)
                except Exception:
                    # last resort try calling with [asin]
                    result = product_trust_score_fn([asin])
            if isinstance(result, dict):
                # ensure expected keys
                ret = result
                ret.setdefault("asin", asin)
                return jsonify(ret)
            else:
                # possibly returns (score, flags)
                try:
                    score, flags = result
                    return jsonify({"asin": asin, "score": float(score), "flags": flags})
                except Exception:
                    # unknown format
                    ml_err = "ML trust returned unexpected type"
        except Exception as e_ml:
            ml_err = str(e_ml)
            print("[TRUST ML ERROR]", e_ml)
    except Exception as e_import:
        ml_err = str(e_import)
        # don't print too verbosely; record for response
        print("[TRUST IMPORT ERROR]", e_import)

    # 2) Lightweight heuristic fallback (bounded CSV scan)
    try:
        candidates = [
            "backend/data/reviews.csv",
            "data/reviews.csv",
            "backend/data/electronics_small.csv",
            "backend/data/electronics_small_reviews.csv",
            "data/electronics_small_reviews.csv",
        ]
        reviews_path = next((p for p in candidates if os.path.exists(p)), None)
        if reviews_path is None:
            return jsonify({"asin": asin, "score": 0.5, "explain": "No reviews CSV found; returning neutral score.", "ml_error": ml_err})

        MAX_ROWS = 50000   # safety cap for reading file
        MATCH_LIMIT = 2000 # cap how many product reviews to scan
        matched = 0
        sum_rating = 0.0
        sum_len = 0
        helpful_sum = 0

        with open(reviews_path, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            asin_col = None
            # determine asin column from header
            headers = reader.fieldnames or []
            for c in ["asin", "product_id", "productID", "productId", "ASIN"]:
                if c in headers:
                    asin_col = c
                    break

            for i, r in enumerate(reader):
                if i > MAX_ROWS:
                    break

                if asin_col:
                    match = (str(r.get(asin_col, "")).strip() == str(asin).strip())
                else:
                    # if file doesn't have asin column, skip matching (unsafe)
                    match = False

                if not match:
                    continue

                matched += 1
                # rating
                try:
                    val = r.get("overall") or r.get("rating") or r.get("stars") or ""
                    sum_rating += float(val) if val != "" else 0.0
                except:
                    pass

                txt = (r.get("reviewText") or r.get("review") or r.get("review_text") or "")
                sum_len += len(str(txt))

                hv = r.get("vote") or r.get("helpful") or r.get("helpful_votes") or ""
                try:
                    hv_val = int(str(hv).split("/")[0]) if hv else 0
                except:
                    hv_val = 0
                helpful_sum += hv_val

                if matched >= MATCH_LIMIT:
                    break

        if matched == 0:
            return jsonify({"asin": asin, "score": 0.5, "explain": "No reviews found for ASIN; neutral score.", "ml_error": ml_err})

        avg_rating = (sum_rating / matched) if matched else 3.0
        avg_len = (sum_len / matched) if matched else 0
        helpful_ratio = (helpful_sum / matched) if matched else 0.0

        # scoring heuristic
        s = (avg_rating - 1.0) / 4.0  # map 1..5 -> 0..1
        if avg_len < 50:
            s *= 0.92
        elif avg_len > 200:
            s *= 1.02
        # penalize low review count
        s *= (0.6 + 0.4 * min(matched, 50) / 50.0)
        # small boost from helpful votes
        s += 0.15 * min(helpful_ratio / 5.0, 1.0)
        s = max(0.0, min(1.0, s))

        explain = f"heuristic: avg_rating={avg_rating:.2f}, avg_len={avg_len:.0f}, reviews={matched}, helpful_sum={helpful_sum}"
        resp = {"asin": asin, "score": round(s, 3), "explain": explain}
        if ml_err:
            resp["ml_error"] = ml_err
        return jsonify(resp)

    except Exception as final_e:
        tb = traceback.format_exc()
        print("[TRUST FALLBACK ERROR]", final_e, "\n", tb)
        return jsonify({
            "asin": asin,
            "score": 0.5,
            "explain": "Fallback: error computing heuristic.",
            "error": str(final_e)[:200],
            "trace": tb.splitlines()[-6:]
        }), 500

@app.route("/api/log", methods=["POST", "OPTIONS"])
def log_endpoint():
    """
    Lightweight logging endpoint - receives JSON { level, message, meta, ts } and prints to server console.
    This endpoint is used by frontend sendLog() and is CORS-enabled by flask_cors above.
    """
    if request.method == "OPTIONS":
        # flask_cors should handle, but be explicit
        resp = make_response("", 204)
        resp.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST,OPTIONS"
        return resp

    data = request.json or {}
    level = str(data.get("level", "info")).lower()
    message = data.get("message", "")
    meta = data.get("meta", {})
    ts = data.get("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))

    prefix = f"[Front->Server][{level.upper()}][{ts}]"
    if level == "error":
        print(prefix, "ERROR:", message, meta)
    elif level == "warn":
        print(prefix, "WARN:", message, meta)
    else:
        print(prefix, message, meta)
    return ("", 204)

if __name__ == "__main__":
    # Bind to 0.0.0.0 or 127.0.0.1 depending on dev needs; debug True for dev only.
    app.run(host="127.0.0.1", port=5000, debug=True)
