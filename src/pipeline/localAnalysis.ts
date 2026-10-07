import { searchFactChecks, type FactCheckResponse } from "./factCheckClient";
import { classifyWriting } from "./bertimbau";

export type LocalAnalysis = {
  article: { title: string; publisher: string; final_url: string };
  explanation: { status: "SUCCESS"; text: string };
};
export type ArticleCandidate = { title: string; url: string; publisher: string };

type Article = { title: string; text: string; finalUrl: string; publisher: string };
type AtlasSnapshot = { domains: string[] };
let atlasPromise: Promise<AtlasSnapshot> | undefined;

function clean(value: string): string { return value.replace(/\s+/g, " ").trim(); }

async function loadArticle(url: string): Promise<Article> {
  const response = await fetch(url, { signal: AbortSignal.timeout(20_000) });
  if (!response.ok) throw new Error("Não foi possível abrir a reportagem no Android.");
  const html = await response.text();
  const document = new DOMParser().parseFromString(html, "text/html");
  const title = clean(document.querySelector('meta[property="og:title"]')?.getAttribute("content") || document.title);
  const text = clean(Array.from(document.querySelectorAll("article, main, p")).map((node) => node.textContent || "").join(" "));
  const finalUrl = response.url || url;
  const publisher = new URL(finalUrl).hostname.replace(/^www\./, "");
  if (!title || text.length < 120) throw new Error("A reportagem não pôde ser extraída para análise.");
  return { title, text, finalUrl, publisher };
}

async function loadAtlas(): Promise<AtlasSnapshot> {
  atlasPromise ||= fetch("/data/atlas-domains.json").then(async (response) => {
    if (!response.ok) return { domains: [] };
    return await response.json() as AtlasSnapshot;
  }).catch(() => ({ domains: [] }));
  return atlasPromise;
}

async function sourceSignals(article: Article): Promise<{ available: boolean; positives: string[]; negatives: string[] }> {
  const domain = article.publisher.toLowerCase();
  const positives: string[] = [];
  const atlas = await loadAtlas();
  if (atlas.domains.includes(domain)) positives.push("o veículo foi encontrado no Atlas da Notícia");
  if (domain.endsWith(".gov.br")) positives.push("o site verificado é um site oficial do governo");
  if (article.finalUrl.startsWith("https://")) positives.push("a reportagem usa HTTPS");
  return { available: positives.length > 0, positives, negatives: [] };
}

function factText(facts: FactCheckResponse): { available: boolean; detail: string } {
  const reviews = (facts.claims || []).flatMap((claim) => claim.claimReview || []).filter((review) => review.publisher?.name);
  if (!reviews.length) return { available: false, detail: "Não há checagem factual disponível." };
  const ratings = reviews.map((review) => `${review.publisher?.name}: ${review.textualRating || "avaliação publicada"}`);
  return { available: true, detail: `Foram encontradas checagens publicadas: ${ratings.slice(0, 3).join("; ")}.` };
}

export async function analyzeLocally(url: string): Promise<LocalAnalysis> {
  const article = await loadArticle(url);
  const source = await sourceSignals(article);
  // O único processamento remoto é a consulta ao proxy de Fact Check.
  const facts = await searchFactChecks(article.title);
  const factual = factText(facts);
  const writing = await classifyWriting(article.text);
  const sourceText = source.available
    ? `Pontos positivos: ${source.positives.join("; ")}.`
    : "O veículo desta notícia não pôde ser consultado na base de veículos.";
  return {
    article: { title: article.title, publisher: article.publisher, final_url: article.finalUrl },
    explanation: {
      status: "SUCCESS",
      text: `Confiabilidade ${factual.available ? "a ser conferida" : "parcial"}. ${factual.detail} A avaliação considera ${writing.available ? "a credibilidade da fonte e o estilo de escrita" : "sinais locais da fonte"}; não confirma todos os fatos da notícia. ${sourceText}${writing.available ? ` Sinal de escrita local: ${writing.label || "classificado"}.` : " O modelo de escrita local está indisponível neste dispositivo."}`,
    },
  };
}

export async function searchNewsByTitle(title: string): Promise<ArticleCandidate[]> {
  const response = await fetch(`https://api.gdeltproject.org/api/v2/doc/doc?query=${encodeURIComponent(title)}&mode=artlist&format=json&maxrecords=20&sort=datedesc`, { signal: AbortSignal.timeout(15_000) });
  if (!response.ok) throw new Error("Não foi possível buscar notícias pelo título.");
  const payload = await response.json() as { articles?: Array<{ title?: string; url?: string; domain?: string }> };
  return (payload.articles || []).filter((item): item is { title: string; url: string; domain?: string } => !!item.title && !!item.url && /^https?:\/\//i.test(item.url)).map((item) => ({ title: item.title, url: item.url, publisher: item.domain || new URL(item.url).hostname })).slice(0, 8);
}
