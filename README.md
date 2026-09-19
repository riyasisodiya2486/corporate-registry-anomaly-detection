# AI-Based Corporate Registry Anomaly Detection

An open, reproducible pipeline that flags structurally unusual company clusters in India's public corporate registry data — for human review, not automated verdicts.

---

## Overview

India's Ministry of Corporate Affairs (MCA) registry records over 28 lakh companies as independent legal entities, but provides no built-in way to see when many "separate" companies are actually structurally connected — through shared registered addresses, near-identical names, or unusual registration timing. Existing tools capable of this kind of analysis (Prophecy Eagle I, Innefu Labs, Accumn) are closed, proprietary, and accessible only to government or enterprise users.

This project builds an **open, reproducible AI pipeline** that ingests public MCA bulk data, resolves inconsistent records through entity resolution, builds a company relationship graph, and uses unsupervised machine learning to score clusters for structural anomaly — surfacing them as **investigation leads for human review**, not fraud verdicts.

## What this project does NOT claim

- It does **not** detect fraud. It flags statistical outliers.
- Company status (e.g., "Struck Off") is treated as a weak, non-definitive signal — never as ground truth.
- Every flagged cluster comes with an explanation (via SHAP), not just a bare score.

---

## Key Features

- **Entity Resolution** — blocking + fuzzy matching (Jaro-Winkler, Levenshtein) to link inconsistently-formatted company records
- **Graph-Based Clustering** — company relationship graph via NetworkX
- **Multi-Signal Anomaly Scoring** — 7 structural signals (address density, name pattern, registration timing, capital similarity, graph topology, cross-cluster bridges, category homogeneity) scored via Isolation Forest
- **Explainable Results** — SHAP values show exactly which signals drove each cluster's score
- **Tamper-Evident Audit Trail** — a hash-chained, blockchain-inspired integrity layer over both the source data and every review action
- **Open Web Interface** — search a company, view its cluster, see the score and the reasoning behind it

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Database | PostgreSQL (via Docker) |
| Entity Resolution | `recordlinkage`, `jellyfish` |
| Graph Analytics | `NetworkX` |
| Machine Learning | `scikit-learn` (Isolation Forest) |
| Explainability | `SHAP` |
| Web Interface | `Streamlit` |
| Containerization | Docker & Docker Compose |
| Version Control | Git & GitHub |

---

## Project Structure

```
corporate-registry-anomaly-detection/
├── docs/                   # scope, data quality notes, interface contract, related work
├── data/
│   ├── raw/                # downloaded CSVs (git-ignored — see Data Source below)
│   └── processed/
├── src/
│   ├── config.py           # shared constants
│   ├── ingestion/          # bulk data loading — Yashika
│   ├── cleaning/           # normalization, pincode extraction — Yashika
│   ├── blocking/           # candidate pair generation — Yashika
│   ├── integrity/          # hash-chain audit layer — Yashika
│   ├── matching/           # fuzzy similarity scoring — Riya
│   ├── graph/              # cluster construction — Riya
│   └── scoring/            # feature extraction, Isolation Forest, SHAP — Riya
├── app/                    # Streamlit web interface — Riya
├── notebooks/              # exploration and analysis
├── results/                # experiment outputs, figures, tables
├── docker-compose.yml
├── requirements.txt
└── README.md
```

See `docs/interface_contract.md` for the exact schema, function signatures, and full team responsibility breakdown.

---

## Data Source

This project uses the **MCA Company Master Data**, published as open government data on [data.gov.in](https://www.data.gov.in), broken down by Registrar of Companies (ROC) jurisdiction. It is free, requires no login, and is updated periodically by the Ministry of Corporate Affairs, Government of India.

Raw data files are **not committed to this repository** (see `.gitignore`) — they're large and freely re-downloadable. See `docs/scope.md` for the exact jurisdiction used and the download date, so the dataset is reproducible.

---

## Getting Started

### Prerequisites
- Python 3.11 or 3.12
- Docker Desktop
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/corporate-registry-anomaly-detection.git
   cd corporate-registry-anomaly-detection
   ```

2. **Start the database**
   ```bash
   docker compose up -d
   ```

3. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Download the dataset**
   Follow the instructions in `docs/scope.md` to download the relevant ROC jurisdiction's CSV from data.gov.in into `data/raw/`.

5. **Run the pipeline**
   ```bash
   python src/ingestion/load_raw.py
   python src/cleaning/run_cleaning.py
   # blocking, matching, graph, and scoring steps follow — see docs/interface_contract.md
   ```

6. **Launch the web interface**
   ```bash
   streamlit run app/main.py
   ```

---

## Team & Roles

| Member | Track | Responsibilities |
|---|---|---|
| **Yashika Hidau** | Data & Infrastructure | Ingestion, cleaning/normalization, database schema, blocking, hash-chain integrity layer, cloud deployment |
| **Riya Sisodiya** | Intelligence & Application | Fuzzy matching, graph construction, structural feature engineering, Isolation Forest scoring, SHAP explainability, web interface |

Full task-by-task ownership is defined in `docs/interface_contract.md`, Section 0.

---

## Methodology (summary)

```
Ingest → Clean & Normalize → Block & Match → Graph & Score → Human Review
```

1. **Ingest** — load bulk registry CSV into a PostgreSQL staging table
2. **Clean & Normalize** — standardize addresses/names, extract pincodes
3. **Block & Match** — reduce comparison space, score candidate pairs via fuzzy matching
4. **Graph & Score** — build company relationship graph, score clusters via Isolation Forest across 7 structural signals
5. **Human Review** — ranked, explainable clusters presented via the web interface for manual audit

---

## Limitations

- **Company status is a noisy proxy, not a fraud label** — correlation with "Struck Off" status is reported as a weak, directional signal only
- **Scoped to a single jurisdiction** for feasibility — not a national-scale claim (see `docs/scope.md`)
- **Director-level ownership data** is not confirmed as freely bulk-accessible and is treated as future work, not a core dependency
- **Shared professional-service addresses** (e.g., a CA firm serving many clients) can resemble genuine anomalies — the scoring accounts for this, but it remains an inherent challenge in address-based signals
- **Determined, deliberately-evasive actors** who avoid shared addresses/names entirely may not be caught — this system is designed to catch common, low-effort patterns, not sophisticated evasion

---

## Related Work

- Fellegi, I. & Sunter, A. — foundational theory of record linkage
- CoDS-COMAD (2018) — shell-company account detection via anomaly detection
- "Who Sits Where? Automated Detection of Director Interlocks in Indian Companies" (2026)
- Commercial platforms: Prophecy Eagle I, Innefu Labs, Accumn (closed-source, not directly comparable)

See `docs/related_work_notes_yashika.md` and `docs/related_work_notes_riya.md` for detailed notes.

---

## License

*(To be decided — recommend an open license such as MIT once the project is ready to be made public, consistent with the "open, reproducible" goal of this work.)*

---

## Acknowledgments

Built as a final-year B.Tech project, Computer Science & Information Technology, Symbiosis University of Applied Sciences.
