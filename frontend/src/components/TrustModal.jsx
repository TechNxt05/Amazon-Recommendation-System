import React from "react";

export default function TrustModal({ asin, loading, data, onClose }) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <div className="modal-head">
          <div>
            <h3>Trust insights</h3>
            <div className="muted">ASIN: {asin}</div>
          </div>
          <button className="close-x" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {loading && <div className="muted">Loading trust data…</div>}

          {!loading && !data && <div className="muted">No data available.</div>}

          {!loading && data && (
            <>
              {data.error && <div className="error-pill">Error: {data.error}</div>}
              {data.trust_score !== undefined && (
                <div className="trust-score">
                  <div className="label">Trust score</div>
                  <div className="value">{data.trust_score}</div>
                </div>
              )}

              {data.explanations && Array.isArray(data.explanations) && (
                <div>
                  <div className="label">Highlights</div>
                  <ul>
                    {data.explanations.slice(0, 8).map((x, i) => <li key={i}>{x}</li>)}
                  </ul>
                </div>
              )}

              <details className="raw-details">
                <summary>Raw data</summary>
                <pre>{JSON.stringify(data, null, 2)}</pre>
              </details>
            </>
          )}
        </div>

        <div className="modal-actions">
          <button className="btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
