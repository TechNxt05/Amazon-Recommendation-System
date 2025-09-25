# backend/precompute_trust_scores.py
"""
Improved precompute: collects evidence examples per ASIN and writes backend/models/trust_scores.json
"""
import os, csv, json, pickle
from collections import defaultdict

CANDIDATE_CSVS = [
    "backend/data/reviews.csv",
    "data/reviews.csv",
    "backend/data/electronics_small.csv",
    "backend/data/electronics_small_reviews.csv"
]

REVIEWS_PATH = next((p for p in CANDIDATE_CSVS if os.path.exists(p)), None)
if REVIEWS_PATH is None:
    raise SystemExit("No reviews CSV found in expected locations: " + ", ".join(CANDIDATE_CSVS))

print("Using reviews file:", REVIEWS_PATH)

# Optionally restrict to ASINs present in products.pkl (uncomment to enable)
USE_PRODUCTS_PKLIST = True
PRODUCTS_PKL = "backend/models/products.pkl"
PRODUCT_ASINS = None
if USE_PRODUCTS_PKLIST and os.path.exists(PRODUCTS_PKL):
    try:
        with open(PRODUCTS_PKL, "rb") as f:
            products = pickle.load(f)
        # handle DataFrame or list/dict
        if hasattr(products, "to_dict"):
            df = products
            if 'asin' in df.columns:
                PRODUCT_ASINS = set(df['asin'].astype(str).tolist())
        else:
            # try list or dict
            if isinstance(products, dict):
                PRODUCT_ASINS = set(products.keys())
            else:
                try:
                    PRODUCT_ASINS = set(str(x.get('asin')) for x in products if isinstance(x, dict) and x.get('asin'))
                except:
                    PRODUCT_ASINS = None
    except Exception as e:
        print("Failed to read products.pkl:", e)
        PRODUCT_ASINS = None

if PRODUCT_ASINS:
    print("Restricting to", len(PRODUCT_ASINS), "ASINs from products.pkl")
else:
    print("Not restricting by products.pkl (either not found or unreadable)")

# columns to search for review text & metadata
TEXT_FIELDS = ["review_text", "reviewText", "review", "summary", "review_body", "text", "review_body", "reviewText_clean"]

ASIN_FIELDS = ["asin", "product_id", "productId", "productID"]
RATING_FIELDS = ["overall", "rating", "stars"]
VOTE_FIELDS = ["vote", "helpful", "helpful_votes"]
REVIEWER_FIELDS = ["reviewerID", "user_id", "author"]

MAX_SCAN = 2_000_000
MAX_EXAMPLES = 3

agg = defaultdict(lambda: {"count":0, "sum_rating":0.0, "examples":[], "short_reviews":0, "helpful_sum":0})

with open(REVIEWS_PATH, encoding="utf-8", errors="ignore") as f:
    reader = csv.DictReader(f)
    # normalize header names set for speed
    headers = [h for h in reader.fieldnames] if reader.fieldnames else []
    for i, row in enumerate(reader):
        if i >= MAX_SCAN:
            break
        # find asin
        asin = None
        for c in ASIN_FIELDS:
            if c in row and row[c]:
                asin = str(row[c]).strip()
                break
        if not asin:
            # try alternative keys or skip
            continue
        if PRODUCT_ASINS and asin not in PRODUCT_ASINS:
            continue
        rec = agg[asin]
        rec["count"] += 1
        # rating
        rating = None
        for rf in RATING_FIELDS:
            if rf in row and row[rf]:
                try:
                    rating = float(row[rf])
                except:
                    rating = None
                break
        if rating is not None:
            rec["sum_rating"] += rating
        # helpful votes
        hv = None
        for vf in VOTE_FIELDS:
            if vf in row and row[vf]:
                hv_raw = str(row[vf])
                try:
                    hv = int(hv_raw.split("/")[0])
                except:
                    try:
                        hv = int(float(hv_raw))
                    except:
                        hv = 0
                break
        if hv:
            rec["helpful_sum"] += hv
        # extract review text from multiple possible fields
        text = ""
        for tf in TEXT_FIELDS:
            if tf in row and row[tf] and str(row[tf]).strip():
                text = str(row[tf]).strip()
                break
        # sometimes reviews are spread across 'summary' + 'reviewText'
        if not text:
            # try concatenating summary + review
            s1 = row.get("summary","") or row.get("title","")
            s2 = row.get("reviewText","") or row.get("review","")
            if s1 or s2:
                text = (str(s1).strip() + " " + str(s2).strip()).strip()
        if text:
            if len(text) < 40:
                rec["short_reviews"] += 1
            if len(rec["examples"]) < MAX_EXAMPLES:
                # collect small metadata
                reviewer = None
                for rf in REVIEWER_FIELDS:
                    if rf in row and row[rf]:
                        reviewer = row[rf]; break
                revtime = row.get("unixReviewTime") or row.get("reviewTime") or row.get("time")
                rec["examples"].append({
                    "reviewer": reviewer or None,
                    "rating": rating,
                    "helpful": hv,
                    "time": revtime,
                    "text": text[:500]
                })
        # continue scanning
    # end for

print("Aggregated", len(agg), "distinct ASINs (scanned up to", MAX_SCAN, "rows)")

def compute_score(rec):
    matched = rec["count"]
    if matched == 0:
        return 0.5
    avg_rating = rec["sum_rating"] / matched if rec["sum_rating"] else 3.0
    helpful_avg = rec["helpful_sum"] / matched if matched else 0.0
    short_frac = rec["short_reviews"] / matched if matched else 0.0
    s = (avg_rating - 1.0) / 4.0
    s *= (0.6 + 0.4 * min(matched, 50)/50.0)
    s += 0.12 * min(helpful_avg/5.0, 1.0)
    if short_frac > 0.6:
        s *= 0.85
    s = max(0.0, min(1.0, s))
    return round(s, 3)

out = {}
for asin, rec in agg.items():
    avg_rating = (rec["sum_rating"]/rec["count"]) if rec["sum_rating"] else 0.0
    out[asin] = {
        "asin": asin,
        "score": compute_score(rec),
        "rationale": f"precomputed heuristic(avg_rating={avg_rating:.2f},reviews={rec['count']})",
        "evidence": rec["examples"],   # list of small dicts
        "model": "precomputed_heuristic"
    }

os.makedirs("backend/models", exist_ok=True)
OUT_PATH = "backend/models/trust_scores.json"
with open(OUT_PATH, "w", encoding="utf-8") as fw:
    json.dump(out, fw, indent=2, ensure_ascii=False)

print("Wrote", OUT_PATH, "with", len(out), "entries")
