from fastapi import FastAPI, HTTPException, Query, Header
from bs4 import BeautifulSoup
from mangum import Mangum
import requests
from urllib.parse import quote_plus

app = FastAPI(title="API de Pesquisa Vercel")

API_KEY = "Gus"

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
def search(q: str = Query(..., min_length=1), x_api_key: str = Header(...), limit: int = Query(10, ge=1, le=20)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")
    
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="DuckDuckGo retornou erro")
        results = parse_duckduckgo(resp.text)
        return {"query": q, "engine": "ddg", "results": results[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

handler = Mangum(app)
