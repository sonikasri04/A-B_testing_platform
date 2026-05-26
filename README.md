# A/B Experimentation Platform

A full-stack A/B testing platform built with FastAPI + Streamlit — designed to statistically validate ML model performance in production.

Built to A/B test the [Content Recommender](https://github.com/sonikasri04/content_recommender) project — comparing a TF-IDF baseline vs a two-tower ML model on real click data.

## Live Demo
- **Dashboard**: [Streamlit App](https://a-b-testingplatform.streamlit.app/) ← update after deploy
- **API Docs**: [Swagger UI](https://a-b-testing-platform.onrender.com/docs)

---

## Architecture

```
Recommender Models          FastAPI Backend
(Control: TF-IDF       →   /experiments
 Treatment: Two-Tower)      /assign
                            /events
        ↓                   /results
   SQLite Store    ←────────────────────
        ↓
  Streamlit Dashboard
  (Create · Simulate · Analyze)
```

---

## ⚙️ Features

- **Deterministic user assignment** via MD5 hashing — same user always gets same variant, no DB lookup needed
- **Two-proportion z-test** with confidence intervals and effect size
- **Sequential testing** with actionable recommendations (ship / stop / keep running)
- **One-click simulation** — demo with 500–5000 synthetic users, no terminal needed
- **REST API** with full Swagger docs
- **Experiment lifecycle** — create, run, monitor, stop

---

## 📊 Sample Results

| Metric | Control (TF-IDF) | Treatment (Two-Tower) |
|--------|-----------------|----------------------|
| Conversion Rate | 11.0% | 17.3% |
| Relative Lift | — | +57% |
| p-value | — | < 0.0001 |
| Significant | — | ✅ Yes |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Uvicorn |
| Statistics | NumPy + SciPy (z-test, CI) |
| Database | SQLite |
| Dashboard | Streamlit + Plotly |
| Deployment | Render (API) + Streamlit Cloud (UI) |

---

** Run a demo**
- Go to **Create Experiment** tab → fill in name + metric → Create
- Go to **Live Results** → select experiment from dropdown
- Hit **▶ Run Simulation** → watch results populate live

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/experiments` | Create experiment |
| GET | `/experiments` | List all experiments |
| GET | `/experiments/{id}` | Get experiment details |
| POST | `/assign` | Assign user to variant |
| POST | `/events` | Log a conversion event |
| GET | `/results/{id}` | Get statistical results |
| POST | `/experiments/{id}/stop` | Stop experiment |

---

## Key Engineering Decisions

**Why MD5 hashing for assignment?**
Deterministic — the same user always lands in the same bucket without any DB lookup or session state. This is how Airbnb, Netflix, and Meta handle assignment at scale.

**Why z-test over t-test?**
For conversion rate metrics (binary outcomes), a two-proportion z-test is the correct choice. A t-test assumes continuous data.

**Why confidence intervals alongside p-values?**
p-values alone don't tell you the magnitude of the effect. The CI shows the plausible range of the true lift — critical for business decisions.

---

## Related Projects

- [Content Recommender](https://github.com/sonikasri04/content_recommender) — the ML model this platform was built to validate
- [Clickstream Analytics](https://github.com/sonikasri04/clickstream-analytics) — Kafka + Flink pipeline that feeds user event data

---

## 👩‍💻 Author

**Sonika Sri** · [GitHub](https://github.com/sonikasri04)
