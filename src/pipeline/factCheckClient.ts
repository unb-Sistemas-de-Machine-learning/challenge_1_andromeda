export type FactCheckReview = {
  claimReview?: { publisher?: { name?: string; site?: string }; textualRating?: string; title?: string; url?: string }[];
};

export type FactCheckResponse = { claims?: FactCheckReview[] };

export async function searchFactChecks(query: string): Promise<FactCheckResponse> {
  const endpoint = import.meta.env.VITE_FACTCHECK_API_URL?.trim();
  if (!endpoint) throw new Error("O endpoint de Fact Check não foi configurado.");
  const proxyToken = import.meta.env.VITE_FACTCHECK_PROXY_TOKEN?.trim();
  if (!proxyToken) throw new Error("O token de comunicação com o backend não foi configurado.");
  const response = await fetch(`${endpoint.replace(/\/+$/, "")}/fact-check`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${proxyToken}` },
    body: JSON.stringify({ query, pageSize: 10, languageCode: "pt" }),
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) throw new Error("O serviço de Fact Check não respondeu.");
  return await response.json() as FactCheckResponse;
}
