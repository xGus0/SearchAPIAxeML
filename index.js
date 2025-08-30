export default {
  async fetch(request) {
    try {
      const API_KEY = "Gus"; // chave esperada no header x-api-key

      const url = new URL(request.url);
      const q = (url.searchParams.get("q") || "").trim();
      const limit = Math.min(20, Math.max(1, Number(url.searchParams.get("limit") || 5)));

      const providedKey = request.headers.get("x-api-key") || "";

      if (!q) {
        return new Response(JSON.stringify({ error: "Parâmetro 'q' (query) é obrigatório." }), {
          status: 400,
          headers: jsonHeaders(),
        });
      }

      if (providedKey !== API_KEY) {
        return new Response(JSON.stringify({ error: "API Key inválida." }), {
          status: 401,
          headers: jsonHeaders(),
        });
      }

      // Busca HTML do DuckDuckGo (endpoint HTML)
      const ddgUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(q)}`;
      const resp = await fetch(ddgUrl, {
        headers: { "User-Agent": "Mozilla/5.0 (compatible)" },
        // note: Cloudflare Worker fetch tem timeout interno; DuckDuckGo costuma responder rápido
      });

      if (!resp.ok) {
        return new Response(JSON.stringify({ error: `DuckDuckGo retornou status ${resp.status}` }), {
          status: 502,
          headers: jsonHeaders(),
        });
      }

      const html = await resp.text();

      // Extrair resultados: procura por <a ... class="...result__a..." href="...">TITLE</a>
      const results = [];
      const regex = /<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
      let match;
      while ((match = regex.exec(html)) && results.length < limit) {
        let link = match[1];
        let title = match[2].replace(/<[^>]*>/g, "").trim();

        // Decodificar links redirecionados do DuckDuckGo (uddg param)
        const mUddg = link.match(/[?&]uddg=([^&]+)/);
        if (mUddg) {
          try { link = decodeURIComponent(mUddg[1]); } catch { /* keep original */ }
        } else if (link.startsWith("//")) {
          link = "https:" + link;
        }

        results.push({ title, link });
      }

      return new Response(JSON.stringify({ query: q, engine: "ddg", results }), {
        status: 200,
        headers: jsonHeaders(),
      });

    } catch (err) {
      return new Response(JSON.stringify({ error: String(err.message || err) }), {
        status: 500,
        headers: jsonHeaders(),
      });
    }
  }
};

function jsonHeaders() {
  return {
    "Content-Type": "application/json;charset=utf-8",
    "Access-Control-Allow-Origin": "*",             // permite chamadas do browser
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "x-api-key, Content-Type",
  };
}
