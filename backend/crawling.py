# backend/crawling.py
from __future__ import annotations
import re
from typing import Dict, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Tunables
TIMEOUT = 10                         # seconds per request
MAX_BYTES = 1_500_000                # cap read size (~1.5 MB)
MAX_LINKS = 200                      # cap number of links returned
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    retries = Retry(
        total=2,           # a couple of retries is plenty for a scan UI
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

def _same_reg(domain: str):
    # allow exact domain and subdomains (example.com, www.example.com)
    domain = domain.lstrip(".")
    return re.compile(rf"(?:^|\.){re.escape(domain)}$", re.IGNORECASE)

def crawl_website(url: str) -> Dict[str, List[str]]:
    """
    Fetch a single page and extract:
      - endpoints: absolute, same-domain http(s) links (max MAX_LINKS)
      - forms: form metadata (action/method/inputs)
    Returns a stable dict even on errors.
    """
    endpoints: List[str] = []
    forms: List[dict] = []

    if not url or not url.startswith(("http://", "https://")):
        return {"endpoints": [], "forms": []}

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    host = parsed.hostname or ""
    same = _same_reg(host)

    try:
        session = _make_session()

        # Stream and read only a reasonable amount to avoid huge responses
        with session.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True) as r:
            # Content-Type must look like HTML
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "html" not in ctype:
                return {"endpoints": [], "forms": []}

            # Read at most MAX_BYTES to keep parsing snappy
            content = b""
            for chunk in r.iter_content(8192):
                content += chunk
                if len(content) >= MAX_BYTES:
                    break

        soup = BeautifulSoup(content, "html.parser")

        # --- Links → absolute, same-domain, http(s), de-duped ---
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href:
                continue
            abs_url = urljoin(url, href)
            p = urlparse(abs_url)

            # Only http(s)
            if p.scheme not in ("http", "https"):
                continue

            # Same-domain only (avoid crawling the whole internet)
            if not p.hostname or not same.match(p.hostname):
                continue

            # Normalize (remove fragments)
            abs_norm = abs_url.split("#", 1)[0]
            if abs_norm in seen:
                continue
            seen.add(abs_norm)
            endpoints.append(abs_norm)

            if len(endpoints) >= MAX_LINKS:
                break

        # --- Forms → summarize action/method/inputs ---
        for form in soup.find_all("form"):
            action = form.get("action")
            action_abs = urljoin(base, action) if action else None
            method = (form.get("method") or "GET").upper()
            inputs = []
            for inp in form.find_all("input"):
                inputs.append({
                    "name": inp.get("name"),
                    "type": (inp.get("type") or "text").lower(),
                })
            forms.append({
                "action": action_abs,
                "method": method,
                "inputs": inputs,
            })

        return {"endpoints": endpoints, "forms": forms}

    except Exception as e:
        # Do not propagate errors to the UI; return stable shape
        # (You can also log e to your server logs if needed)
        return {"endpoints": [], "forms": []}
