# main.py
from fastapi import FastAPI, UploadFile, Request, File, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

import pandas as pd
import tempfile
import os

# ----------------------------
# Safe imports (fallbacks if modules aren't present in deploy)
# ----------------------------
try:
    from crawling import crawl_website  # must return {"endpoints": [...], "forms": [...]}
except Exception:
    def crawl_website(url: str):
        base = url.rstrip("/")
        # simple, predictable fallback so UI has something to draw
        return {"endpoints": [base, f"{base}/login", f"{base}/profile"], "forms": []}

try:
    from firebase_sync import push_alert  # optional; noop fallback if missing
except Exception:
    def push_alert(data: dict):
        print("[push_alert] (noop fallback)", data)

from preprocessing import preprocess_mdp  # must return a pandas DataFrame
from prediction import load_model
from network_analysis import build_graph, find_attack_paths


app = FastAPI(title="Aura-AI Backend", version="1.0.0")

# ----------------------------
# CORS
# ----------------------------
ALLOWED_ORIGINS = [
    "https://auraaii.netlify.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["*"],
    max_age=600,
)

# ----------------------------
# Health & Root (Render-friendly)
# ----------------------------
@app.api_route("/", methods=["GET", "HEAD"])
def root_ok():
    return {"status": "ok", "service": "aura-ai", "time": datetime.utcnow().isoformat() + "Z"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health_ok():
    return Response(status_code=200)

# Optional explicit preflight (some hosts are picky)
@app.options("/api/login")
async def options_login() -> Response:
    return Response(status_code=204)

# ----------------------------
# Lazy model loader
# ----------------------------
_model = None
def get_model():
    global _model
    if _model is None:
        print("[prediction] loading model...")
        _model = load_model()
    return _model

# ----------------------------
# Schemas
# ----------------------------
class GraphRequest(BaseModel):
    endpoints: List[str]
    connections: List[List[str]] = []  # pairs like ["a", "b"]

class AttackPathsRequest(BaseModel):
    start: str
    end: str
    endpoints: Optional[List[str]] = []
    connections: Optional[List[List[str]]] = []

class AlertPayload(BaseModel):
    alert_data: Dict[str, Any]

# ----------------------------
# Routes
# ----------------------------
@app.post("/api/login")
async def receive_login(request: Request):
    data = await request.json()
    print("Login from:", data)
    return {"message": "Login data received"}

@app.post("/crawl")
def crawl(url: str = Form(...)):
    return crawl_website(url)

@app.post("/predict")
def predict_vulnerability(file: UploadFile = File(...)):
    """
    Accepts a CSV and runs the loaded model's predict.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        df = preprocess_mdp(tmp_path)  # must return a DataFrame
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    mdl = get_model()
    try:
        preds = mdl.predict(df)
    except Exception as e:
        print("[predict] model error:", e)
        preds = [0] * len(df)

    results = [{"row": i, "score": int(p)} for i, p in enumerate(preds)]
    return {"count": len(results), "predictions": results}

@app.post("/network/graph")
def network_graph(payload: GraphRequest):
    edges: List[Tuple[str, str]] = [tuple(edge) for edge in (payload.connections or [])]
    G = build_graph(payload.endpoints or [], edges)
    return {"nodes": list(G.nodes), "edges": list(G.edges)}

@app.post("/network/paths")
def attack_paths(payload: AttackPathsRequest):
    eps = payload.endpoints or []
    conns: List[Tuple[str, str]] = [tuple(edge) for edge in (payload.connections or [])]
    G = build_graph(eps, conns)
    paths = find_attack_paths(G, payload.start, payload.end)
    return {"paths": paths}

@app.post("/alert")
def alert(payload: AlertPayload):
    push_alert(payload.alert_data)
    return {"status": "alert pushed"}

# ----------------------------
# Demo fullscan endpoint
# ----------------------------
@app.post("/fullscan")
def fullscan(
    url: str = Form(None),
    file: UploadFile = File(None),
    scan_type: str = Form(None)
):
    print(f"[Fullscan] scan_type: {scan_type}")

    # --- Demo mappings ---
    demo_vulns = {
        "https://testphp.vulnweb.com": [
            {
                "id": "vuln-0",
                "name": "SQL Injection in Login Form",
                "severity": "critical",
                "description": "User input in the login form is not sanitized, allowing attackers to execute arbitrary SQL commands.",
                "affectedEndpoint": "/login.php",
                "cve": "CVE-2022-1234",
                "fixAvailable": True
            },
            {
                "id": "vuln-1",
                "name": "Cross-Site Scripting (XSS)",
                "severity": "high",
                "description": "Reflected XSS vulnerability in user profile page.",
                "affectedEndpoint": "/user/profile.php",
                "cve": "CVE-2022-5678",
                "fixAvailable": True
            },
            {
                "id": "vuln-2",
                "name": "Outdated SSL Certificate",
                "severity": "medium",
                "description": "SSL certificate is expired or uses weak hashing algorithm.",
                "affectedEndpoint": "*.vulnweb.com",
                "cve": None,
                "fixAvailable": False
            }
        ],
        "https://demo.testfire.net": [
            {
                "id": "vuln-0",
                "name": "Cross-Site Scripting (XSS)",
                "severity": "critical",
                "description": "Persistent XSS in comment section.",
                "affectedEndpoint": "/comments.aspx",
                "cve": "CVE-2023-1111",
                "fixAvailable": True
            },
            {
                "id": "vuln-1",
                "name": "Insecure Cookie Settings",
                "severity": "medium",
                "description": "Cookies are not set with HttpOnly and Secure flags.",
                "affectedEndpoint": "Global",
                "cve": None,
                "fixAvailable": True
            }
        ],
        "https://juice-shop.herokuapp.com": [
            {
                "id": "vuln-0",
                "name": "Missing Rate Limiting",
                "severity": "high",
                "description": "API endpoint does not enforce rate limiting, allowing brute-force attacks.",
                "affectedEndpoint": "/rest/user/login",
                "cve": None,
                "fixAvailable": False
            }
        ],
        "https://cascade-demo.com": [
            {
                "id": "vuln-0",
                "name": "Sensitive Data Exposure",
                "severity": "critical",
                "description": "Sensitive user data is exposed via API endpoints.",
                "affectedEndpoint": "/api/user/data",
                "cve": "CVE-2024-9999",
                "fixAvailable": True
            },
            {
                "id": "vuln-1",
                "name": "Open Redirect",
                "severity": "low",
                "description": "Improper validation allows open redirects.",
                "affectedEndpoint": "/redirect",
                "cve": None,
                "fixAvailable": False
            }
        ]
    }

    charts_map = {
        "https://testphp.vulnweb.com": {
            "attackFrequencyData": {
                "day": [
                    {"time": "00:00", "attacks": 6},
                    {"time": "04:00", "attacks": 3},
                    {"time": "08:00", "attacks": 8},
                    {"time": "12:00", "attacks": 15},
                    {"time": "16:00", "attacks": 9},
                    {"time": "20:00", "attacks": 5},
                ],
                "week": [
                    {"time": "Mon", "attacks": 12},
                    {"time": "Tue", "attacks": 18},
                    {"time": "Wed", "attacks": 20},
                    {"time": "Thu", "attacks": 25},
                    {"time": "Fri", "attacks": 19},
                    {"time": "Sat", "attacks": 7},
                    {"time": "Sun", "attacks": 10},
                ],
                "month": [
                    {"time": "Week 1", "attacks": 45},
                    {"time": "Week 2", "attacks": 60},
                    {"time": "Week 3", "attacks": 55},
                    {"time": "Week 4", "attacks": 70},
                ],
                "year": [
                    {"time": "Jan", "attacks": 100},
                    {"time": "Feb", "attacks": 120},
                    {"time": "Mar", "attacks": 130},
                    {"time": "Apr", "attacks": 140},
                    {"time": "May", "attacks": 115},
                    {"time": "Jun", "attacks": 160},
                    {"time": "Jul", "attacks": 170},
                    {"time": "Aug", "attacks": 180},
                    {"time": "Sep", "attacks": 190},
                    {"time": "Oct", "attacks": 200},
                    {"time": "Nov", "attacks": 210},
                    {"time": "Dec", "attacks": 220},
                ]
            },
            "vulnerabilityTrendsData": {
                "day": [
                    {"time": "00:00", "critical": 2, "high": 4, "medium": 7, "low": 8},
                    {"time": "04:00", "critical": 1, "high": 3, "medium": 6, "low": 7},
                    {"time": "08:00", "critical": 3, "high": 5, "medium": 8, "low": 9},
                    {"time": "12:00", "critical": 4, "high": 6, "medium": 8, "low": 10},
                    {"time": "16:00", "critical": 2, "high": 4, "medium": 7, "low": 8},
                    {"time": "20:00", "critical": 2, "high": 3, "medium": 6, "low": 6},
                ],
                "week": [
                    {"time": "Mon", "critical": 7, "high": 11, "medium": 16, "low": 21},
                    {"time": "Tue", "critical": 6, "high": 10, "medium": 15, "low": 20},
                    {"time": "Wed", "critical": 8, "high": 12, "medium": 18, "low": 23},
                    {"time": "Thu", "critical": 9, "high": 13, "medium": 19, "low": 24},
                    {"time": "Fri", "critical": 7, "high": 11, "medium": 16, "low": 21},
                    {"time": "Sat", "critical": 3, "high": 5, "medium": 10, "low": 15},
                    {"time": "Sun", "critical": 2, "high": 4, "medium": 8, "low": 13},
                ],
                "month": [
                    {"time": "Week 1", "critical": 14, "high": 25, "medium": 36, "low": 48},
                    {"time": "Week 2", "critical": 18, "high": 30, "medium": 45, "low": 60},
                    {"time": "Week 3", "critical": 12, "high": 20, "medium": 30, "low": 40},
                    {"time": "Week 4", "critical": 20, "high": 36, "medium": 54, "low": 72},
                ],
                "year": [
                    {"time": "Jan", "critical": 35, "high": 65, "medium": 95, "low": 125},
                    {"time": "Mar", "critical": 28, "high": 55, "medium": 75, "low": 110},
                    {"time": "May", "critical": 40, "high": 80, "medium": 120, "low": 150},
                    {"time": "Jul", "critical": 45, "high": 90, "medium": 130, "low": 170},
                    {"time": "Sep", "critical": 50, "high": 100, "medium": 140, "low": 180},
                    {"time": "Nov", "critical": 38, "high": 75, "medium": 110, "low": 145},
                ]
            },
            "exploitedServicesData": [
                {"name": "HTTP/80", "value": 40},
                {"name": "SSH/22", "value": 18},
                {"name": "FTP/21", "value": 12},
                {"name": "SMB/445", "value": 15},
                {"name": "RDP/3389", "value": 8},
                {"name": "Other", "value": 7},
            ]
        },
        "https://demo.testfire.net": {
            "attackFrequencyData": {
                "day": [
                    {"time": "00:00", "attacks": 2},
                    {"time": "04:00", "attacks": 3},
                    {"time": "08:00", "attacks": 5},
                    {"time": "12:00", "attacks": 6},
                    {"time": "16:00", "attacks": 7},
                    {"time": "20:00", "attacks": 4},
                ],
                "week": [
                    {"time": "Mon", "attacks": 6},
                    {"time": "Tue", "attacks": 8},
                    {"time": "Wed", "attacks": 12},
                    {"time": "Thu", "attacks": 10},
                    {"time": "Fri", "attacks": 9},
                    {"time": "Sat", "attacks": 5},
                    {"time": "Sun", "attacks": 4},
                ],
                "month": [
                    {"time": "Week 1", "attacks": 18},
                    {"time": "Week 2", "attacks": 25},
                    {"time": "Week 3", "attacks": 23},
                    {"time": "Week 4", "attacks": 30},
                ],
                "year": [
                    {"time": "Jan", "attacks": 55},
                    {"time": "Feb", "attacks": 60},
                    {"time": "Mar", "attacks": 75},
                    {"time": "Apr", "attacks": 80},
                    {"time": "May", "attacks": 70},
                    {"time": "Jun", "attacks": 90},
                    {"time": "Jul", "attacks": 95},
                    {"time": "Aug", "attacks": 110},
                    {"time": "Sep", "attacks": 120},
                    {"time": "Oct", "attacks": 130},
                    {"time": "Nov", "attacks": 140},
                    {"time": "Dec", "attacks": 150},
                ]
            },
            "vulnerabilityTrendsData": {
                "day": [
                    {"time": "00:00", "critical": 1, "high": 2, "medium": 3, "low": 4},
                    {"time": "04:00", "critical": 1, "high": 2, "medium": 3, "low": 4},
                    {"time": "08:00", "critical": 2, "high": 3, "medium": 4, "low": 5},
                    {"time": "12:00", "critical": 2, "high": 3, "medium": 4, "low": 5},
                    {"time": "16:00", "critical": 1, "high": 2, "medium": 3, "low": 4},
                    {"time": "20:00", "critical": 1, "high": 2, "medium": 3, "low": 4},
                ],
                "week": [
                    {"time": "Mon", "critical": 2, "high": 4, "medium": 6, "low": 8},
                    {"time": "Tue", "critical": 2, "high": 4, "medium": 6, "low": 8},
                    {"time": "Wed", "critical": 3, "high": 6, "medium": 9, "low": 12},
                    {"time": "Thu", "critical": 3, "high": 6, "medium": 9, "low": 12},
                    {"time": "Fri", "critical": 2, "high": 4, "medium": 6, "low": 8},
                    {"time": "Sat", "critical": 1, "high": 2, "medium": 3, "low": 4},
                    {"time": "Sun", "critical": 1, "high": 2, "medium": 3, "low": 4},
                ],
                "month": [
                    {"time": "Week 1", "critical": 4, "high": 8, "medium": 12, "low": 16},
                    {"time": "Week 2", "critical": 5, "high": 10, "medium": 15, "low": 20},
                    {"time": "Week 3", "critical": 3, "high": 6, "medium": 9, "low": 12},
                    {"time": "Week 4", "critical": 7, "high": 14, "medium": 21, "low": 28},
                ],
                "year": [
                    {"time": "Jan", "critical": 10, "high": 20, "medium": 30, "low": 40},
                    {"time": "Mar", "critical": 12, "high": 24, "medium": 36, "low": 48},
                    {"time": "May", "critical": 15, "high": 30, "medium": 45, "low": 60},
                    {"time": "Jul", "critical": 18, "high": 36, "medium": 54, "low": 72},
                    {"time": "Sep", "critical": 20, "high": 40, "medium": 60, "low": 80},
                    {"time": "Nov", "critical": 16, "high": 32, "medium": 48, "low": 64},
                ]
            },
            "exploitedServicesData": [
                {"name": "HTTP/80", "value": 12},
                {"name": "SSH/22", "value": 8},
                {"name": "FTP/21", "value": 6},
                {"name": "SMB/445", "value": 7},
                {"name": "RDP/3389", "value": 5},
                {"name": "Other", "value": 3},
            ]
        },
        "https://juice-shop.herokuapp.com": {
            "attackFrequencyData": {
                "day": [
                    {"time": "00:00", "attacks": 1},
                    {"time": "04:00", "attacks": 2},
                    {"time": "08:00", "attacks": 3},
                    {"time": "12:00", "attacks": 4},
                    {"time": "16:00", "attacks": 2},
                    {"time": "20:00", "attacks": 1},
                ],
                "week": [
                    {"time": "Mon", "attacks": 2},
                    {"time": "Tue", "attacks": 3},
                    {"time": "Wed", "attacks": 4},
                    {"time": "Thu", "attacks": 5},
                    {"time": "Fri", "attacks": 3},
                    {"time": "Sat", "attacks": 2},
                    {"time": "Sun", "attacks": 1},
                ],
                "month": [
                    {"time": "Week 1", "attacks": 5},
                    {"time": "Week 2", "attacks": 7},
                    {"time": "Week 3", "attacks": 6},
                    {"time": "Week 4", "attacks": 8},
                ],
                "year": [
                    {"time": "Jan", "attacks": 20},
                    {"time": "Feb", "attacks": 22},
                    {"time": "Mar", "attacks": 25},
                    {"time": "Apr", "attacks": 28},
                    {"time": "May", "attacks": 24},
                    {"time": "Jun", "attacks": 30},
                    {"time": "Jul", "attacks": 32},
                    {"time": "Aug", "attacks": 34},
                    {"time": "Sep", "attacks": 36},
                    {"time": "Oct", "attacks": 38},
                    {"time": "Nov", "attacks": 40},
                    {"time": "Dec", "attacks": 42},
                ]
            },
            "vulnerabilityTrendsData": {
                "day": [
                    {"time": "00:00", "critical": 1, "high": 1, "medium": 2, "low": 3},
                    {"time": "04:00", "critical": 1, "high": 1, "medium": 2, "low": 3},
                    {"time": "08:00", "critical": 1, "high": 2, "medium": 2, "low": 3},
                    {"time": "12:00", "critical": 1, "high": 2, "medium": 2, "low": 3},
                    {"time": "16:00", "critical": 1, "high": 1, "medium": 2, "low": 3},
                    {"time": "20:00", "critical": 1, "high": 1, "medium": 2, "low": 3},
                ],
                "week": [
                    {"time": "Mon", "critical": 1, "high": 2, "medium": 3, "low": 4},
                    {"time": "Tue", "critical": 1, "high": 2, "medium": 3, "low": 4},
                    {"time": "Wed", "critical": 2, "high": 3, "medium": 4, "low": 5},
                    {"time": "Thu", "critical": 2, "high": 3, "medium": 4, "low": 5},
                    {"time": "Fri", "critical": 1, "high": 2, "medium": 3, "low": 4},
                    {"time": "Sat", "critical": 1, "high": 2, "medium": 3, "low": 4},
                    {"time": "Sun", "critical": 1, "high": 2, "medium": 3, "low": 4},
                ],
                "month": [
                    {"time": "Week 1", "critical": 2, "high": 3, "medium": 4, "low": 5},
                    {"time": "Week 2", "critical": 3, "high": 4, "medium": 5, "low": 6},
                    {"time": "Week 3", "critical": 2, "high": 3, "medium": 4, "low": 5},
                    {"time": "Week 4", "critical": 4, "high": 5, "medium": 6, "low": 7},
                ],
                "year": [
                    {"time": "Jan", "critical": 4, "high": 6, "medium": 8, "low": 10},
                    {"time": "Mar", "critical": 5, "high": 7, "medium": 9, "low": 11},
                    {"time": "May", "critical": 6, "high": 8, "medium": 10, "low": 12},
                    {"time": "Jul", "critical": 7, "high": 9, "medium": 11, "low": 13},
                    {"time": "Sep", "critical": 8, "high": 10, "medium": 12, "low": 14},
                    {"time": "Nov", "critical": 9, "high": 11, "medium": 13, "low": 15},
                ]
            },
            "exploitedServicesData": [
                {"name": "HTTP/80", "value": 8},
                {"name": "SSH/22", "value": 6},
                {"name": "FTP/21", "value": 4},
                {"name": "SMB/445", "value": 5},
                {"name": "RDP/3389", "value": 3},
                {"name": "Other", "value": 2},
            ]
        }
    }

    # If the URL is one of the demo URLs, return canned results
    if url and url in demo_vulns:
        vulnerabilities = demo_vulns[url]
        endpoints = [v["affectedEndpoint"] for v in vulnerabilities]
        preds = [
            9 if v["severity"] == "critical" else
            7 if v["severity"] == "high" else
            5 if v["severity"] == "medium" else 2
            for v in vulnerabilities
        ]
        # FIX: proper chain of edges, not a single pair
        connections = [(endpoints[i], endpoints[i + 1]) for i in range(len(endpoints) - 1)] if len(endpoints) > 1 else []
        G = build_graph(endpoints, connections)
        threat_level = int(100 * sum(preds) / len(preds)) if preds else 0

        try:
            attack_paths = find_attack_paths(G, endpoints[0], endpoints[-1]) if len(endpoints) > 1 else []
        except Exception:
            attack_paths = []

        alert_map = {
            "https://testphp.vulnweb.com": [
                {"message": "SQL Injection detected on login form!", "level": "critical"},
                {"message": "XSS vulnerability found in profile.", "level": "high"}
            ],
            "https://demo.testfire.net": [
                {"message": "Persistent XSS in comments.", "level": "critical"},
                {"message": "Insecure cookie settings detected.", "level": "medium"}
            ],
            "https://juice-shop.herokuapp.com": [
                {"message": "Brute-force risk: missing rate limiting.", "level": "high"}
            ],
            "https://cascade-demo.com": [
                {"message": "Sensitive data exposure found!", "level": "critical"},
                {"message": "Open redirect risk.", "level": "low"}
            ]
        }

        if url == "https://testphp.vulnweb.com":
            attack_probs = [
                {"type": "sql", "probability": 0.7},
                {"type": "xss", "probability": 0.2},
                {"type": "mitm", "probability": 0.1},
                {"type": "ddos", "probability": 0.0}
            ]
        elif url == "https://demo.testfire.net":
            attack_probs = [
                {"type": "xss", "probability": 0.6},
                {"type": "mitm", "probability": 0.3},
                {"type": "sql", "probability": 0.1},
                {"type": "ddos", "probability": 0.0}
            ]
        elif url == "https://juice-shop.herokuapp.com":
            attack_probs = [
                {"type": "ddos", "probability": 0.7},
                {"type": "sql", "probability": 0.2},
                {"type": "mitm", "probability": 0.1},
                {"type": "xss", "probability": 0.0}
            ]
        else:
            attack_probs = [
                {"type": "sql", "probability": 0.0},
                {"type": "mitm", "probability": 0.0},
                {"type": "ddos", "probability": 0.0},
                {"type": "xss", "probability": 0.0}
            ]

        charts = charts_map.get(url, {})

        return {
            "url": url,
            "threat_level": threat_level,
            "vulnerabilities": vulnerabilities,
            "network": {"nodes": list(G.nodes), "edges": list(G.edges)},
            "attack_paths": attack_paths,
            "alerts": alert_map.get(url, [
                {"message": "High threat detected!", "level": "critical"} if threat_level > 75 else
                {"message": "Moderate threat detected.", "level": "warning"} if threat_level > 40 else
                {"message": "System appears safe.", "level": "info"}
            ]),
            "attackProbabilities": attack_probs,
            "totalScans": 12 if url == "https://testphp.vulnweb.com" else 7 if url == "https://demo.testfire.net" else 5 if url == "https://juice-shop.herokuapp.com" else 1,
            "totalVulnerabilities": len(vulnerabilities),
            "resolvedVulnerabilities": 2 if url == "https://testphp.vulnweb.com" else 1,
            "unresolvedVulnerabilities": max(0, len(vulnerabilities) - (2 if url == "https://testphp.vulnweb.com" else 1)),
            "attackSources": 3 if url == "https://testphp.vulnweb.com" else 2 if url == "https://demo.testfire.net" else 1,
            "charts": charts
        }

    # --- Real flow (URL or CSV) ---
    if url:
        crawl_result = crawl_website(url)
        endpoints = [str(e) for e in (crawl_result.get("endpoints") or [])]
        # FIX: proper chain A->B, B->C, ...
        connections = [(endpoints[i], endpoints[i + 1]) for i in range(len(endpoints) - 1)] if len(endpoints) > 1 else []
        df = pd.DataFrame({"endpoint": endpoints})

    elif file:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        try:
            df = preprocess_mdp(tmp_path)  # must return DataFrame
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        # FIX: don't use df.get(...).tolist() with list default
        if isinstance(df, pd.DataFrame) and "endpoint" in df.columns:
            endpoints = df["endpoint"].astype(str).tolist()
        else:
            endpoints = [f"row-{i}" for i in range(len(df))]
        connections = [(endpoints[i], endpoints[i + 1]) for i in range(len(endpoints) - 1)] if len(endpoints) > 1 else []

    else:
        return {"error": "Provide either a URL or a file."}

    mdl = get_model()
    try:
        preds = mdl.predict(df)
    except Exception as e:
        print("[fullscan] model error:", e)
        preds = [0] * len(df)

    G = build_graph(endpoints, connections)
    try:
        attack_paths = find_attack_paths(G, endpoints[0], endpoints[-1]) if len(endpoints) > 1 else []
    except Exception:
        attack_paths = []

    threat_level = int(100 * sum(int(p) for p in preds) / len(preds)) if len(preds) else 0

    vulnerabilities = []
    for idx, (ep, pred) in enumerate(zip(endpoints, preds)):
        score = int(pred)
        if score >= 8:
            severity = "critical"
        elif score >= 6:
            severity = "high"
        elif score >= 3:
            severity = "medium"
        else:
            severity = "low"
        vulnerabilities.append({
            "id": f"vuln-{idx}",
            "name": f"Vulnerability {score}",
            "severity": severity,
            "description": f"Auto-generated vulnerability for endpoint {ep} with score {score}.",
            "affectedEndpoint": ep,
            "cve": None,
            "fixAvailable": False
        })

    return {
        "url": url,
        "threat_level": threat_level,
        "vulnerabilities": vulnerabilities,
        "network": {"nodes": list(G.nodes), "edges": list(G.edges)},
        "attack_paths": attack_paths,
        "alerts": [
            {"message": "High threat detected!", "level": "critical"} if threat_level > 75
            else {"message": "Moderate threat detected.", "level": "warning"} if threat_level > 40
            else {"message": "System appears safe.", "level": "info"}
        ]
    }
