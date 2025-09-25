import React, { useState, useEffect, useCallback } from "react";
import ProductList from "./components/ProductList.jsx";
import TrustModal from "./components/TrustModal.jsx";
import { sendLog } from "./utils/logger.js";

/** Backend base (update if needed) */
const BACKEND = "http://127.0.0.1:5000";

function useDebounced(value, ms = 400) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export default function App() {
  const [prompt, setPrompt] = useState("laptop");
  const debouncedPrompt = useDebounced(prompt, 450);

  const [priceImportance, setPriceImportance] = useState(30); // 0..100 (visual)
  const [priceRange, setPriceRange] = useState([0, 20000]); // actual rupee/dollar range display
  const [sortBy, setSortBy] = useState("score"); // score | price | reviews
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 12;

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [trustFor, setTrustFor] = useState(null);
  const [error, setError] = useState(null);

  // map slider percent to realistic price range (example: 0..10000)
  useEffect(() => {
    const maxPrice = 100000; // maximum considered price
    // Interpret priceImportance as "prefer lower price" where 100 => prefer cheapest.
    const center = Math.round((1 - priceImportance / 100) * (maxPrice * 0.6) + (maxPrice * 0.2));
    const span = Math.round((1 - priceImportance / 100) * (maxPrice * 0.4) + 500);
    const min = Math.max(0, Math.round(center - span / 2));
    const max = Math.min(maxPrice, Math.round(center + span / 2));
    setPriceRange([min, max]);
  }, [priceImportance]);

  useEffect(() => {
    sendLog("info", "App mounted", { prompt, priceImportance });
    // initial load
    fetchRecommendations().catch((e) => {
      // fetchRecommendations logs and sets error; swallow here
      console.error("[INIT FETCH ERR]", e);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchRecommendations = useCallback(
    async (opts = {}) => {
      setLoading(true);
      setError(null);
      const q = opts.prompt ?? debouncedPrompt ?? prompt;
      sendLog("info", "fetchRecommendations:start", { q, priceImportance, sortBy });
      try {
        // Build URL with query parameters
        const url = `${BACKEND}/api/recommend?prompt=${encodeURIComponent(q)}&slider=${priceImportance}`;
        const res = await fetch(url);
        if (!res.ok) {
          // try to read JSON or text for better error message
          const text = await res.text().catch(() => "");
          throw new Error(text || `Bad response: ${res.status}`);
        }

        const json = await res.json().catch(() => {
          throw new Error("Invalid JSON returned from /api/recommend");
        });

        // Ensure array
        const arr = Array.isArray(json) ? json : [];

        // normalize product fields and set fallback prices
        const normalized = arr.map((p, idx) => {
          const price = p?.price ?? p?.price_value ?? p?.pricing ?? null;
          const parsedPrice =
            typeof price === "number"
              ? price
              : price && typeof price === "string"
              ? Number(price.replace(/[^\d.]/g, "")) || null
              : null;
          const _price = parsedPrice ?? null; // no random fallback here — keep null if unknown
          return {
            asin: p?.asin ?? p?.ASIN ?? `ASINFALLBACK${idx}`,
            title: p?.title ?? p?.name ?? p?.summary ?? "Untitled product",
            score: Number(p?.score ?? p?.similarity ?? 0) || 0,
            reviews: Number(p?.reviews ?? p?.review_count ?? Math.round(Math.random() * 2000)) || 0,
            price: _price,
            image: p?.image ?? null,
            raw: p,
          };
        });

        // Frontend filter by priceRange — IMPORTANT: include items without price info
        const [minP, maxP] = priceRange;
        const filtered = normalized.filter((x) => {
          if (typeof x.price === "number" && !isNaN(x.price)) {
            return x.price >= minP && x.price <= maxP;
          }
          // If price is missing, include the item
          return true;
        });

        // sort
        const sorted = filtered.sort((a, b) => {
          if (sortBy === "price") {
            // items without price should go after priced items
            if (typeof a.price !== "number") return 1;
            if (typeof b.price !== "number") return -1;
            return a.price - b.price;
          }
          if (sortBy === "reviews") return b.reviews - a.reviews;
          return b.score - a.score;
        });

        setProducts(sorted);
        setPage(1);
        sendLog("success", "fetchRecommendations:done", { totalReceived: arr.length, afterFilter: sorted.length });
        console.log("[RECS]", { query: q, received: arr.length, shown: sorted.length });
      } catch (e) {
        console.error("[RECS ERROR]", e);
        setError(e.message || "Failed to load recommendations");
        sendLog("error", "fetchRecommendations:error", { message: e.message });
        setProducts([]);
      } finally {
        setLoading(false);
      }
    },
    [debouncedPrompt, priceImportance, priceRange, sortBy]
  );

  // when debounced prompt changes, auto fetch
  useEffect(() => {
    if (debouncedPrompt && debouncedPrompt.trim().length > 0) {
      fetchRecommendations({ prompt: debouncedPrompt }).catch((e) =>
        console.error("[AUTO FETCH ERR]", e)
      );
    }
  }, [debouncedPrompt, fetchRecommendations]);

  async function handleTrust(asin) {
    setTrustFor({ asin, loading: true, data: null });
    sendLog("info", "trust:request", { asin });
    try {
      const res = await fetch(`${BACKEND}/api/trust/${encodeURIComponent(asin)}`);
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(txt || `Bad response: ${res.status}`);
      }
      const j = await res.json().catch(() => ({ error: "Invalid JSON from /api/trust" }));
      setTrustFor({ asin, loading: false, data: j });
      sendLog("success", "trust:loaded", { asin });
      console.log("[TRUST DATA]", asin, j);
    } catch (e) {
      console.error("[TRUST ERROR]", e);
      setTrustFor({ asin, loading: false, data: { error: e.message } });
      sendLog("error", "trust:error", { asin, message: e.message });
    }
  }

  async function handleGenerateBundle() {
    sendLog("info", "bundle:request", { prompt: debouncedPrompt });
    try {
      const res = await fetch(`${BACKEND}/api/generate_bundle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: debouncedPrompt }),
      });

      // handle non-OK responses gracefully
      if (!res.ok) {
        // try parse JSON error body, else text
        const text = await res.text().catch(() => "");
        let parsed;
        try {
          parsed = JSON.parse(text);
        } catch {
          parsed = null;
        }
        const detail = parsed?.detail ?? parsed?.error ?? text ?? `HTTP ${res.status}`;
        throw new Error(detail);
      }

      const j = await res.json().catch(() => {
        throw new Error("Invalid JSON from /api/generate_bundle");
      });

      sendLog("success", "bundle:done", { j });
      console.log("[BUNDLE]", j);
      alert("Bundle generated (check console / backend).");
    } catch (e) {
      sendLog("error", "bundle:error", { message: e.message });
      alert("Bundle failed: " + e.message);
    }
  }

  // Pagination helpers
  const totalPages = Math.max(1, Math.ceil(products.length / PAGE_SIZE));
  const shown = products.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="brand">
          <div className="logo">AR</div>
          <div>
            <h1>Amazon Recs — Demo</h1>
            <div className="subtitle">Prompt-driven recommendations & trust</div>
          </div>
        </div>

        <div className="controls">
          <div className="search-row">
            <input
              aria-label="search prompt"
              className="search-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Type prompt (e.g. 'thin laptop under 50k')"
            />

            <button className="primary" onClick={() => fetchRecommendations({ prompt })} disabled={loading}>
              {loading ? "Searching…" : "Search"}
            </button>

            <button className="ghost" onClick={handleGenerateBundle}>
              Generate bundle
            </button>
          </div>

          <div className="filters-row">
            <label className="slider-label">
              Price importance
              <input
                type="range"
                min="0"
                max="100"
                value={priceImportance}
                onChange={(e) => setPriceImportance(Number(e.target.value))}
              />
            </label>

            <div className="price-display">
              Showing price window: <b>₹{Math.round(priceRange[0])}</b> — <b>₹{Math.round(priceRange[1])}</b>
            </div>

            <label>
              Sort
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="score">Best match</option>
                <option value="price">Price (low → high)</option>
                <option value="reviews">Top reviews</option>
              </select>
            </label>
          </div>
        </div>
      </header>

      <main className="main-area">
        <div className="summary-row">
          <div>{loading ? "Searching recommendations…" : `Showing ${products.length} results`}</div>
          {error && <div className="error-pill">Error: {error}</div>}
        </div>

        <ProductList products={shown} loading={loading} onTrustClick={handleTrust} />

        <div className="pager">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
            ← Prev
          </button>
          <div>
            Page <b>{page}</b> of <b>{totalPages}</b>
          </div>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
            Next →
          </button>
        </div>
      </main>

      <footer className="footer">
        <div>Built by Amritanshu — demo UI</div>
        <div className="small-muted">Tip: Click Trust for product-level analysis</div>
      </footer>

      {trustFor && <TrustModal asin={trustFor.asin} loading={trustFor.loading} data={trustFor.data} onClose={() => setTrustFor(null)} />}
    </div>
  );
}
