// data.js
export default {
  name: "DuckDuckGo Search API",
  description: "Cloudflare Worker que retorna resultados do DuckDuckGo.",
  tags: ["search", "duckduckgo", "api", "serverless"],
  endpoint: "https://searchapiaxeml.gustavo-vasconcelos0304.workers.dev/", // sua URL do Worker
  auth: {
    type: "header",
    headerName: "x-api-key",
    exampleKey: "Gus"
  },
  queryParams: [
    { name: "q", type: "string", required: true, description: "Termo de busca" },
    { name: "limit", type: "number", required: false, default: 5, description: "Quantidade de resultados retornados" }
  ]
};
