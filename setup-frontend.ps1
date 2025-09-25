$frontendPath = "frontend"
$srcPath = Join-Path $frontendPath "src"
$componentsPath = Join-Path $srcPath "components"

# Create folders
New-Item -ItemType Directory -Force -Path $frontendPath | Out-Null
New-Item -ItemType Directory -Force -Path $srcPath | Out-Null
New-Item -ItemType Directory -Force -Path $componentsPath | Out-Null

# package.json
@'
{
  "name": "amazon-recs-frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@babel/core": "^7.22.0",
    "parcel": "^2.9.3"
  },
  "scripts": {
    "start": "parcel src/index.html --port 3000 --open",
    "build": "parcel build src/index.html --public-url ./"
  }
}
'@ | Out-File -Encoding UTF8 (Join-Path $frontendPath "package.json")

# index.html
@'
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Amazon Recs Demo</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="./index.jsx"></script>
  </body>
</html>
'@ | Out-File -Encoding UTF8 (Join-Path $srcPath "index.html")

# index.jsx
@'
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

import "./styles.css";

const container = document.getElementById("root");
const root = createRoot(container);
root.render(<App />);
'@ | Out-File -Encoding UTF8 (Join-Path $srcPath "index.jsx")

# styles.css
@'
:root{
  --bg:#f3f4f6;
  --card:#fff;
  --accent:#2563eb;
  --muted:#6b7280;
}
body{margin:0;font-family:Inter,Roboto,Arial,sans-serif;background:var(--bg);color:#111827;}
.app{max-width:1100px;margin:28px auto;padding:18px;}
.header{display:flex;gap:16px;align-items:center;justify-content:space-between;margin-bottom:18px;}
.brand{font-weight:700;font-size:20px;}
.controls{display:flex;gap:8px;align-items:center;}
.control-row{display:flex;gap:8px;align-items:center;}
input[type="text"]{padding:8px 12px;border-radius:8px;border:1px solid #e5e7eb;min-width:360px;}
button{padding:8px 12px;border-radius:8px;border:0;background:var(--accent);color:white;cursor:pointer;}
.slider{display:flex;gap:8px;align-items:center;}
.products{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-top:18px;}
.card{background:var(--card);padding:12px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,0.06);}
.title{font-weight:600;margin-bottom:6px;}
.meta{font-size:13px;color:var(--muted);margin-bottom:8px;}
.score{display:inline-block;padding:4px 8px;border-radius:6px;background:#eef2ff;color:#1e3a8a;font-weight:600;margin-right:8px;}
.small{font-size:13px;color:var(--muted);}
.trust-details{margin-top:8px;font-size:13px;color:var(--muted);background:#f8fafc;padding:8px;border-radius:6px;}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;}
.modal{width:90%;max-width:720px;background:white;border-radius:12px;padding:16px;}
.evidence{margin-top:8px;padding:8px;background:#f8fafc;border-radius:6px;}
pre{white-space:pre-wrap;word-wrap:break-word;}
'@ | Out-File -Encoding UTF8 (Join-Path $srcPath "styles.css")

# App.jsx
@'
import React, { useState } from "react";
import ProductList from "./components/ProductList";
import TrustModal from "./components/TrustModal";

const BACKEND = "http://127.0.0.1:5000";

export default function App() {
  const [prompt, setPrompt] = useState("laptop");
  const [slider, setSlider] = useState(30);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [trustFor, setTrustFor] = useState(null);

  async function fetchRecommendations() {
    setLoading(true);
    try {
      const url = `${BACKEND}/api/recommend?prompt=${encodeURIComponent(prompt)}&slider=${slider}`;
      const res = await fetch(url);
      const json = await res.json();
      setProducts(json);
    } catch (e) { alert("Failed: " + e.message); }
    setLoading(false);
  }

  async function handleTrust(asin) {
    setTrustFor({ asin, loading: true, data: null });
    try {
      const res = await fetch(`${BACKEND}/api/trust/${encodeURIComponent(asin)}`);
      const data = await res.json();
      setTrustFor({ asin, loading: false, data });
    } catch (e) { setTrustFor({ asin, loading: false, data: { error: e.message } }); }
  }

  async function handleGenerateBundle() {
    try {
      const res = await fetch(`${BACKEND}/api/generate_bundle`, {
        method:"POST", headers:{ "Content-Type":"application/json" },
        body: JSON.stringify({prompt})
      });
      const j = await res.json();
      alert("Bundle generated. Check console.");
      console.log(j);
    } catch(e){ alert("Bundle failed: "+e.message); }
  }

  return (
    <div className="app">
      <div className="header">
        <div><div className="brand">Amazon Recs — Demo</div><div className="small">Prompt-driven recs + trust</div></div>
        <div className="controls">
          <div className="control-row">
            <input value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Search prompt"/>
            <div className="slider">
              <label className="small">Price importance</label>
              <input type="range" min="0" max="100" value={slider} onChange={e=>setSlider(Number(e.target.value))}/>
            </div>
            <button onClick={fetchRecommendations}>{loading ? "Loading…" : "Search"}</button>
            <button onClick={handleGenerateBundle} style={{background:"#10b981"}}>Generate bundle</button>
          </div>
        </div>
      </div>
      <ProductList products={products} onTrustClick={handleTrust}/>
      {trustFor && <TrustModal asin={trustFor.asin} loading={trustFor.loading} data={trustFor.data} onClose={()=>setTrustFor(null)}/>}
    </div>
  );
}
'@ | Out-File -Encoding UTF8 (Join-Path $srcPath "App.jsx")

# ProductList.jsx
@'
import React from "react";
import ProductCard from "./ProductCard";

export default function ProductList({ products, onTrustClick }) {
  if (!products?.length) return <div>No recommendations yet.</div>;
  return <div className="products">{products.map(p=><ProductCard key={p.asin} product={p} onTrustClick={onTrustClick}/>)}</div>;
}
'@ | Out-File -Encoding UTF8 (Join-Path $componentsPath "ProductList.jsx")

# ProductCard.jsx
@'
import React from "react";

export default function ProductCard({ product, onTrustClick }) {
  const { title, asin, price, score } = product;
  return (
    <div className="card">
      <div className="title">{title}</div>
      <div className="meta"><span className="score">{(score||0).toFixed(3)}</span><span className="small">₹{price}</span></div>
      <div className="small">ASIN: {asin}</div>
      <div style={{display:"flex",gap:8,marginTop:8}}>
        <button onClick={()=>onTrustClick(asin)}>Trust</button>
      </div>
    </div>
  );
}
'@ | Out-File -Encoding UTF8 (Join-Path $componentsPath "ProductCard.jsx")

# TrustModal.jsx
@'
import React from "react";

export default function TrustModal({ asin, loading, data, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e=>e.stopPropagation()}>
        <h3>Trust — {asin}</h3>
        {loading && <div>Loading trust info…</div>}
        {!loading && data && (
          <div>
            <div><strong>Model:</strong> {data.model} | <strong>Score:</strong> {data.score}</div>
            <div className="trust-details">
              <div><b>Rationale:</b> {data.rationale}</div>
              <div><b>Evidence:</b></div>
              {Array.isArray(data.evidence) && data.evidence.length>0 ? data.evidence.map((ev,i)=><div key={i} className="evidence"><pre>{JSON.stringify(ev,null,2)}</pre></div>) : "No evidence"}
            </div>
          </div>
        )}
        <button onClick={onClose} style={{background:"#ef4444",marginTop:10}}>Close</button>
      </div>
    </div>
  );
}
'@ | Out-File -Encoding UTF8 (Join-Path $componentsPath "TrustModal.jsx")

Write-Host "✅ Frontend scaffold created. Next steps:"
Write-Host "1) cd frontend"
Write-Host "2) npm install"
Write-Host "3) npm start"
