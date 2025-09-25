import React from "react";

/** small currency formatter; adjust to your locale */
const fmtPrice = (p) => {
  try {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(p);
  } catch {
    return "₹" + Math.round(p);
  }
};

function PlaceholderImage() {
  return (
    <svg viewBox="0 0 200 140" className="placeholder-svg" xmlns="http://www.w3.org/2000/svg">
      <rect width="200" height="140" rx="8" fill="#f3f4f6" />
      <g transform="translate(32,20)" fill="#e5e7eb">
        <rect x="0" y="0" width="136" height="86" rx="6" />
      </g>
    </svg>
  );
}

export default function ProductCard({ product, onTrust }) {
  const { title, score, reviews, asin, price, image } = product;
  return (
    <article className="card">
      <div className="card-top">
        <div className="img-wrap">
          {image ? <img src={image} alt={title} /> : <PlaceholderImage />}
        </div>

        <div className="meta">
          <div className="title">{title}</div>
          <div className="badges">
            <span className="badge price">{fmtPrice(price)}</span>
            <span className="badge score">★ {Number(score).toFixed(3)}</span>
            <span className="badge reviews">🗨 {Number(reviews).toLocaleString()}</span>
          </div>
          <div className="asin">ASIN: <span>{asin}</span></div>
        </div>
      </div>

      <div className="card-actions">
        <button className="btn-primary" onClick={onTrust}>Trust</button>
        <button
          className="btn-ghost"
          onClick={() => {
            // quick log action
            console.log("[CARD] open product", asin, title);
          }}
        >
          Details
        </button>
      </div>
    </article>
  );
}
