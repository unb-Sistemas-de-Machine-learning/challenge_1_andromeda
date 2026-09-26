from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from news_analysis.api.dependencies import get_analyzer, get_repository, get_settings
from news_analysis.api.schemas import AnalysisRequest, AnalysisResponse
from news_analysis.config import Settings
from news_analysis.pipeline.analyzer import NewsAnalyzer
from news_analysis.pipeline.errors import AnalysisStatus, HTTP_STATUS_BY_ANALYSIS_STATUS
from news_analysis.pipeline.models import ErrorInfo, model_to_dict
from news_analysis.storage.audit_repository import AuditRepository

app = FastAPI(title="News Analysis API", version="0.1.0")


INDEX_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Analisador de Noticias</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #5d6d7e;
      --line: #d7dde5;
      --good: #1f7a4d;
      --warn: #9a5b00;
      --bad: #a03131;
      --accent: #2457c5;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 24px;
    }
    h1 {
      font-size: 28px;
      line-height: 1.15;
      margin: 0 0 8px;
      letter-spacing: 0;
    }
    p { margin: 0; }
    .muted { color: var(--muted); }
    .api-link {
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      white-space: nowrap;
    }
    .status-line {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 14px;
    }
    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--warn);
    }
    .dot.ready { background: var(--good); }
    form {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 14px;
      font-weight: 700;
    }
    input {
      width: 100%;
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 12px;
      font: inherit;
    }
    button {
      align-self: end;
      min-height: 44px;
      border: 0;
      border-radius: 6px;
      padding: 0 18px;
      background: var(--accent);
      color: white;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled { opacity: .65; cursor: progress; }
    .grid {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 16px;
      align-items: start;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    .score {
      display: grid;
      gap: 8px;
    }
    .score-number {
      font-size: 54px;
      line-height: 1;
      font-weight: 800;
      letter-spacing: 0;
    }
    .badge {
      display: inline-flex;
      width: fit-content;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 13px;
      font-weight: 700;
      background: #eef2f8;
    }
    .badge.good { color: var(--good); background: #e8f5ee; }
    .badge.warn { color: var(--warn); background: #fff3df; }
    .badge.bad { color: var(--bad); background: #fdeaea; }
    dl {
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 8px 12px;
      margin: 14px 0 0;
      font-size: 14px;
    }
    dt { color: var(--muted); }
    dd { margin: 0; overflow-wrap: anywhere; }
    .criteria {
      display: grid;
      gap: 12px;
    }
    .criterion {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .criterion h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }
    .criterion-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      font-size: 14px;
    }
    .cell span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 3px;
    }
    ul {
      margin: 12px 0 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 14px;
    }
    .error {
      border-color: #f0b7b7;
      background: #fff7f7;
      color: var(--bad);
    }
    .empty {
      color: var(--muted);
      text-align: center;
      padding: 42px 20px;
    }
    @media (max-width: 820px) {
      header, form, .grid, .criterion-grid { grid-template-columns: 1fr; }
      header { display: grid; }
      .api-link { white-space: normal; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Analisador de confiabilidade de noticias</h1>
        <p class="muted">Cole um link de noticia para receber uma analise rastreavel dos criterios disponiveis.</p>
        <p id="config-status" class="status-line"><span class="dot"></span><span>Verificando chave de fact-check...</span></p>
      </div>
      <a class="api-link" href="/docs">API docs</a>
    </header>

    <form id="analysis-form">
      <label>
        Link da noticia
        <input id="url" name="url" type="url" placeholder="https://..." required>
      </label>
      <button id="submit" type="submit">Analisar</button>
    </form>

    <section id="result" class="empty panel">A analise aparecera aqui.</section>
  </main>

  <script>
    const form = document.querySelector("#analysis-form");
    const result = document.querySelector("#result");
    const button = document.querySelector("#submit");
    const configStatus = document.querySelector("#config-status");

    refreshConfigStatus();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      button.disabled = true;
      button.textContent = "Analisando...";
      result.className = "empty panel";
      result.textContent = "Buscando noticia, executando criterios e montando explicacao.";

      try {
        const response = await fetch("/analyses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: document.querySelector("#url").value,
            user_id: "web-user"
          })
        });
        const payload = await response.json();
        if (!response.ok) {
          renderError(payload);
        } else {
          renderAnalysis(payload);
        }
      } catch (error) {
        renderError({ error: { message: "Nao foi possivel conectar ao servico local." } });
      } finally {
        button.disabled = false;
        button.textContent = "Analisar";
      }
    });

    function renderError(payload) {
      const message = payload?.error?.message || "Nao foi possivel concluir a analise.";
      const code = payload?.error?.code || payload?.status || "ERRO";
      result.className = "panel error";
      result.innerHTML = `<strong>${escapeHtml(code)}</strong><p>${escapeHtml(message)}</p>`;
    }

    async function refreshConfigStatus() {
      try {
        const response = await fetch("/config");
        const config = await response.json();
        const dot = configStatus.querySelector(".dot");
        const text = configStatus.querySelector("span:last-child");
        if (config.fact_check_api_key_configured) {
          dot.classList.add("ready");
          text.textContent = "Google Fact Check API configurada";
        } else {
          dot.classList.remove("ready");
          text.textContent = "Google Fact Check API sem chave: crie .env ou defina FACTCHECK_API_KEY";
        }
      } catch (error) {
        configStatus.querySelector("span:last-child").textContent = "Nao foi possivel verificar configuracao";
      }
    }

    function renderAnalysis(data) {
      const score = data.final?.score;
      const level = score === null || score === undefined ? "Indisponivel" : scoreLabel(score);
      const badgeClass = score === null || score === undefined ? "warn" : score >= 70 ? "good" : score >= 40 ? "warn" : "bad";
      result.className = "grid";
      result.innerHTML = `
        <aside class="panel score">
          <span class="badge ${badgeClass}">${level}</span>
          <div class="score-number">${score === null || score === undefined ? "--" : Math.round(score)}</div>
          <p class="muted">Indice operacional de confiabilidade</p>
          <dl>
            <dt>Cobertura</dt><dd>${data.final?.coverage ?? 0}%</dd>
            <dt>Status</dt><dd>${escapeHtml(data.status)}</dd>
            <dt>Titulo</dt><dd>${escapeHtml(data.article?.title || "Nao extraido")}</dd>
            <dt>URL final</dt><dd>${escapeHtml(data.article?.final_url || data.input?.url || "")}</dd>
            <dt>Versao</dt><dd>${escapeHtml(data.pipeline_version?.id || "")}</dd>
          </dl>
          <ul>${(data.limitations || []).map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </aside>
        <section class="panel criteria">
          ${criterionCard("Checagem publicada", data.criteria?.source_credibility)}
          ${criterionCard("Estilo de escrita", data.criteria?.writing_style)}
          ${reservedCard(data.criteria?.factual_claims)}
        </section>
      `;
    }

    function criterionCard(title, criterion) {
      if (!criterion) return "";
      return `
        <article class="criterion">
          <h3>${escapeHtml(title)}</h3>
          <div class="criterion-grid">
            <div class="cell"><span>Disponivel</span>${criterion.available ? "Sim" : "Nao"}</div>
            <div class="cell"><span>Score</span>${formatScore(criterion.score)}</div>
            <div class="cell"><span>Peso efetivo</span>${formatWeight(criterion.effective_weight)}</div>
            <div class="cell"><span>Contribuicao</span>${formatScore100(criterion.contribution)}</div>
          </div>
          ${criterion.qualitative_state ? `<ul><li>${escapeHtml(criterion.qualitative_state)}: sinal de escrita, nao veredito factual.</li></ul>` : ""}
          ${criterion.query ? `<ul><li>Consulta usada: ${escapeHtml(criterion.query)}</li></ul>` : ""}
          ${criterion.error ? `<ul><li>${escapeHtml(criterion.error.message)}</li></ul>` : ""}
          ${attemptsList(criterion)}
        </article>
      `;
    }

    function attemptsList(criterion) {
      const attempts = criterion?.error?.details?.attempted_queries || [];
      if (!attempts.length) return "";
      return `<ul><li>Tentativas de busca:</li>${attempts.slice(0, 5).map(query => `<li>${escapeHtml(query)}</li>`).join("")}</ul>`;
    }

    function reservedCard(criterion) {
      if (!criterion) return "";
      return `
        <article class="criterion">
          <h3>Checagem factual por alegacoes</h3>
          <div class="criterion-grid">
            <div class="cell"><span>Status</span>${escapeHtml(criterion.status)}</div>
            <div class="cell"><span>Modelo planejado</span>${escapeHtml(criterion.planned_model)}</div>
            <div class="cell"><span>Entra no indice</span>Nao</div>
            <div class="cell"><span>Score</span>--</div>
          </div>
        </article>
      `;
    }

    function scoreLabel(score) {
      if (score >= 70) return "Confiabilidade mais alta";
      if (score >= 40) return "Confiabilidade intermediaria";
      return "Confiabilidade baixa";
    }
    function formatScore(value) {
      return value === null || value === undefined ? "--" : Number(value).toFixed(2);
    }
    function formatScore100(value) {
      return value === null || value === undefined ? "--" : Number(value).toFixed(1);
    }
    function formatWeight(value) {
      return value === null || value === undefined ? "--" : `${Math.round(Number(value) * 100)}%`;
    }
    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }
  </script>
