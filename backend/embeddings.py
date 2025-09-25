# backend/embeddings.py
"""
Safe embeddings retrieval for Windows demo:
- Does NOT import sentence-transformers or transformers at module import time.
- Loads precomputed embeddings (product_embeddings.npy) and products.pkl.
- Uses NumPy cosine similarity to retrieve top-k results.
- If embeddings or products missing, raises descriptive errors.
"""

import os
import pickle
import numpy as np
import pandas as pd

MODELS_DIR = "models"
EMB_PATH = os.path.join(MODELS_DIR, "product_embeddings.npy")
PRODUCTS_PKL = os.path.join(MODELS_DIR, "products.pkl")
# If you built a faiss index on Colab and copied it, those files can still exist,
# but we will rely on numpy arrays here to avoid requiring faiss on Windows.

# load artifacts lazily and cache in module
_EMB = None
_PRODUCTS = None

def _ensure_loaded():
    global _EMB, _PRODUCTS
    if _EMB is None or _PRODUCTS is None:
        if not os.path.exists(EMB_PATH):
            raise FileNotFoundError(f"Embeddings file not found: {EMB_PATH}. Please place product_embeddings.npy in backend/models/")
        if not os.path.exists(PRODUCTS_PKL):
            raise FileNotFoundError(f"Products pickle not found: {PRODUCTS_PKL}. Please place products.pkl in backend/models/")
        _EMB = np.load(EMB_PATH)
        # ensure float32
        if _EMB.dtype != np.float32:
            _EMB = _EMB.astype("float32")
        with open(PRODUCTS_PKL, "rb") as f:
            _PRODUCTS = pickle.load(f)
        # normalize once for cosine
        norms = np.linalg.norm(_EMB, axis=1, keepdims=True) + 1e-9
        _EMB = _EMB / norms

def load_index_and_meta():
    """
    Backwards-compatible loader:
    Returns (None, emb, products) where None is placeholder for faiss index,
    emb is numpy array (N, D), products is a pandas DataFrame.
    """
    _ensure_loaded()
    return None, _EMB, _PRODUCTS

def retrieve_by_text_embedding(query_embedding, topk=50):
    """
    If you have a precomputed query embedding (numpy array shape (D,) or (1,D)),
    this will return the topk product rows (pandas.DataFrame) sorted by cosine similarity.
    """
    _ensure_loaded()
    q = np.array(query_embedding, dtype="float32")
    if q.ndim == 1:
        q = q.reshape(1, -1)
    # normalize
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)
    sims = np.dot(_EMB, q.T).squeeze()  # (N,)
    idxs = np.argsort(-sims)[:topk]
    results = _PRODUCTS.iloc[idxs].reset_index(drop=True).copy()
    # attach score
    results["score"] = sims[idxs].tolist()
    return results

def retrieve_by_text(query, topk=50):
    """
    Safe fallback: do NOT encode the query locally (that would import sentence-transformers).
    This function expects the calling code to provide the query embedding OR to use
    a simple keyword-match fallback. For demo convenience, we'll implement a cheap
    TF-free fallback: keyword-based retrieval using product titles + descriptions.
    This returns topk products by simple BM25-like scoring (term frequency) as fallback.
    """
    # try to use embeddings if a precomputed query vector is stored in an env var (rare)
    # Otherwise use keyword-based ranking (no TF/transformers required).
    _ensure_loaded()
    q = str(query).lower().strip()
    if q == "":
        # return top items by original order
        res = _PRODUCTS.head(topk).copy()
        res["score"] = 1.0
        return res

    # simple token count score on title + description
    def score_row(row):
        text = (str(row.get("title","")) + " " + str(row.get("description",""))).lower()
        cnt = 0
        for tok in q.split():
            cnt += text.count(tok)
        # add tiny bias for short products
        return cnt

    scores = _PRODUCTS.apply(score_row, axis=1).values
    idxs = np.argsort(-scores)[:topk]
    results = _PRODUCTS.iloc[idxs].reset_index(drop=True).copy()
    # normalize scores to [0,1]
    sc = scores[idxs].astype(float)
    if sc.max() - sc.min() > 0:
        sc_norm = (sc - sc.min()) / (sc.max() - sc.min())
    else:
        sc_norm = np.ones_like(sc)
    results["score"] = sc_norm.tolist()
    return results

# Optional utility: nearest_by_embedding_api(query_text, encoder_fn, topk)
def retrieve_by_text_with_encoder_fn(query, encoder_fn, topk=50):
    """
    If you *do* want semantic retrieval (e.g., from Colab or a hosted encoder),
    pass an encoder function that accepts a list[str] and returns numpy array (N, D).
    Example:
        from some_service import remote_encode
        df = retrieve_by_text_with_encoder_fn("laptop", lambda texts: remote_encode(texts), topk=50)
    This keeps heavy encoding outside this module.
    """
    emb = encoder_fn([query])
    if isinstance(emb, list):
        emb = np.array(emb, dtype="float32")
    return retrieve_by_text_embedding(emb[0], topk=topk)

# Add this at the end of backend/embeddings.py

def build_index(products_csv="data/products.csv", index_out="models/faiss_index.idx", force_rebuild=False):
    """
    Stub build_index function.

    - Intended to be run where sentence-transformers + faiss are available (Colab or a properly configured machine).
    - On Windows with no TF/transformers this function will raise a helpful error telling you to run the Colab pipeline.
    - If you DO have sentence-transformers and faiss installed locally and want to build here,
      set environment up correctly and call this function (it will attempt to import the required libs).
    """
    # If user explicitly wants to build here and has libs installed, attempt a lazy import
    try:
        # lazy import so normal server runs won't attempt TF import
        from sentence_transformers import SentenceTransformer
        import faiss
        import numpy as np
        import pandas as pd
    except Exception as e:
        # helpful message instead of noisy traceback
        raise RuntimeError(
            "Local build_index unavailable: this environment does not have the necessary ML libraries "
            "installed or importing them would trigger platform issues (TensorFlow on Windows). "
            "Recommended options:\n"
            "1) Build embeddings & Faiss index on Colab (GPU) using the notebook instructions we discussed, "
            "then copy backend/models/product_embeddings.npy, products.pkl and faiss_index.idx into backend/models/.\n"
            "2) If you insist on building locally, create a clean conda env, install sentence-transformers & faiss-cpu, "
            "and then call build_index again. Error from import: " + str(e)
        )

    # If we reach here, libs are available — perform the build (simple implementation)
    print("Running local build_index (this machine has sentence-transformers & faiss installed).")
    df = pd.read_csv(products_csv)
    df = df.fillna("")
    texts = (df.get("title","") + " " + df.get("description","")).tolist()
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(texts, show_progress_bar=True, convert_to_numpy=True).astype("float32")
    # normalize for cosine
    faiss.normalize_L2(emb)
    d = emb.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(emb)
    # make models dir
    os.makedirs(os.path.dirname(index_out) or "models", exist_ok=True)
    faiss.write_index(index, index_out)
    np.save(os.path.join(os.path.dirname(index_out),"product_embeddings.npy"), emb)
    df.to_pickle(os.path.join(os.path.dirname(index_out),"products.pkl"))
    print("Built index and saved to", os.path.dirname(index_out))
