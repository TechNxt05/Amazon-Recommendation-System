# recommender.py
# Candidate generation, simple rel_score proxy, scalarized scoring.
import numpy as np
import pandas as pd
from embeddings import load_index_and_meta, retrieve_by_text

# Basic candidate generation: if user_history provided (list of ASINs),
# we return items nearest to most recent item; else use retrieval by popular text.
def get_candidates_by_prompt(prompt, top_n=200):
    # Use embedding retrieval as candidate generator
    df = retrieve_by_text(prompt, topk=top_n)
    # compute rel_score proxy: use avg rating if available, else popularity placeholder
    if 'avg_rating' in df.columns:
        df['rel_score'] = df['avg_rating'].fillna(3.0)
    else:
        df['rel_score'] = 3.0 + (np.log1p(df.index + 1) * 0.01)  # tiny proxy
    if 'price' not in df.columns:
        df['price'] = np.random.uniform(100, 5000, size=len(df))  # simulate
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(df['price'].median())
    df = df[['asin','title','price','rel_score']]
    return df

def normalize_series(s):
    s2 = s.copy().astype(float)
    return (s2 - s2.min()) / (s2.max() - s2.min() + 1e-9)

def compute_scalar_scores(cands_df, w_price=0.3):
    # w_price in [0,1], w_rel = 1 - w_price
    df = cands_df.copy()
    df['rel_norm'] = normalize_series(df['rel_score'])
    df['price_norm'] = normalize_series(df['price'])
    df['score'] = (1-w_price) * df['rel_norm'] + w_price * df['price_norm']
    return df.sort_values('score', ascending=False).reset_index(drop=True)
