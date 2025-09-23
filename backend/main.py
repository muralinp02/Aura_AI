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
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import ssl, socket

# ----------------------------
# Safe imports (fallbacks if modules aren't present in deploy)
# ----------------------------
try:
    from crawling import crawl_website  # if you have a crawling module, prefer it
except Exception:
    # fallback crawler (safe, non-intrusive): fetch pages from same host, extract links & forms
    def crawl_website(url: str):
        """
        Simple, polite BFS crawler that:
         - ensures URL is https:// or http://
         - fetches the start URL (and some same-domain links up to a limit)
         - extracts form actions and anchors
         - returns a dict with endpoints, pages, forms, headers, and tls info
        """
        if not url:
            return {"error": "No URL provided"}
        url = url.strip()
        if not re.match(r"^https?://", url):
            url = "https://" + url

        try:
            parsed = urlparse(url)
            base_netloc = parsed.netloc
            base_scheme = parsed.scheme
            base_root = f"{base_scheme}://{base_netloc}"
        except Exception:
            return {"error": "Invalid URL"}

        session = requests.Session()
        session.headers.update({"User-Agent": "Aura-AI-Crawler/1.0 (+https://example/)"})
        REQUEST_TIMEOUT = 8
        MAX_PAGES = 30
        MAX_LINKS_PER_PAGE = 80

        def same_domain(u):
            try:
                return urlparse(u).netloc == base_netloc
            except Exception:
                return False

        discovered = set()
        queue = [url]
        discovered.add(url)
        pages_info = []
        endpoints = []
        forms = []
        security_headers = {}
        server_info = {}

        def fetch_page(u):
            try:
                r = session.get(u, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            except Exception as e:
                return {"url": u, "error": str(e)}
            headers = {k.lower(): v for k, v in r.headers.items()}
            # gather some security-relevant headers
            for h in ("content-security-policy", "strict-transport-security", "x-frame-options", "x-content-type-options", "referrer-policy"):
                if h in headers and h not in security_headers:
                    security_headers[h] = headers[h]
            server_info["server"] = headers.get("server")
            content_type = headers.get("content-type", "")
            links = []
            page_forms = []
            if "html" in content_type.lower():
                try:
                    soup = BeautifulSoup(r.text, "html.parser")
                    anchors = soup.find_all("a", href=True)[:MAX_LINKS_PER_PAGE]
                    for a in anchors:
                        href = a["href"].strip()
                        if not href:
                            continue
                        full = urljoin(u, href)
                        if same_domain(full):
                            links.append(full)
                    for f in soup.find_all("form")[:50]:
                        action = f.get("action") or u
                        method = (f.get("method") or "get").lower()
                        full_action = urljoin(u, action)
                        inputs = []
                        for inp in f.find_all(["input", "textarea", "select"]):
                            name = inp.get("name")
                            itype = inp.get("type") or inp.name
                            inputs.append({"name": name, "type": itype})
                        page_forms.append({"action": full_action, "method": method, "inputs": inputs})
                except Exception:
                    pass
            return {"url": u, "status": r.status_code, "content_type": content_type, "links": links, "forms": page_forms}

        # BFS-ish crawl
        while queue and len(discovered) <= MAX_PAGES:
            cur = queue.pop(0)
            result = fetch_page(cur)
            pages_info.append({"url": cur, "status": result.get("status"), "error": result.get("error")})
            if not result.get("error"):
                endpoints.append(result.get("url"))
                for f in result.get("forms", []):
                    forms.append(f)
                for link in result.get("links", []):
                    if link not in discovered and len(discovered) < MAX_PAGES:
                        discovered.add(link)
                        queue.append(link)

        # TLS info best-effort
        tls_info = {}
        try:
            host = base_netloc.split(":")[0]
            ctx = ssl.create_default_context()
            with socket.create_connection((host, 443), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    not_after = cert.get("notAfter")
                    tls_info["raw"] = cert
                    tls_info["notAfter"] = not_after
        except Exception as e:
            tls_info["error"] = str(e)

        return {
            "url": url,
            "root": base_root,
            "endpoints": endpoints,
            "pages": pages_info,
            "forms": forms,
            "security_headers": security_headers,
            "server_info": server_info,
            "tls": tls_info,
            "crawled_count": len(endpoints),
        }

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
    "http://aurababy.life",
    "https://aurababy.life",
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
    # If your build_graph returns networkx Graph, nodes/edges will work; if fallback SimpleGraph, adjust accordingly
    nodes = list(getattr(G, "nodes", [])) if not isinstance(G, (list, tuple)) else list(G)
    edges_list = list(getattr(G, "edges", [])) if not isinstance(G, (list, tuple)) else []
    return {"nodes": nodes, "edges": edges_list}

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
        ],
        # added aurababy demo entries
        "https://aurababy.life": [
            {
                "id": "vuln-0",
                "name": "Demo Sensitive Data Exposure",
                "severity": "medium",
                "description": "Demo: possible data exposure on profile endpoint.",
                "affectedEndpoint": "/profile",
                "cve": None,
                "fixAvailable": False
            }
        ],
        "http://aurababy.life": [
            {
                "id": "vuln-0",
                "name": "Demo Sensitive Data Exposure",
                "severity": "medium",
                "description": "Demo: possible data exposure on profile endpoint.",
                "affectedEndpoint": "/profile",
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
            },
        },
        "https://demo.testfire.net": {
            "attackFrequencyData": {
                "day": [
                    {"time": "00:00", "attacks": 2},
                    {"time": "12:00", "attacks": 6},
                ],
            }
        },
        "https://juice-shop.herokuapp.com": {
            "attackFrequencyData": {
                "day": [
                    {"time": "00:00", "attacks": 1},
                    {"time": "12:00", "attacks": 4},
                ],
            }
        },
        "https://aurababy.life": {
            "attackFrequencyData": {
                "day": [
                    {"time": "00:00", "attacks": 1},
                    {"time": "12:00", "attacks": 2},
                ]
            }
        },
        "http://aurababy.life": {
            "attackFrequencyData": {
                "day": [
                    {"time": "00:00", "attacks": 1},
                    {"time": "12:00", "attacks": 2},
                ]
            }
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
            ],
            "https://aurababy.life": [
                {"message": "Demo site scanned", "level": "info"}
            ],
            "http://aurababy.life": [
                {"message": "Demo site scanned", "level": "info"}
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
            "network": {"nodes": list(getattr(G, "nodes", [])), "edges": list(getattr(G, "edges", []))},
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
        try:
            score = int(pred)
        except Exception:
            score = 0
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
        "network": {"nodes": list(getattr(G, "nodes", [])), "edges": list(getattr(G, "edges", []))},
        "attack_paths": attack_paths,
        "alerts": [
            {"message": "High threat detected!", "level": "critical"} if threat_level > 75
            else {"message": "Moderate threat detected.", "level": "warning"} if threat_level > 40
            else {"message": "System appears safe.", "level": "info"}
        ]
    }
