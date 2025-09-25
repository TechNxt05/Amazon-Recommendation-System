# gemini_client.py
# Minimal wrapper to call Gemini (or any LLM). For demo we use a placeholder HTTP call.
# Replace call_gemini with your provider's SDK (Vertex AI, OpenAI, etc).
import os
import json
import requests

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", None)

def call_gemini_raw(prompt, max_tokens=256):
    # Placeholder: user must replace endpoint + auth method based on their Gemini setup.
    if not GEMINI_KEY:
        # Fallback: simple deterministic echoing (for offline demo)
        return {
            "bundle": [],
            "justification": "Gemini key not set — demo fallback returned no ASINs.",
            "total_price": 0.0
        }
    # Example (PSEUDOCODE) - swap URL & payload for your provider:
    url = "https://api.generative.google/v1beta2/models/gemini-mini:generate"  # EXAMPLE — change to your endpoint
    headers = {"Authorization": f"Bearer {GEMINI_KEY}", "Content-Type":"application/json"}
    payload = {
        "prompt": prompt,
        "max_output_tokens": max_tokens
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("Gemini call failed:", e)
        return {"error":"call_failed", "message": str(e)}

def generate_bundle(prompt_text, candidate_products):
    """
    candidate_products: pandas DataFrame with columns asin, title, price
    We craft a prompt that only allows these ASINs and asks the model to return JSON.
    """
    # build product list text (limit length to keep prompt small)
    lines = []
    for _, r in candidate_products.head(60).iterrows():
        lines.append(f"{r['asin']}: {r['title']} (₹{r['price']:.2f})")
    product_block = "\n".join(lines)
    user_prompt = f"""
You are a shopping assistant. Build a bundle that fits the user's constraints.
User request: {prompt_text}

Available products (use ONLY these ASINs; return JSON using ASINs only):
{product_block}

Return a strict JSON with keys:
- bundle: list of objects {{ "asin": "...", "qty": 1 }}
- justification: short reason (1-2 sentences)
- total_price: numeric

If you cannot satisfy constraints, return bundle: [] and justification explaining why.
"""
    raw = call_gemini_raw(user_prompt)
    # If fallback (no key), raw could be fallback dict or string. Try to parse robustly:
    # If provider returns text, attempt to parse JSON from it:
    if isinstance(raw, dict) and "bundle" in raw:
        return raw
    if isinstance(raw, dict) and "output" in raw:
        text = raw.get("output", "")
    elif isinstance(raw, str):
        text = raw
    elif isinstance(raw, dict):
        # unknown format from provider: try to stringify
        text = json.dumps(raw)
    else:
        text = str(raw)
    # try to extract JSON from text
    import re, json
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except:
            pass
    # fallback: no parseable JSON
    return {
        "bundle": [],
        "justification": "Could not parse Gemini output. Raw output saved.",
        "raw": text
    }
