# generate_synthetic_fake_reviews.py
# Create a tiny synthetic dataset for fake-review finetuning demo.
import csv
import random

real_templates = [
    "I used this product for a month and it works well. Good value.",
    "Decent build, battery life is average. Recommended for the price.",
    "Not as expected, had some issues with connectivity.",
    "Good sound, comfortable. Bought it for commuting."
]

fake_templates = [
    "BEST EVER!!! MUST BUY 100% recommended",
    "Amazing product buy now buy now BUY NOW!!!!",
    "Paid review, five stars. Buy from seller.",
    "Excellent excellent excellent! five stars"
]

def gen_csv(outfile, n_real=300, n_fake=100):
    rows = []
    for i in range(n_real):
        rows.append({"text": random.choice(real_templates), "label": 0})
    for i in range(n_fake):
        rows.append({"text": random.choice(fake_templates), "label": 1})
    random.shuffle(rows)
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text","label"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print("Wrote", outfile)

if __name__ == "__main__":
    gen_csv("../data/fake_reviews_train.csv", n_real=300, n_fake=100)
    gen_csv("../data/fake_reviews_val.csv", n_real=80, n_fake=20)
