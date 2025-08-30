import fetch from "node-fetch"; // se usar Node >=18, fetch já está nativo
import data from "./data.js";

async function searchDuckDuckGo(query, limit = 5) {
  const url = new URL(data.endpoint);
  url.searchParams.append("q", query);
  url.searchParams.append("limit", limit);

  const response = await fetch(url.toString(), {
    headers: { [data.auth.headerName]: data.auth.exampleKey }
  });

  if (!response.ok) {
    throw new Error(`Falha ao consultar API: ${response.status} - ${response.statusText}`);
  }

  const json = await response.json();
  return json.results;
}

// Teste da API
(async () => {
  try {
    const results = await searchDuckDuckGo("python", 5);
    console.log(`Resultados da pesquisa "python":\n`);
    results.forEach((r, i) => {
      console.log(`${i + 1}. ${r.title} → ${r.link}`);
    });
  } catch (e) {
    console.error(e.message);
  }
})();
