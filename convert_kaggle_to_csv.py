import pandas as pd
import hashlib
import random
import time

# Load Kaggle dataset (update filename if different)
df = pd.read_csv("data/electronics_small.csv")  # replace with your actual file name

# Generate synthetic asin (product_id) using hash of summary
def make_asin(text):
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()[:10]

df["asin"] = df["summary"].apply(make_asin)

# Generate synthetic user_id
df["user_id"] = ["user_" + str(i) for i in range(len(df))]

# Convert reviewTime string to unix timestamp
def to_unix(rt):
    try:
        return int(time.mktime(time.strptime(str(rt), "%m %d, %Y")))
    except:
        return None

df["unixReviewTime"] = df["reviewTime"].apply(to_unix)

# ---- Create reviews.csv ----
reviews = df[["asin","user_id","overall","reviewText","unixReviewTime"]].copy()
reviews.insert(0,"review_id", range(1, len(reviews)+1))
reviews.rename(columns={"overall":"rating","reviewText":"review_text"}, inplace=True)
reviews.to_csv("data/reviews.csv", index=False)
print("Wrote data/reviews.csv")

# ---- Create products.csv ----
products = df.groupby("asin").agg({
    "summary":"first",
    "reviewText":"first"
}).reset_index()
products["price"] = [random.randint(500,5000) for _ in range(len(products))]
products["brand"] = "Unknown"
products["categories"] = "Electronics"
products.rename(columns={"summary":"title","reviewText":"description"}, inplace=True)
products.to_csv("data/products.csv", index=False)
print("Wrote data/products.csv")
