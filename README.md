# Ethos: Campus Entity Resolution & Security Monitoring System

## Challenge Overview

Modern campuses generate vast, diverse data—swipes, Wi-Fi logs, library checkouts, helpdesk notes, bookings, CCTV images—but these remain siloed. Security and operations teams need a privacy-aware, explainable system to unify records, resolve identities, and deliver actionable insights.

**Ethos** is a Cross-Source Entity Resolution and Security Monitoring System that links identifiers, reconstructs activity histories, predicts missing data, and proactively alerts anomalies via an interactive dashboard.

---

## Features

- **Entity Resolution:** Match students, staff, devices, and assets across multiple identifiers and datasets.
- **Cross-Source Linking:** Integrate structured data, text notes, and visual inputs.
- **Multi-Modal Fusion:** Unify records with provenance and confidence scoring.
- **Timeline Generation:** Build and summarize chronological activity histories.
- **Predictive Monitoring:** ML-based inference for missing/ambiguous data, with explainability.
- **Security Dashboard:** Dropdown-based queries, complete daily histories, and alerting for inactivity.

---

## Folder Structure

```
data/           # Sample/synthetic data
src/            # Source code (entity resolution, fusion, timeline, monitoring, UI)
models/         # ML model & encoder files
report/         # Technical report (10 pages)
demo/           # 3–5 min video walkthrough
```

---

## Setup & Usage

1. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Run the dashboard:**
    ```bash
    streamlit run src/app.py
    ```

3. **Sample Queries:**
    - Track a student or asset’s daily activity.
    - Predict current location given incomplete data.
    - Visualize timeline and receive inactivity alerts.

---

## Demo

See the `demo/demo_video.mp4` for a walkthrough of queries, timeline generation, predictive inference, and UI.

---

## Technical Report

See `report/Ethos_Report.pdf` for detailed documentation on system architecture, algorithms, fusion, explainability, performance, and privacy.
