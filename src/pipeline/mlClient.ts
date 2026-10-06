// Etapa 3 do pipeline: envio do conteúdo já validado e filtrado para o modelo
// de ML. A lógica de predição e os status pertencem ao serviço de ML; aqui só
// fica o contrato de comunicação e a adaptação da resposta para a interface.
//
// Configuração: defina VITE_ML_API_URL (ex.: em .env.local) com o endpoint que
// recebe um POST JSON. Sem essa variável, o protótipo usa a simulação local
// de src/analysis.ts.

import { analyzeNews, type Analysis, type Outcome } from "../analysis";

// Corpo enviado para a ML. "url" é enviado como string absoluta (https://…).
export type MlRequest = {
  type: "text" | "url";
  content: string;
};

export type MlOptions = { simulateFailure?: boolean; signal?: AbortSignal };

const REQUEST_TIMEOUT_MS = 30_000;
const OUTCOMES: Outcome[] = ["supported", "context", "insufficient"];

export class MlServiceError extends Error {}

// Ponto único de ajuste quando o formato de resposta da ML for definido.
// Hoje espera um objeto compatível com o tipo Analysis.
export function toAnalysis(payload: unknown, request: MlRequest): Analysis {
  const data = payload as Partial<Analysis> | null;
  if (!data || !OUTCOMES.includes(data.outcome as Outcome)) {
    throw new MlServiceError("Resposta da ML em formato inesperado");
  }
  return {
    outcome: data.outcome as Outcome,
    claim: data.claim ?? request.content,
    title: data.title ?? "",
    explanation: data.explanation ?? [],
    sources: data.sources ?? [],
    next: data.next ?? "",
  };
}

async function postToMl(
  endpoint: string,
  request: MlRequest,
  signal?: AbortSignal,
): Promise<Analysis> {
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
  if (!response.ok) {
    throw new MlServiceError(`ML respondeu com status ${response.status}`);
  }
  return toAnalysis(await response.json(), request);
}

export function sendToMl(
  request: MlRequest,
  options: MlOptions = {},
): Promise<Analysis> {
  const endpoint = import.meta.env.VITE_ML_API_URL;
  if (endpoint && !options.simulateFailure) {
    return postToMl(endpoint, request, options.signal);
  }
  return analyzeNews(request.content, options);
}
