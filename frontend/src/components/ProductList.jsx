import React from "react";
import ProductCard from "./ProductCard.jsx";

export default function ProductList({ products = [], loading = false, onTrustClick }) {
  if (loading && (!products || products.length === 0)) {
    // show skeleton grid while loading first time
    return (
      <div className="grid-grid">
        {Array.from({ length: 8 }).map((_, i) => (
          <div className="card card-skeleton" key={i}>
            <div className="s-img" />
            <div className="s-line short" />
            <div className="s-line" />
            <div className="s-line tiny" />
          </div>
        ))}
      </div>
    );
  }

  if (!products || products.length === 0) {
    return <div className="empty-state">No results — try a different prompt or broaden the price range.</div>;
  }

  return (
    <div className="grid-grid">
      {products.map((p) => (
        <ProductCard
          key={p.asin}
          product={p}
          onTrust={() => (onTrustClick ? onTrustClick(p.asin) : undefined)}
        />
      ))}
    </div>
  );
}
