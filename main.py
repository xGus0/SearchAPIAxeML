from fastapi import FastAPI, HTTPException, Query, Header
from bs4 import BeautifulSoup
import requests
import os

app = FastAPI(title="API de Pesquisa por Scraping")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/139.0.0.0 Safari/537.36"
}

# API Key do ambiente
API_KEY = os.environ.get("API_KEY", "minha_super_chave")

@app.get("/search")
def search(q: str = Query(..., min_length=1), x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")

    try:
        url = f"https://www.google.com/search?q={q}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erro ao acessar o Google")

        soup = BeautifulSoup(response.text, "lxml")
        results = []

        for g in soup.find_all('div', class_='tF2Cxc'):
            title = g.find('h3')
            link = g.find('a')
            if title and link:
                results.append({"title": title.text, "link": link['href']})

        return {"query": q, "results": results[:10]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
