# Web Application Wireframe Outline

## Page 1: Search & Filtering
- Search box for Company Name / CIN.
- Jurisdiction filter (e.g., ROC Pune).
- Filter by anomaly score range.

## Page 2: Cluster Detail View
- Graph visualization of the connected cluster (NetworkX rendering).
- List of companies sharing the address/name pattern.
- Breakdown of the 7 anomaly signals.
- SHAP reasoning plot explaining *why* this cluster was flagged.

## Page 3: Leaderboard / Lead List
- Ranked table of top anomalous clusters (highest anomaly scores first).
- Quick flags (e.g., high address density, rapid incorporation window).
- Status review buttons for manual audit tracking.