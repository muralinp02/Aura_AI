# Aura-AI

> **AI-powered web security testing & continuous defense**
> Automates vulnerability discovery, risk prioritization, and remediation insights—backed by real-time monitoring and intuitive dashboards.

[![CI](https://img.shields.io/badge/build-passing-brightgreen)](#) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](#license) [![Stack](https://img.shields.io/badge/stack-React%20%7C%20Vite%20%7C%20FastAPI%20%7C%20Firebase-informational)](#tech-stack)

---

## Table of Contents

* [Overview](#overview)
* [Core Capabilities](#core-capabilities)
* [Architecture](#architecture)
* [Tech Stack](#tech-stack)
* [Project Structure](#project-structure)
* [Quick Start](#quick-start)
* [Setup & Configuration](#setup--configuration)

  * [Frontend (.env)](#frontend-env)
  * [Backend (.env)](#backend-env)
* [Run Locally](#run-locally)
* [Deployment](#deployment)
* [Usage Walkthrough](#usage-walkthrough)
* [API (Backend)](#api-backend)
* [Security & Ethics](#security--ethics)
* [Troubleshooting](#troubleshooting)
* [Scripts](#scripts)
* [Contributing](#contributing)
* [License](#license)
* [Acknowledgments](#acknowledgments)
* [Maintainers](#maintainers)

---

## Overview

Aura-AI is an end-to-end cybersecurity platform for web applications. It combines classical security scanning with ML-assisted analytics to surface actionable insights, visualize attack paths, and push alerts—so you can move from “finding issues” to “fixing risks” quickly.

---

## Core Capabilities

* **Vulnerability Scanning**

  * Detects **SQLi, XSS, CSRF, open redirects, weak headers**, and common misconfigs
  * Quick / Full / Custom scans with tunable depth & scope

* **Network & Attack-Path Visualization**

  * Real-time graph of hosts, services, and edges
  * Highlights **critical choke points** and **probable lateral paths**

* **Monitoring & Alerts**

  * Continuous watch on critical assets
  * Push notifications (Firebase) for new high-risk findings

* **Reporting**

  * Executive & technical **PDF** reports with remediation guidance
  * Trends, MTTR, severity distributions

* **Dashboard Analytics**

  * KPIs, historical trends, and filterable findings

* **Auth & Roles**

  * Firebase Authentication (email/password, providers)
  * Guarded routes and basic RBAC patterns

---

## Architecture

```
┌─────────────┐        HTTPS        ┌───────────────┐
│  Frontend   │  <----------------> │   FastAPI     │
│ React+Vite  │                     │  Backend API  │
└──────┬──────┘                     └───────┬───────┘
       │                                    │
       │                                   Tasks: Crawl, Preprocess,
       │                                   Model Inference, Graph Build,
       │                                   Scan Orchestration, Report Gen
       │
┌──────▼──────┐                     ┌────────▼─────────┐
│  Firebase   │ <------------------>│  Firestore/Store │
│  Auth       │     Findings+Meta   │  (optional)      │
└─────────────┘                     └──────────────────┘
```

* Visualization: **Recharts**, **vis-network**
* Alerts: backend → **Firebase** (push/notification pipeline)
* CORS: restricted to configured origins

---

## Tech Stack

**Frontend**

* React, TypeScript, Vite
* shadcn-ui, Tailwind CSS, Lucide-react
* TanStack Query, React Context API
* Recharts, vis-network
* jsPDF, jsPDF-autotable

**Backend**

* FastAPI, Uvicorn
* (Optional) scikit-learn / lightweight DL for risk models
* Custom modules: `crawling`, `preprocessing`, `prediction`, `network_analysis`, `firebase_sync`

---

## Project Structure

```
Aura-AI/
├── backend/
│   ├── main.py                 # FastAPI entrypoint
│   ├── crawling.py             # Target discovery & fetch
│   ├── preprocessing.py        # Data cleaning/normalization
│   ├── prediction.py           # Model load/infer
│   ├── network_analysis.py     # Graph build & attack paths
│   ├── firebase_sync.py        # Push alerts to Firebase
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── styles/
│       ├── firebase/           # firebase.ts lives here
│       ├── contexts/
│       │   └── ScanContext.tsx
│       ├── components/
│       │   ├── layout/
│       │   ├── scanner/
│       │   ├── reports/
│       │   └── ui/
│       └── pages/
├── README.md
└── LICENSE
```

---

## Quick Start

```bash
# 1) Clone
git clone <your-repo-url>
cd Aura-AI

# 2) Frontend deps
cd frontend
npm install

# 3) Backend deps
cd ../backend
python -m venv .venv && source .venv/bin/activate   # (Windows) .venv\Scripts\activate
pip install -r requirements.txt
```

Create the env files as shown below, then run both servers.

---

## Setup & Configuration

### Frontend (.env)

Create `frontend/.env`:

```env
# Firebase
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project
VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=xxxxxxxxxxxx
VITE_FIREBASE_APP_ID=1:xxxxxxxxxxxx:web:xxxxxxxxxxxxxxxx
VITE_FIREBASE_MEASUREMENT_ID=G-XXXXXXXXXX   # optional

# Backend API base (local dev)
VITE_API_BASE=http://127.0.0.1:8000
```

Create `frontend/src/firebase/firebase.ts`:

```ts
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

> **Note:** Ensure **only one** `VITE_API_BASE` line exists—duplicate lines can silently override.

### Backend (.env)

Create `backend/.env`:

```env
# Comma-separated origins; include your Netlify domain for prod
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,https://<your-netlify-site>.netlify.app

# Optional: Firebase service account (if backend needs to push alerts)
# Provide a file path or JSON string
GOOGLE_APPLICATION_CREDENTIALS=/abs/path/to/service-account.json

# App
APP_HOST=127.0.0.1
APP_PORT=8000
```

In `backend/main.py`, ensure CORS uses `CORS_ORIGINS` and **Uvicorn** runs on **8000** to match the frontend:

```py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["*"],
    max_age=600,
)
```

---

## Run Locally

**Backend**

```bash
cd backend
source .venv/bin/activate        # (Windows) .venv\Scripts\activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend**

```bash
cd frontend
npm run dev
# Vite typically serves at http://127.0.0.1:5173
```

---

## Deployment

### Frontend (Netlify)

* **Build command:** `npm run build`
* **Publish directory:** `dist`
* **Env vars:** copy your `.env` values as Netlify environment variables (prefixed with `VITE_`).
* **VITE_API_BASE:** set to your backend’s public URL (e.g., Render).

### Backend (Render / Railway / VPS)

* **Start command:** `uvicorn main:app --host 0.0.0.0 --port 8000`
* **Env vars:** `CORS_ORIGINS` must include your frontend’s deployed URL (e.g., `https://<site>.netlify.app`).
* If using Firebase server SDKs, configure `GOOGLE_APPLICATION_CREDENTIALS` appropriately.

---

## Usage Walkthrough

1. **Sign In / Sign Up**
   Authenticate via Firebase. Protected routes require a valid session.

2. **Dashboard**
   View findings, risk trends, top affected assets, open vs resolved items.

3. **Scanner**

   * Choose **Quick / Full / Custom**
   * Enter target base URL(s), depth, include/exclude paths
   * Launch and watch progress

4. **Network**
   Explore service graph, highlight high-betweenness nodes, suspected attack paths.

5. **Reports**
   Export PDF with executive summary and technical details.

6. **Monitoring**
   Enable continuous watch for critical domains; receive alerts on new high-risk items.

---

## API (Backend)

**Base URL:** `http://127.0.0.1:8000`

Examples (subject to your implementation):

* `POST /scan/start`

  ```json
  { "targets": ["https://example.com"], "mode": "full", "depth": 3 }
  ```

  **Response:** `{"scan_id":"...","status":"started"}`

* `GET /scan/status/{scan_id}` → progress & partial findings

* `GET /findings?severity=high&limit=50` → paginated results

* `POST /graph/build` → returns nodes/edges for vis-network

* `POST /alerts/push` → pushes high-severity alert to Firebase topic/device

> Tip: Document response shapes with OpenAPI. FastAPI auto-serves docs at `/docs`.

---

## Security & Ethics

* **Intended Use:** Only scan systems you **own** or have **explicit written permission** to test.
* **Data Handling:** Do not store sensitive payloads beyond what’s needed for triage.
* **Compliance:** Align with local laws, institutional policies, and client agreements.

---

## Troubleshooting

* **Frontend shows `Unexpected token '<', "<!doctype"... is not valid JSON`:**
  Your fetch likely hit an **HTML error page** (CORS or wrong URL) instead of JSON.

  * Confirm `VITE_API_BASE` (no trailing slashes, correct protocol/port).
  * Ensure backend actually runs on **8000** and the route exists.
  * Add your frontend origin to `CORS_ORIGINS`.
  * Check browser DevTools → Network → Response.

* **CORS errors / 403 / Preflight fails:**

  * `OPTIONS` must be allowed, and `allow_headers` must include `Content-Type, Authorization`.
  * Make sure your production origin (Netlify URL) is in `CORS_ORIGINS`.

* **`503` or backend timeouts on Render:**

  * Ensure a **persistent** web service (not cron/worker).
  * Verify start command and health checks.
  * Heavy scans may need higher timeouts or background jobs.

* **Firebase initialization errors:**

  * Double-check `.env` keys.
  * Ensure `firebase.ts` reads `import.meta.env.*`.
  * Avoid multiple `.env` lines for the same var—last one wins.

* **Model version mismatch (scikit-learn pickles):**

  * Retrain or re-export model with the target `scikit-learn` version, or pin version in `requirements.txt`.

---

## Scripts

**Frontend**

* `npm run dev` – Vite dev server
* `npm run build` – production build
* `npm run preview` – preview production build
* `npm run lint` – ESLint

**Backend**

* `uvicorn main:app --reload --port 8000` – local dev
* `pip install -r requirements.txt` – deps
* (optional) `pytest` – if tests added

---

## Contributing

1. Fork & create a feature branch: `feat/<short-title>`
2. Add tests where sensible
3. Follow code style (TS strict, ESLint rules; Black/isort for Python if configured)
4. Open a PR with a clear summary & screenshots for UI changes

---

## License

Licensed under **Apache-2.0**. See `LICENSE` for details.

---

## Acknowledgments

* **shadcn-ui** for elegant primitives
* **Firebase** for auth & notifications
* The **React** ecosystem for stellar tooling

---

## Maintainers

* **Murali N P** — [LinkedIn](https://www.linkedin.com/in/murali-n-p-131034276) · [GitHub](https://github.com/muralinp02)
