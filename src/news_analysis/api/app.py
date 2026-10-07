from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from news_analysis.api.dependencies import get_analyzer, get_atlas_repository, get_repository, get_settings
from news_analysis.atlas_sync import atlas_status
from news_analysis.storage.atlas_repository import AtlasRepository
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
      grid-template-columns: 1fr;
      gap: 12px;
    }
    .criterion, .analysis-card {
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
      header, form, .grid, .criteria, .criterion-grid { grid-template-columns: 1fr; }
      header { display: grid; }
      .api-link { white-space: normal; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Analisador de confiabilidade de notícias</h1>
        <p class="muted">Cole um link de notícia para receber uma análise rastreável dos critérios disponíveis.</p>
        <p id="config-status" class="status-line"><span class="dot"></span><span>Verificando chave de fact-check...</span></p>
        <p id="atlas-status" class="muted">Verificando base do Atlas...</p>
      </div>
      <a class="api-link" href="/docs">Documentação da API</a>
    </header>

    <form id="analysis-form">
      <label>
        Link da notícia
        <input id="url" name="url" type="url" placeholder="https://..." required>
      </label>
      <button id="submit" type="submit">Analisar</button>
      <label>
        Afirmação a checar (opcional)
        <input id="claim" name="claim" type="text" minlength="3" maxlength="500" placeholder="Uma afirmação verificável; sem preencher, usamos o título">
      </label>
    </form>

    <section id="result" class="empty panel">A análise aparecerá aqui.</section>
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
      result.textContent = "Buscando notícia, executando critérios e montando explicação.";

      try {
        const response = await fetch("/analyses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: document.querySelector("#url").value,
            user_id: "web-user",
            claim: document.querySelector("#claim").value.trim() || null
          })
        });
        const payload = await response.json();
        if (!response.ok) {
          renderError(payload);
        } else {
          renderAnalysis(payload);
        }
      } catch (error) {
        renderError({ error: { message: "Não foi possível conectar ao serviço local." } });
      } finally {
        await refreshConfigStatus();
        button.disabled = false;
        button.textContent = "Analisar";
      }
    });

    function renderError(payload) {
      const message = payload?.error?.message || "Não foi possível concluir a análise.";
      const code = payload?.error?.code || payload?.status || "ERRO";
      result.className = "panel error";
      result.innerHTML = `<strong>${escapeHtml(code)}</strong><p>${escapeHtml(message)}</p>`;
    }

    async function refreshConfigStatus() {
      try {
        const response = await fetch("/config");
        const config = await response.json();
        const atlasStates = {disabled: 'desabilitado', missing: 'sem base local; a próxima análise tentará atualizar', fresh: 'base atualizada', stale: 'atualização pendente; a próxima análise tentará atualizar', expired: 'base expirada; a próxima análise tentará atualizar'};
        document.querySelector('#atlas-status').textContent = `Atlas da Notícia: ${atlasStates[config.atlas_status] || 'estado indisponível'}${config.atlas_last_success_at ? ` · Última atualização: ${config.atlas_last_success_at}` : ''}`;
        const dot = configStatus.querySelector(".dot");
        const text = configStatus.querySelector("span:last-child");
        if (config.fact_check_status === "render_ready") {
          dot.classList.add("ready");
          text.textContent = "Conexão com Render configurada; disponibilidade verificada na análise";
        } else if (config.fact_check_status === "local_key_ready") {
          dot.classList.add("ready");
          text.textContent = "Google Fact Check API configurada";
        } else {
          dot.classList.remove("ready");
          text.textContent = config.fact_check_status === "missing_proxy_token"
            ? "Google Fact Check via Render: configure FACTCHECK_PROXY_TOKEN na aplicação"
            : "Google Fact Check indisponível: configure a chave ou o serviço remoto";
        }
      } catch (error) {
        configStatus.querySelector("span:last-child").textContent = "Não foi possível verificar a configuração";
      }
    }

    function renderAnalysis(data) {
      const score = data.final?.score;
      const historicalSource = data.criteria?.source_credibility;
      const legacyFacts = !data.criteria?.verifiable_facts && historicalSource?.reviews_count !== undefined && !historicalSource?.signals;
      const factCriterion = data.criteria?.verifiable_facts ?? (legacyFacts ? historicalSource : null);
      const metadataSource = historicalSource?.signals ? historicalSource : null;
      const sourceAvailable = data.criteria?.credibility?.score_fonte != null;
      const writingOnly = data.criteria?.writing_style?.available && !factCriterion?.available && !sourceAvailable && !metadataSource?.available;
      const noFactCheck = !factCriterion?.available;
      const level = score === null || score === undefined ? "Indisponível" : scoreLabel(score);
      const badgeClass = score === null || score === undefined || noFactCheck ? "warn" : score > 85 ? "good" : score > 40 ? "warn" : "bad";
      result.className = "grid";
      result.innerHTML = `
        <aside class="panel score">
          <span class="badge ${badgeClass}">${level}</span>
          <div class="score-number">${score === null || score === undefined ? "--" : Math.round(score)}</div>
          <p class="muted">Índice operacional de confiabilidade</p>
          ${noFactCheck ? `<p><strong>Sem checagem factual disponível.</strong> ${sourceAvailable && data.criteria?.writing_style?.available ? 'A média considera a credibilidade da fonte e o estilo de escrita.' : sourceAvailable ? 'A média considera apenas a credibilidade da fonte.' : writingOnly ? 'A média considera apenas o estilo de escrita.' : 'Não há critérios disponíveis para uma nota.'} Esta avaliação não confirma os fatos da notícia.</p>` : ""}
          <p class="muted">F = checagem factual; C = credibilidade da fonte; W = estilo de escrita. Cada critério varia de 0 a 1 na fórmula.</p>
          <dl>
            <dt>Cobertura</dt><dd>${data.final?.coverage ?? 0}%</dd>
            <dt>Fórmula</dt><dd>${escapeHtml(data.final?.formula || "Não informada")}</dd>
            ${data.final?.score_before_veto != null ? `<dt>Média antes do veto</dt><dd>${formatScore100(data.final.score_before_veto)}</dd>` : ''}
            <dt>Status</dt><dd>${escapeHtml(statusLabel(data.status))}</dd>
            <dt>ID da análise</dt><dd>${escapeHtml(data.id || "Não informado")}</dd>
            <dt>Título</dt><dd>${escapeHtml(data.article?.title || "Não extraído")}</dd>
            <dt>URL final</dt><dd>${escapeHtml(data.article?.final_url || data.input?.url || "")}</dd>
            <dt>Versão</dt><dd>${escapeHtml(data.pipeline_version?.id || "")}</dd>
          </dl>
          <ul>${(data.limitations || []).map(item => `<li>${escapeHtml(limitationLabel(item))}</li>`).join("")}</ul>
        </aside>
        <section class="panel criteria">
          ${explanationCard(data)}
          ${factCriterionCard(factCriterion, legacyFacts, data)}
          ${criterionCard("Estilo de escrita", data.criteria?.writing_style)}
          ${sourceAnalysisCard(data.criteria?.credibility, data.criteria?.credibility_evidence, metadataSource, data.final)}
        </section>
      `;
    }

    function explanationCard(data) {
      const title = 'Por que esta notícia recebeu esta avaliação?';
      const explanation = data.explanation || {};
      const score = data.final?.score;
      const fact = data.criteria?.verifiable_facts;
      const writing = data.criteria?.writing_style;
      const source = data.criteria?.credibility;
      const parts = [score == null ? 'Avaliação de confiabilidade indisponível.' : `${scoreLabel(score)}.`];
      const factual = {SUPPORTED: 'Há evidências favoráveis à afirmação avaliada.', REFUTED: 'Há evidências contrárias à afirmação avaliada.', MIXED: 'As evidências sobre a afirmação avaliada são divergentes.', MATCHED_UNSCORED: 'Há checagens relacionadas, mas faltam dados para uma conclusão.', UNAVAILABLE: 'Não há checagem factual disponível.'};
      parts.push(factual[fact?.evidence_status] || factual.UNAVAILABLE);
      if (!fact?.available && writing?.available && source?.score_fonte != null) parts.push('A avaliação considera a credibilidade da fonte e o estilo de escrita; não confirma os fatos da notícia.');
      else if (!fact?.available && writing?.available) parts.push('A avaliação considera apenas o estilo de escrita e não confirma os fatos da notícia.');
      else if (!fact?.available && source?.score_fonte != null) parts.push('A avaliação considera apenas a credibilidade da fonte e não confirma os fatos da notícia.');
      const recognition = source?.criterios?.find(item => item.nome === 'veiculo_reconhecido');
      if (recognition?.status === 'indisponivel') parts.push('O veículo desta notícia não pôde ser consultado na base de veículos.');
      else if (recognition?.status === 'negativo') parts.push('O veículo desta notícia não foi encontrado nas bases de veículos consultadas.');
      else if (recognition?.status === 'ok') {
        const foundInAtlas = data.criteria?.credibility_evidence?.evidence?.some(item => item.source === 'atlas');
        parts.push(foundInAtlas ? 'O veículo desta notícia foi encontrado no Atlas da Notícia.' : 'O veículo desta notícia foi encontrado na base de veículos.');
      }
      const tld = source?.criterios?.find(item => item.nome === 'tld_institucional');
      if (tld?.status === 'ok') parts.push(source?.dominio?.endsWith('.gov.br') ? 'Ponto positivo: o site verificado é um site oficial do governo.' : 'Ponto positivo: o site verificado possui um domínio institucional oficial.');
      const summary = parts.join(' ');
      const evidence = explanation.evidence_example_url && /^https?:\\/\\//i.test(explanation.evidence_example_url)
        ? `<p><strong>Exemplo de checagem:</strong> ${escapeHtml(explanation.evidence_example_publisher || 'Fonte não informada')} · ${escapeHtml(explanation.evidence_example_rating || 'avaliação não informada')} · <a href="${escapeHtml(explanation.evidence_example_url)}" target="_blank" rel="noopener noreferrer">abrir evidência</a></p>`
        : '';
      return `<article class="analysis-card explanation"><h3>${title}</h3><p>${escapeHtml(summary)}</p>${evidence}<small>Resumo baseado nos critérios da análise.</small></article>`;
    }

    function factCriterionCard(criterion, legacy, data) {
      const fallback = {
        available: false, status: "UNAVAILABLE", intended_weight: 0.65,
        target_claim: data.input?.claim || data.article?.title,
        error: { message: "A resposta da API não contém o critério de checagem de fatos. Reinicie o servidor e faça uma nova análise." }
      };
      return criterionCard("Checagem de fatos verificáveis", criterion || fallback, true) +
        (legacy ? `<p>Resposta no formato anterior da API. Os dados disponíveis são exibidos; reinicie o servidor para obter a afirmação selecionada e os detalhes do cálculo atual.</p>` : "");
    }

    function evidenceState(criterion) {
      const labels = {SUPPORTED: 'Evidências favoráveis', REFUTED: 'Evidências contrárias', MIXED: 'Evidências mistas ou parciais', MATCHED_UNSCORED: 'Checagem correspondente, sem nota utilizável', UNAVAILABLE: 'Sem evidência utilizável'};
      return criterion?.evidence_status ? `<p><strong>${escapeHtml(labels[criterion.evidence_status] || criterion.evidence_status)}</strong>. Síntese das checagens recuperadas para esta afirmação; não é um veredito sobre a notícia inteira.</p>` : '';
    }

    function additionalClaimEvidence(criterion) {
      if (!criterion?.additional_claims?.length) return '';
      return `<details><summary>Afirmações complementares (${criterion.additional_claims.length}) — não entram na nota</summary>
        <p>Frases candidatas selecionadas do texto, sem extração semântica. Não representam todos os fatos da notícia.</p>
        ${criterion.additional_claims.map(claim => `<section><h4>${escapeHtml(claim.target_claim)}</h4>
          ${evidenceState(claim)}${claim.search_incomplete ? '<p>Busca incompleta; as evidências obtidas foram preservadas.</p>' : ''}
          ${factCheckEvidence(claim, true)}${claim.error ? `<p>${escapeHtml(factCheckErrorMessage(claim.error))}</p>` : ''}${attemptsList(claim)}</section>`).join('')}</details>`;
    }

    function sourceAnalysisCard(source, evidence, historical, final) {
      if (!source && !historical) return `<article class="analysis-card"><h3>Credibilidade da fonte</h3><p>Sem dados de credibilidade disponíveis nesta análise.</p></article>`;
      const criteria = source?.criterios || [];
      const baseCriteria = criteria.filter(item => item.nome !== 'tld_institucional');
      const total = baseCriteria.reduce((sum, item) => sum + Number(item.maximo || 0), 0);
      const evaluated = baseCriteria.filter(item => item.status !== 'indisponivel').reduce((sum, item) => sum + Number(item.maximo || 0), 0);
      const sourceCoverage = total ? Math.round(100 * evaluated / total) : 0;
      const institutionalBonus = criteria.find(item => item.nome === 'tld_institucional' && item.status === 'ok');
      const sourceConfidence = {baixa: 'baixa', media: 'média', alta: 'alta'}[source?.confianca_fonte] || source?.confianca_fonte || 'não informada';
      const criterionNames = {veiculo_reconhecido: 'Reconhecimento do veículo', transparencia_editorial: 'Transparência editorial', idade_dominio: 'Idade do domínio', tld_institucional: 'Domínio institucional', https: 'Conexão HTTPS'};
      const criterionStatuses = {indisponivel: 'indisponível', negativo: 'não atendido', neutro: 'neutro', ok: 'atendido'};
      return `<article class="analysis-card"><h3>Credibilidade da fonte</h3>
        ${source ? `<p>${source.score_fonte == null ? 'Pontuação da fonte indisponível' : `Pontuação da credibilidade: ${escapeHtml(source.score_fonte)}/100`} · Cobertura dos sinais: ${sourceCoverage}% (${escapeHtml(sourceConfidence)})</p>
        <p>Os quatro critérios principais somam até 100 pontos. Um critério indisponível não recebe pontos, mas sua ausência não comprova baixa reputação.${institutionalBonus ? (source.score_fonte === 100 ? ' O domínio institucional oficial garantiu 100/100 para a credibilidade da fonte.' : ' O domínio institucional foi reconhecido, mas a lista de bloqueio prevaleceu.') : ''}</p>
        ${source.intended_weight != null ? `<p>Peso previsto: ${formatWeight(source.intended_weight)} · Peso efetivo: ${formatWeight(source.effective_weight)} · Contribuição para o índice: ${formatScore100(source.contribution)} pontos</p>` : ''}
        ${source.score_fonte == null ? '<p>Sem sinais suficientes para avaliar a fonte; a indisponibilidade não aplica veto.</p>' : ''}
        <p>Domínio: ${escapeHtml(source.dominio)}. Sinais da fonte não comprovam a veracidade da notícia.</p>
        <ul>${criteria.map(c => `<li>${escapeHtml(criterionNames[c.nome] || c.nome)}: ${escapeHtml(c.pontos)}/${escapeHtml(c.maximo)} — ${escapeHtml(criterionStatuses[c.status] || c.status)}. ${escapeHtml(c.detalhe)}</li>`).join("")}</ul>
        ${evidence ? `<details><summary>Origem do reconhecimento da fonte</summary>
          <p>${escapeHtml(recognitionLabel(evidence.status))} · Consulta: ${escapeHtml(evidence.checked_at)}</p>
          <ul>${(evidence.providers || []).map(p => `<li>${escapeHtml(p.source === 'atlas' ? 'Atlas da Notícia' : 'Base local')}: ${escapeHtml(recognitionLabel(p.status))} · ${escapeHtml(recognitionLabel(p.reason_code))}${p.fetched_at ? ` · Base de ${escapeHtml(p.fetched_at)}` : ''}${p.freshness === 'stale' ? ' · Atualização pendente; cópia dentro da validade' : ''}</li>`).join('')}</ul>
          <ul>${(evidence.evidence || []).map(e => `<li>${escapeHtml(e.source)}${e.atlas_id ? ` · Cadastro ${escapeHtml(e.atlas_id)}: ${escapeHtml(e.name)}` : ''}${e.resolved_url && /^https?:\\/\\//i.test(e.resolved_url) ? ` · <a href="${escapeHtml(e.resolved_url)}" target="_blank" rel="noopener noreferrer">Site registrado</a>` : ''}</li>`).join('')}</ul>
        </details>` : ''}
        ${source.veto_dominio_suspeito ? (final?.score != null ? '<p>Teto de 35 aplicado à nota final. As contribuições acima mostram a média antes do teto.</p>' : '<p>Veto da fonte identificado; não há nota final à qual aplicar o teto.</p>') : ''}
        <ul>${[...(source.flags || []), ...(source.erros || [])].map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ''}
        ${historical ? `<details><summary>Credibilidade da fonte — análise histórica</summary><p>Critério de metadados da versão anterior. Pesos, contribuições e nota foram preservados, sem recálculo.</p><ul>${historical.signals.map(s => `<li>${escapeHtml(s.label)}: ${s.passed ? 'Sim' : 'Não'} — ${escapeHtml(s.evidence)}</li>`).join('')}</ul></details>` : ''}
      </article>`;
    }

    function criterionCard(title, criterion, isFactCheck = false) {
      if (!criterion) return "";
      return `
        <article class="analysis-card criterion">
          <h3>${escapeHtml(title)}</h3>
          <div class="criterion-grid">
            <div class="cell"><span>Disponível</span>${criterion.available ? "Sim" : "Não"}</div>
            <div class="cell"><span>Status do critério</span>${escapeHtml(statusLabel(criterion.status || "Não informado"))}</div>
            <div class="cell"><span>Nota</span>${formatScore(criterion.score)}</div>
            <div class="cell"><span>Peso previsto</span>${formatWeight(criterion.intended_weight)}</div>
            <div class="cell"><span>Peso efetivo</span>${formatWeight(criterion.effective_weight)}</div>
            <div class="cell"><span>Contribuição</span>${formatScore100(criterion.contribution)}</div>
          </div>
          ${isFactCheck ? `<p><strong>Afirmação avaliada:</strong> ${escapeHtml(criterion.target_claim || "Não informada nesta resposta")}</p><p>Checagens recuperadas: ${escapeHtml(criterion.reviews_count ?? "Não informado")} · Correspondentes: ${escapeHtml(criterion.applicable_reviews_count ?? "Não informado")} · Relacionadas: ${escapeHtml(criterion.related_reviews_count ?? "Não informado")} · Usadas na nota: ${escapeHtml(criterion.scored_reviews_count ?? "Não informado")} · Agências: ${escapeHtml(criterion.publishers_count ?? "Não informado")}</p><p>Nota da afirmação selecionada; não avalia a reputação da fonte nem todos os fatos da notícia.</p>${!criterion.available ? `<p>Este critério não contribuiu para a nota. Ausência de checagens não significa verdadeiro ou falso.</p>` : ""}` : ""}
          ${criterion.qualitative_state ? `<ul><li>${escapeHtml(criterion.qualitative_state)}: sinal de escrita, não veredito factual.</li></ul>` : ""}
          ${isFactCheck ? evidenceState(criterion) : ''}
          ${criterion.search_incomplete ? '<p>Busca incompleta: houve falha em uma ou mais tentativas. Evidências já obtidas foram preservadas.</p>' : ''}
          ${criterion.model ? `<ul><li>Modelo: ${escapeHtml(criterion.model)}</li><li>Revisão: ${escapeHtml(criterion.model_version)}</li><li>Segmentos analisados: ${escapeHtml(criterion.segments_analyzed)}</li></ul>` : ""}
          ${criterion.prediction ? `<ul><li>Classe prevista pelo modelo: ${escapeHtml(classLabel(criterion.prediction.label))}</li><li>Confiança do classificador: ${formatWeight(criterion.prediction.confidence)} (não comprova veracidade)</li></ul>` : ""}
          ${criterion.segments?.length ? `<details><summary>Resultados por segmento (${criterion.segments.length})</summary><ul>${criterion.segments.map(segment => `<li>Segmento ${escapeHtml(segment.index + 1)}: ${escapeHtml(segment.character_count)} caracteres · ${escapeHtml(segment.token_count ?? "Não informado")} tokens · Classe ${escapeHtml(classLabel(segment.label))} · Confiança ${formatWeight(segment.confidence)} · Nota ${formatScore(segment.writing_score)}</li>`).join("")}</ul></details>` : ""}
          ${criterion.query ? `<ul><li>Consulta usada: ${escapeHtml(criterion.query)}</li></ul>` : ""}
          ${criterion.scope ? `<p>${escapeHtml(criterion.scope)}</p>` : ""}
          ${criterion.publishers_count ? `<p>Regra: média das notas únicas por agência, seguida da média entre agências com pesos iguais.</p><ul>${Object.entries(criterion.publisher_scores || {}).map(([agency, score]) => `<li>${escapeHtml(agency)}: ${formatScore(score)} na afirmação avaliada</li>`).join("")}</ul>` : ""}
          ${criterion.conflicting_verdicts ? `<p>Há vereditos divergentes. A média não representa consenso.</p>` : ""}
          ${criterion.search_truncated ? `<p>Busca limitada a três páginas por consulta; podem existir outras checagens.</p>` : ""}
          ${isFactCheck && !criterion.reviews?.length ? `<p>Nenhuma evidência de checagem retornada nesta análise.</p>` : ""}
          ${factCheckEvidence(criterion)}
          ${criterion.error ? `<ul><li>Motivo: ${escapeHtml(factCheckErrorMessage(criterion.error))}</li><li>Código: ${escapeHtml(criterion.error.code || "Não informado")}</li></ul>` : ""}
          ${attemptsList(criterion)}
          ${isFactCheck ? additionalClaimEvidence(criterion) : ""}
        </article>
      `;
    }

    function attemptsList(criterion) {
      const recorded = criterion?.search_attempts || [];
      const attempts = recorded.length ? recorded : (criterion?.error?.details?.attempted_queries || []).map(query => ({query}));
      if (!attempts.length) return "";
      return `<details open><summary>Consultas realizadas (${attempts.length})</summary><ul>${attempts.map(attempt => `<li>${escapeHtml(attempt.query)}${attempt.claims_count !== undefined ? ` — ${escapeHtml(attempt.claims_count)} afirmações retornadas` : ""}${attempt.status ? ` · ${escapeHtml(statusLabel(attempt.status))}` : ''}${attempt.error?.http_status ? ` · HTTP ${escapeHtml(attempt.error.http_status)}` : ''}</li>`).join("")}</ul></details>`;
    }

    function factCheckErrorMessage(error) {
      if (error.details?.reason === "partial_search_failure" &&
          error.details?.errors?.some(item => item.http_status === 503)) {
        return "O servidor de checagem retornou HTTP 503. Abra a URL do Render para verificar as variáveis ausentes indicadas em missing_env.";
      }
      const messages = {
        missing_api_key: "A chave do Google Fact Check não está configurada.",
        missing_proxy_token: "O token de acesso ao servidor Render não está configurado na aplicação.",
        no_reviews_returned: "O Google Fact Check não retornou checagens publicadas para as consultas realizadas.",
        related_reviews_only: "Foram encontradas checagens relacionadas, mas a equivalência da afirmação não foi confirmada. Consulte as evidências.",
        no_applicable_reviews: "Foram encontradas checagens, mas nenhuma correspondeu à afirmação selecionada.",
        no_normalizable_ratings: "As checagens correspondentes têm vereditos sem conversão na escala do projeto.",
        missing_publisher_identity: "As checagens correspondentes não identificam a agência responsável.",
        no_claim_candidate: "Não foi possível selecionar uma afirmação candidata. Informe a afirmação que deseja consultar.",
        partial_search_failure: "Parte da busca falhou. As evidências já obtidas foram preservadas."
      };
      return messages[error.details?.reason] || error.message;
    }

    function factCheckEvidence(criterion, supplemental = false) {
      if (!criterion.reviews?.length) return "";
      return `<ul>${criterion.reviews.map(review => {
        const url = review.review_url || "";
        const safeLink = /^https?:\\/\\//i.test(url) ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Abrir checagem</a>` : "";
        const reasons = {claim_mismatch: "correspondência não estabelecida", claim_related: "conteúdo relacionado, insuficiente para pontuar", unmapped_rating: "veredito não mapeado", missing_publisher_identity: "agência não identificada", duplicate_review: "checagem duplicada"};
        const matches = {SAME_CLAIM: 'Forte — mesma afirmação pelas regras do projeto', RELATED: 'Relacionada — requer conferência, fora da nota', DIFFERENT: 'Correspondência não estabelecida'};
        const matchReasons = {missing_claim_text: 'Texto da afirmação ausente', numeric_mismatch: 'Números ou datas diferentes', location_mismatch: 'Localidades diferentes', polarity_or_action_mismatch: 'Negação, ação ou desmentido não correspondem', attribution_missing: 'Autoria da fala não confirmada nos dois textos', attribution_mismatch: 'Autoria da fala diferente', negation_scope_mismatch: 'A negação se refere a partes diferentes da fala', exact_normalized: 'Textos equivalentes após normalização controlada', controlled_lexical_match: 'Sobreposição após equivalências controladas e filtros', insufficient_proposition_overlap: 'Sobreposição insuficiente para confirmar a mesma afirmação'};
        const matching = review.match_classification ? `<p>Correspondência: ${escapeHtml(matches[review.match_classification])}. ${escapeHtml(matchReasons[review.match_reason] || review.match_reason || '')}${review.match_similarity != null ? ` · Sobreposição lexical: ${formatWeight(review.match_similarity)} (não é probabilidade nem confiança calibrada)` : ''}</p>` : '';
        const context = review.rating_interpretation === 'CONTEXT' ? '<p>Avaliação de contexto: não significa que a fala nunca ocorreu. A nota 0,25 é uma convenção do projeto para esse rótulo.</p>' : '';
        const inclusion = review.included_in_score === undefined ? "Inclusão na nota não informada neste resultado" : review.included_in_score ? (supplemental ? "Usada na síntese complementar, fora da nota final" : "Incluída na nota") : `Excluída: ${escapeHtml(reasons[review.exclusion_reason] || review.exclusion_reason || "Não aplicável")}`;
        return `<li><strong>${escapeHtml(review.claim || "Afirmação ausente")}</strong><br>Agência: ${escapeHtml(review.publisher_name || review.publisher_key || "Não informada")} · Veredito: ${escapeHtml(review.textual_rating || "Não informado")} · Nota: ${formatScore(review.normalized_value)}<br>Data: ${escapeHtml(review.review_date || "Não informada")} · ${inclusion} ${safeLink}${matching}${context}</li>`;
      }).join("")}</ul>`;
    }

    function scoreLabel(score) {
      if (score > 85) return "Confiabilidade alta";
      if (score > 70) return "Confiabilidade média";
      if (score > 40) return "Confiabilidade baixa";
      return "Confiabilidade baixíssima";
    }
    function statusLabel(status) {
      return {SUCCESS: 'Concluída', EXECUTED: 'Executado', UNAVAILABLE: 'Indisponível', ERROR: 'Erro', FAILED: 'Falhou', success: 'concluída', error: 'erro', unavailable: 'indisponível'}[status] || status;
    }
    function classLabel(label) {
      return {True: 'sinal favorável', Fake: 'sinal de alerta', False: 'sinal de alerta'}[label] || label;
    }
    function recognitionLabel(value) {
      return {matched: 'veículo encontrado', not_found: 'veículo não encontrado', unavailable: 'indisponível', ambiguous: 'identificação ambígua', available: 'disponível', no_snapshot: 'base local ausente', incomplete_identity_coverage: 'cadastro parcial', ok: 'sem falha', expired_snapshot: 'base expirada', atlas_storage_unavailable: 'erro ao ler a base local', local_base_unavailable: 'base local indisponível'}[value] || value;
    }
    function limitationLabel(item) {
      const legacy = {
        'The final index is an operational combination of executed criteria, not a probability that the news is true or false.': 'O índice combina os critérios avaliados; não representa a probabilidade de a notícia ser verdadeira ou falsa.',
        'Writing-style predictions are model signals and not factual verdicts.': 'O resultado do modelo de escrita é um sinal de estilo, não um veredito factual.',
        'Unavailable evidence is reported and excluded from scoring rather than treated as negative evidence.': 'Critérios indisponíveis são informados e não são tratados como evidência negativa.',
        'Both current criteria were executed.': 'Os critérios atuais de checagem factual e estilo de escrita foram avaliados.',
        'Only the fact-checking criterion contributed to the final index.': 'Apenas a checagem factual contribuiu para o índice final.',
        'Only the writing-style criterion contributed to the final index.': 'Apenas o estilo de escrita contribuiu para o índice final.',
        'No current criteria contributed to the final index.': 'Nenhum critério atual contribuiu para o índice final.'
      };
      return legacy[item] || item;
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
def config_status(settings: Settings = Depends(get_settings), atlas: AtlasRepository = Depends(get_atlas_repository)):
    state = atlas_status(atlas, settings.credibility_config().atlas)
    fact_check_status = ("render_ready" if settings.factcheck_backend_url and settings.factcheck_proxy_token else
                         "missing_proxy_token" if settings.factcheck_backend_url else
                         "local_key_ready" if settings.factcheck_api_key else "missing_config")
    return {"fact_check_api_key_configured": fact_check_status in {"render_ready", "local_key_ready"},
            "fact_check_status": fact_check_status,
            'atlas_enabled': state['enabled'], 'atlas_status': state['status'],
            'atlas_last_success_at': state['last_success_at']}


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
    analysis = analyzer.analyze(request.url, claim=request.claim)
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