</body>
</html>
"""


class InMemoryRateLimiter:
    def __init__(self):
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        window = now - 60
        hits = self._hits[key]
        while hits and hits[0] <= window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = InMemoryRateLimiter()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    return INDEX_HTML


@app.get("/config")
def config_status(settings: Settings = Depends(get_settings)):
    return {"fact_check_api_key_configured": bool(settings.factcheck_api_key)}


@app.post("/analyses", response_model=AnalysisResponse)
def create_analysis(
    request: AnalysisRequest,
    analyzer: NewsAnalyzer = Depends(get_analyzer),
    settings: Settings = Depends(get_settings),
):
    user_key = request.user_id or request.url
    if not rate_limiter.allow(user_key, settings.rate_limit_per_minute):
        error = ErrorInfo(
            code=AnalysisStatus.RATE_LIMITED.value,
            message="Rate limit reached: only 10 analysis requests per user are accepted per minute.",
            retryable=True,
            details={"limit_per_minute": settings.rate_limit_per_minute},
        )
        return JSONResponse(
            status_code=429,
            content={"status": AnalysisStatus.RATE_LIMITED.value, "error": model_to_dict(error)},
        )
    analysis = analyzer.analyze(request.url)
    status_code = HTTP_STATUS_BY_ANALYSIS_STATUS.get(AnalysisStatus(analysis.status), 200)
    if status_code != 200:
        return JSONResponse(
            status_code=status_code,
            content={"status": analysis.status, "error": model_to_dict(analysis.error)},
        )
    return analysis


@app.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str, repository: AuditRepository = Depends(get_repository)):
    payload = repository.get(analysis_id)
    if payload is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": AnalysisStatus.CRITERION_UNAVAILABLE.value,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Analysis not found.",
                    "retryable": False,
                },
            },
        )
    return payload
