# quick script: prepare_products_reviews.py  (run in repo root)
from datasets import load_dataset
import pandas as pd
reviews = load_dataset("McAuley-Lab/Amazon-Reviews-2023", "raw_review_Electronics", split="full", trust_remote_code=True)
meta = load_dataset("McAuley-Lab/Amazon-Reviews-2023", "raw_meta_Electronics", split="full", trust_remote_code=True)
reviews_df = pd.DataFrame(reviews)
meta_df = pd.DataFrame(meta)
# create simple CSVs:
products = meta_df[['parent_asin','title','description','price','brand']].rename(columns={'parent_asin':'asin'})
reviews_slim = reviews_df[['parent_asin','user_id','rating','text','timestamp']].rename(columns={'parent_asin':'asin','text':'review_text','timestamp':'unixReviewTime'})
products.to_csv("data/products.csv", index=False)
reviews_slim.to_csv("data/reviews.csv", index=False)
print("Wrote data/products.csv and data/reviews.csv")
