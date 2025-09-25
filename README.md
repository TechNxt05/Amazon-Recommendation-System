# Amazon Product Recommendation & Reviews Analysis

An **end-to-end product recommendation system** built with **React.js (frontend)** and **Flask (backend)**, powered by **FAISS embeddings, Gemini API**, and the **Amazon Reviews 2018 dataset**.  
The system provides **prompt-driven product recommendations, price–review tradeoff scoring, and trust analysis** with an interactive UI.

---

## 🔹 What Makes This Project Unique

Unlike generic recommenders or review dashboards, this system integrates **several unique tweaks and innovations**:

1. **Prompt-driven Recommendations (NLP + Embeddings)**  
   - Search via natural language prompts (e.g., *“thin laptop under 50k with good battery life”*).  
   - Uses **FAISS vector embeddings** for semantic product retrieval, unlike traditional keyword or collaborative filtering.

2. **Price–Review Tradeoff Scoring (Custom Scalar)**  
   - A **slider** allows users to tune how much price influences results.  
   - Backend computes a **hybrid scalar score** combining embedding similarity, normalized price, and review scores.

3. **Trust Analysis Layer (Review Heuristics + ML hooks)**  
   - Calculates product **trust scores** from review text length, helpful votes, and rating distribution.  
   - Fallback heuristics ensure reliability even if ML models are unavailable.

4. **Interactive Explainability (UI/UX innovation)**  
   - Each product has a **“Trust” modal** showing: trust score, heuristics, and explanations.  
   - Adds **transparency** to recommendations, unlike black-box recsys.

5. **Bundle Generation via Gemini API (Generative Twist)**  
   - Produces **bundles of complementary products** (e.g., laptop + backpack + mouse).  
   - Moves beyond flat recommendations into **creative, generative suggestions**.

6. **Integration with Amazon Reviews 2018 Dataset**  
   - Combines system building with **large-scale review analysis (100M+ reviews)**.  
   - Links to deeper dataset exploration in a [separate repo](https://github.com/TechNxt05/amazon-reviews-2018-analysis).

7. **Full-Stack Implementation**  
   - **React.js frontend** with filters, pagination, and sliders.  
   - **Flask backend** exposing `/recommend`, `/trust`, `/generate_bundle`, and `/log` APIs.  
   - Clean modular separation for real-world deployment.

---

## ✨ Features
- Prompt-driven semantic search with FAISS  
- Slider-based price–quality tradeoff tuning  
- Trust scoring with heuristics and optional ML models  
- Generative bundle creation using Gemini API  
- Explainable UI with interactive trust modals  
- Large-scale Amazon Reviews dataset insights  

---

## 🏗️ Tech Stack
**Frontend:** React.js, JavaScript, CSS  
**Backend:** Flask, Python, FAISS, pandas  
**ML/AI:** Gemini API, Embeddings, Trust Scoring  
**Dataset:** Amazon Reviews 2018 (100M+ reviews)

---

## 📂 Project Structure
```
.
├── frontend/               # React.js client (UI)
│   ├── src/                # Components, utils, styles
│   ├── package.json
│   └── ...
├── backend/                # Flask server
│   ├── app.py              # Main API
│   ├── recommender.py      # FAISS-based recommendations
│   ├── trust.py            # Trust score heuristics/ML
│   ├── gemini_client.py    # Gemini API integration
│   ├── data/               # CSVs, review samples
│   └── models/             # FAISS index, product metadata
├── README.md
└── .gitignore
```

---

## 🚀 Getting Started

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/TechNxt05/Amazon-Recommendation-System
cd amazon-recs-review-analysis
```

### 2️⃣ Setup Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py
```

Backend runs on: **http://127.0.0.1:5000**

### 3️⃣ Setup Frontend
```bash
cd frontend
npm install
npm start
```

Frontend runs on: **http://localhost:3001**

---

## 📊 Dataset
We used insights from the **Amazon Reviews 2018 dataset**.  
For more detailed dataset-level analysis, see the separate repo here:  
👉 [Amazon Reviews 2018 — Dataset-level Analysis](https://github.com/TechNxt05/Amazon-Review-Analysis-2018)

---

## 📌 Future Work
- Deploy on AWS (EC2 + S3 + RDS)  
- Enhance trust scoring with Transformer-based sentiment models  
- Add visualization dashboard for dataset insights  

---

## 👨‍💻 Author
**Amritanshu Yadav**  
- [Portfolio](https://technxt05.github.io/Portfolio-Website/)  
- [GitHub](https://github.com/TechNxt05)  
- [LinkedIn](https://www.linkedin.com/in/amritanshu-yadav-6480662a8/)
