from fastapi import FastAPI, HTTPException, Query, Header
from bs4 import BeautifulSoup
import requests
import os
from mangum import Mangum
import random
import time
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
import logging

app = FastAPI(title="API de Pesquisa por Scraping Vercel")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper_vercel")

# Lista de User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

API_KEY = os.environ.get("API_KEY", "Gus")  # variável de ambiente

def fetch(session, url, headers, timeout=10):
    resp = session.get(url, headers=headers, timeout=timeout)
    return resp

def parse_google(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    results = []
    for h3 in soup.find_all("h3"):
        a = h3.find_parent("a")
        if a and a.has_attr("href"):
            link = a["href"]
            if link.startswith("/url?"):
                params = parse_qs(urlparse(link).query)
                link = params.get("q", [""])[0]
            results.append({"title": h3.get_text(strip=True), "link": link})
    return results

def parse_duckduckgo(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    results = []
    for a in soup.select("a.result__a"):
        title = a.get_text(strip=True)
        link = a.get("href")
        if title and link:
            results.append({"title": title, "link": link})
    return results

@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1),
    x_api_key: str = Header(...),
    engine: str = Query("auto"),
    limit: int = Query(10, ge=1, le=50),
    delay: float = Query(0.0, ge=0.0, le=10.0)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")

    import requests
    session = requests.Session()
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    encoded_q = quote_plus(q)
    if delay > 0:
        time.sleep(delay)

    try:
        results = []
        used_engine = None

        if engine in ["google", "auto"]:
            try:
                url = f"https://www.google.com/search?q={encoded_q}&hl=pt-BR"
                resp = fetch(session, url, headers)
                if resp.status_code == 200:
                    results = parse_google(resp.text)
                    used_engine = "google"
                elif engine == "google":
                    raise HTTPException(status_code=500, detail="Google retornou erro")
            except Exception as e:
                if engine == "google":
                    raise HTTPException(status_code=500, detail=str(e))
                logger.warning(f"Google falhou, tentando DuckDuckGo: {e}")

        if (engine == "ddg") or (engine == "auto" and not results):
            url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
            resp = fetch(session, url, headers)
            if resp.status_code == 200:
                results = parse_duckduckgo(resp.text)
                used_engine = "ddg"

        # deduplicar
        seen = set()
        dedup = []
        for r in results:
            if r["link"] not in seen:
                dedup.append(r)
                seen.add(r["link"])

        return {"query": q, "engine": used_engine, "results": dedup[:limit]}
    except Exception as e:
        logger.exception("Erro na pesquisa")
        raise HTTPException(status_code=500, detail=str(e))

# Adaptador serverless
handler = Mangum(app)
