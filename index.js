// index.js (Node 18+)
import data from "./data.js";

function decodeDuckDuckGoLink(url) {
  // DuckDuckGo sometimes returns links like //duckduckgo.com/l/?uddg=ENCODED_URL
  try {
    const m = url.match(/[?&]uddg=([^&]+)/);
    if (m) return decodeURIComponent(m[1]);
    // sometimes link starts with '//' (protocol relative) — normalize to https
    if (url.startsWith("//")) return "https:" + url;
    return url;
  } catch {
    return url;
  }
}

async function searchDuckDuckGo(query, limit = 5) {
  if (!query) throw new Error("Query vazia");

  const url = new URL(data.endpoint);
  url.searchParams.set("q", query);
  url.searchParams.set("limit", String(limit));

  const res = await fetch(url.toString(), {
    headers: { [data.auth.headerName]: data.auth.exampleKey }
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Falha ao consultar API: ${res.status} ${res.statusText} ${text ? "- " + text : ""}`);
  }

  const json = await res.json();

  // Normalizar/decodificar links que sejam redirecionamentos do DuckDuckGo
  if (Array.isArray(json.results)) {
    json.results = json.results.map(r => {
      const link = typeof r.link === "string" ? decodeDuckDuckGoLink(r.link) : r.link;
      return { title: r.title ?? "", link };
    });
  }

  return json;
}

// Executa: node index.js termo [limit]
(async () => {
  try {
    const argv = process.argv.slice(2);
    const query = argv[0] ?? "python";
    const limit = argv[1] ? Number(argv[1]) : 5;

    const dataResponse = await searchDuckDuckGo(query, limit);

    console.log(`\nResultados para: "${dataResponse.query}" (engine: ${dataResponse.engine})\n`);
    if (!dataResponse.results || dataResponse.results.length === 0) {
      console.log("Nenhum resultado encontrado.");
      return;
    }

    dataResponse.results.forEach((r, i) => {
      console.log(`${i + 1}. ${r.title}\n   → ${r.link}\n`);
    });
  } catch (err) {
    console.error("Erro:", err.message);
    process.exitCode = 1;
  }
})();
