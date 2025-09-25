# backend/recreate_products_pkl.py
import os, pickle, pandas as pd

# Try these CSVs in order; adjust if your CSV has a different name
csv_candidates = [
    "backend/data/products.csv",
    "data/products.csv",
    "backend/data/electronics_small.csv",
]

os.makedirs("backend/models", exist_ok=True)

for p in csv_candidates:
    if os.path.exists(p):
        print("Using", p)
        df = pd.read_csv(p)
        df = df.fillna("")
        # Optionally select useful columns only:
        # keep = ["asin","title","description","price","brand","categories"]
        # df = df[[c for c in keep if c in df.columns]]
        with open("backend/models/products.pkl", "wb") as f:
            pickle.dump(df, f)
        print("Wrote backend/models/products.pkl (rows=%d)" % len(df))
        break
else:
    print("No products CSV found. Put products.csv in backend/data/ or data/ and rerun.")
