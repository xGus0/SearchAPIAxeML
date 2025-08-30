# main.py
from fastapi import FastAPI, HTTPException, Query, Header
from bs4 import BeautifulSoup
import requests
import os
import logging
import random
import time
from urllib.parse import quote_plus
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = FastAPI(title="API de Pesquisa por Scraping")

# Lista curta de User-Agents mais realistas - adiciona outros se quiser
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# Configuração de logging (ver logs no Render para mensagens completas)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper_api")

# API Key do ambiente
API_KEY = os.environ.get("API_KEY", "minha_super_chave")

# Cria session com retry/backoff
def create_session():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def fetch(session: requests.Session, url: str, headers: dict, timeout: int = 10):
    resp = session.get(url, headers=headers, timeout=timeout)
    return resp

def parse_google(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    results = []
    # Procura por todos os <h3> (títulos dos resultados) e pega o <a> pai
    for h3 in soup.find_all('h3'):
        a = h3.find_parent('a')
        if a and a.has_attr('href'):
            title = h3.get_text(strip=True)
            link = a['href']
            # evitar anchors internos
            if link.startswith('/'):
                # Google às vezes retorna /url?q=...
                # a['href'] pode ser /url?q=...; extrair q= parte
                if link.startswith('/url?'):
                    # tentativa simples
                    from urllib.parse import parse_qs, urlparse, unquote
                    q = urlparse(link).query
                    params = parse_qs(q)
                    if 'q' in params:
                        link = params['q'][0]
                    else:
                        continue
                else:
                    continue
            results.append({"title": title, "link": link})
    return results

def parse_duckduckgo(html_text):
    soup = BeautifulSoup(html_text, "lxml")
    results = []
    # DuckDuckGo HTML endpoint tem classes 'result' e anchors com class 'result__a'
    for a in soup.select("a.result__a"):
        title = a.get_text(strip=True)
        link = a.get("href")
        if title and link:
            results.append({"title": title, "link": link})
    # fallback: procurar anchors dentro de div.result
    if not results:
        for div in soup.select("div.result"):
            a = div.find("a")
            if a and a.get("href"):
                title = a.get_text(strip=True)
                link = a.get("href")
                results.append({"title": title, "link": link})
    return results

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search")
def search(
    q: str = Query(..., min_length=1),
    x_api_key: str = Header(...),
    engine: str = Query("auto", description="auto|google|ddg"),
    limit: int = Query(10, ge=1, le=50),
    delay: float = Query(0.0, ge=0.0, le=10.0)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")

    session = create_session()
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    encoded_q = quote_plus(q)
    tried_engines = []

    # opcional delay (em segundos) para reduzir detecção
    if delay and delay > 0:
        logger.info(f"Delay solicitado: {delay}s")
        time.sleep(delay)

    def try_google():
        tried_engines.append("google")
        url = f"https://www.google.com/search?q={encoded_q}&hl=pt-BR"
        logger.info(f"Consultando Google: {url}")
        resp = fetch(session, url, headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Google retornou status {resp.status_code}")
        return parse_google(resp.text)

    def try_ddg():
        tried_engines.append("ddg")
        # DuckDuckGo HTML endpoint
        url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
        logger.info(f"Consultando DuckDuckGo: {url}")
        resp = fetch(session, url, headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"DuckDuckGo retornou status {resp.status_code}")
        return parse_duckduckgo(resp.text)

    results = []
    used_engine = None

    try:
        if engine == "google":
            results = try_google()
            used_engine = "google"
        elif engine == "ddg":
            results = try_ddg()
            used_engine = "ddg"
        else:  # auto
            # tenta Google primeiro; se falhar, tenta DuckDuckGo
            try:
                results = try_google()
                used_engine = "google"
            except Exception as ge:
                logger.warning(f"Google falhou: {ge}. Tentando DuckDuckGo como fallback.")
                try:
                    results = try_ddg()
                    used_engine = "ddg"
                except Exception as de:
                    logger.error(f"Ambos falharam. Google: {ge}; DDG: {de}")
                    raise Exception(f"Falha ao consultar motores de busca. Detalhes: Google: {ge}; DuckDuckGo: {de}")

        # deduplicar por link simples mantendo ordem
        seen = set()
        dedup = []
        for r in results:
            link = r.get("link")
            if not link:
                continue
            if link in seen:
                continue
            seen.add(link)
            dedup.append(r)

        return {"query": q, "engine": used_engine, "results": dedup[:limit]}

    except Exception as e:
        # log completo para debugar no Render
        logger.exception("Erro durante /search")
        # retornar mensagem curta ao cliente, detalhes completos ficam no log do Render
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar a busca: {str(e)}")
