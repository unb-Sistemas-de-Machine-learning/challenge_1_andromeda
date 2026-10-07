import json
import shutil
import subprocess

import pytest

from news_analysis.api.app import INDEX_HTML


def render(payload):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required to execute the frontend rendering regression test")
    script = INDEX_HTML.split("<script>")[1].split("</script>")[0]
    harness = r"""
const vm = require('node:vm');
const fs = require('node:fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = { innerHTML: '' };
const dummy = {addEventListener(){},querySelector(){return dummy;},classList:{add(){},remove(){}}};
const context = {document:{querySelector(selector){return selector === '#result' ? result : dummy;}},fetch:()=>new Promise(()=>{})};
vm.createContext(context);
vm.runInContext(input.script, context);
context.payload = input.payload;
vm.runInContext('renderAnalysis(payload)', context);
process.stdout.write(result.innerHTML);
"""
    return subprocess.run([node, "-e", harness], input=json.dumps({"script": script, "payload": payload}), text=True, capture_output=True, check=True, encoding="utf-8").stdout


def payload(criterion=None, key="verifiable_facts"):
    criteria = {"writing_style": {"available": True, "score": 1, "intended_weight": 0.4}}
    if criterion is not None:
        criteria[key] = criterion
    return {"status": "SUCCESS", "final": {"score": 100, "coverage": 40, "formula": "1.00 * W * 100"}, "criteria": criteria}


def test_credibility_details_and_veto_are_rendered_safely():
    data = payload()
    data['criteria']['credibility'] = dict(score_fonte=5, confianca_fonte='baixa', dominio='example.com',
        criterios=[dict(nome='https', pontos=5, maximo=5, status='ok', detalhe='<script>injected</script>')],
        flags=['dominio_recem_criado'], erros=[], veto_dominio_suspeito=True)
    html = render(data)
    assert 'Credibilidade da fonte' in html
    assert 'Teto de 35' in html
    assert 'dominio_recem_criado' in html
    assert '<script>injected</script>' not in html


def test_unavailable_fact_check_remains_visible_with_all_attempts():
    criterion = {"available": False, "status": "UNAVAILABLE", "intended_weight": 0.6, "reviews_count": 0, "applicable_reviews_count": 0, "scored_reviews_count": 0, "publishers_count": 0, "search_attempts": [{"query": f"consulta {i}", "claims_count": 0} for i in range(6)], "error": {"code": "CRITERION_UNAVAILABLE", "details": {"reason": "no_reviews_returned"}, "message": "No reviews"}}
    html = render(payload(criterion))
    assert "Checagem de fatos verificáveis" in html
    assert "O Google Fact Check não retornou" in html
    assert "consulta 5" in html
    assert "Consultas realizadas (6)" in html
    assert "Confiabilidade alta" in html
    assert "A avaliação considera apenas o estilo de escrita" in html
    assert "Somente estilo de escrita" not in html


def test_legacy_fact_key_and_error_attempts_are_supported():
    criterion = {"available": False, "status": "UNAVAILABLE", "reviews_count": 0, "search_attempts": [], "error": {"message": "No matching reviews", "details": {"attempted_queries": ["consulta antiga"]}}}
    html = render(payload(criterion, key="source_credibility"))
    assert "Checagem de fatos verificáveis" in html
    assert "consulta antiga" in html
    assert "formato anterior" in html


def test_missing_fact_criterion_is_explained_instead_of_hidden():
    html = render(payload())
    assert "Checagem de fatos verificáveis" in html
    assert "não contém o critério" in html


def test_evidence_details_are_escaped_and_unsafe_links_are_omitted():
    criterion = {"available": True, "score": 0, "reviews": [{"claim": "<script>alert(1)</script>", "textual_rating": "Falso", "publisher_name": "Agência", "review_url": "javascript:alert(1)", "included_in_score": False, "exclusion_reason": "duplicate_review"}], "publishers_count": 1, "publisher_scores": {"agencia.example": 0}, "conflicting_verdicts": True, "search_truncated": True}
    html = render(payload(criterion))
    assert "&lt;script&gt;" in html
    assert "javascript:" not in html
    assert "checagem duplicada" in html
    assert "vereditos divergentes" in html
    assert "três páginas" in html
    assert "agencia.example" in html


def test_writing_segment_details_are_available():
    data = payload()
    data["criteria"]["writing_style"]["segments"] = [{"index": 0, "character_count": 1200, "token_count": 512, "label": "True", "confidence": 0.9, "writing_score": 0.9}]
    html = render(data)
    assert "Resultados por segmento (1)" in html
    assert "1200 caracteres" in html
    assert "512 tokens" in html


def test_historical_metadata_is_not_rendered_as_fact_check():
    data = payload()
    data['criteria']['source_credibility'] = dict(available=True, score=1, intended_weight=.2,
        effective_weight=.4, contribution=40, signals=[dict(label='HTTPS', passed=True, evidence='<unsafe>')])
    html = render(data)
    assert 'Credibilidade da fonte — análise histórica' in html
    assert 'sem recálculo' in html
    assert 'não contém o critério' in html
    assert 'Confiabilidade alta' in html
    assert '&lt;unsafe&gt;' in html


def test_unavailable_source_and_pre_veto_score_are_explicit():
    data = payload()
    data['final']['score_before_veto'] = 100
    data['criteria']['credibility'] = dict(score_fonte=None, confianca_fonte='baixa', criterios=[],
                                         veto_dominio_suspeito=False)
    html = render(data)
    assert 'Pontuação da fonte indisponível' in html
    assert 'indisponibilidade não aplica veto' in html
    assert 'Média antes do veto' in html
    assert 'Teto de 35 aplicado' not in html


def test_fact_evidence_states_and_supplemental_claims_are_distinct_and_escaped():
    data = payload({'available': True, 'score': .5, 'evidence_status': 'MIXED', 'search_incomplete': True,
        'additional_claims': [{'target_claim': '<script>extra</script>', 'evidence_status': 'REFUTED',
            'reviews': [{'claim': 'Outra afirmação', 'textual_rating': 'Falso', 'included_in_score': True,
                         'normalized_value': 0, 'review_url': 'javascript:alert(1)'}]}]})
    html = render(data)
    assert 'Evidências mistas ou parciais' in html
    assert 'Evidências contrárias' in html
    assert 'Busca incompleta' in html
    assert 'não entram na nota' in html
    assert 'fora da nota final' in html
    assert '<script>extra</script>' not in html
    assert '&lt;script&gt;extra&lt;/script&gt;' in html
    assert 'href="javascript:' not in html


@pytest.mark.parametrize("score,label", [
    (40, "Confiabilidade baixíssima"),
    (70, "Confiabilidade baixa"),
    (85, "Confiabilidade média"),
    (86, "Confiabilidade alta"),
])
def test_confidence_labels_follow_requested_thresholds(score, label):
    data = payload({"available": True, "score": 0.5})
    data["final"]["score"] = score
    assert label in render(data)


def test_fallback_explanation_is_rendered_without_sml_attribution():
    data = payload({"available": True, "score": 0.5})
    data['criteria']['credibility'] = {'criterios': [{'nome': 'veiculo_reconhecido', 'status': 'negativo', 'pontos': 0, 'maximo': 35, 'detalhe': 'Não localizado'}], 'confianca_fonte': 'baixa', 'score_fonte': 0}
    data["explanation"] = {"status": "SUCCESS", "validation": "FALLBACK",
                           "text": "Confiabilidade média. Pontos negativos encontrados: o veículo não foi reconhecido."}
    html = render(data)
    assert "Por que esta notícia recebeu esta avaliação?" in html
    assert "O veículo desta notícia não foi encontrado nas bases de veículos consultadas" in html
    assert "Resumo baseado nos critérios" in html


def test_writing_only_analysis_ignores_corrupted_sml_and_explains_source_coverage():
    data = payload({"available": False, "evidence_status": "UNAVAILABLE", "status": "UNAVAILABLE",
                    "reviews_count": 0, "search_attempts": [{"query": "teste", "status": "success", "claims_count": 0}]})
    data["final"].update(score=86.1, coverage=40)
    data["explanation"] = {"status": "SUCCESS", "validation": "VALID", "model_id": "google/flan-t5-small",
                           "text": "Fonte: Negative Pontes encontrados: o veculo no foi reconhecido; cobertura parcial."}
    data["limitations"] = ["Only the writing-style criterion contributed to the final index."]
    data["criteria"]["credibility"] = {
        "score_fonte": 100, "confianca_fonte": "baixa", "dominio": "cnnbrasil.com.br",
        "criterios": [
            {"nome": "veiculo_reconhecido", "pontos": 0, "maximo": 35, "status": "indisponivel", "detalhe": "Base ausente"},
            {"nome": "transparencia_editorial", "pontos": 25, "maximo": 25, "status": "ok", "detalhe": "Metadados encontrados"},
            {"nome": "idade_dominio", "pontos": 15, "maximo": 15, "status": "ok", "detalhe": "Domínio antigo"},
            {"nome": "tld_institucional", "pontos": 0, "maximo": 20, "status": "neutro", "detalhe": "Sem penalidade"},
            {"nome": "https", "pontos": 5, "maximo": 5, "status": "ok", "detalhe": "Certificado validado"},
        ],
    }
    html = render(data)
    assert "Confiabilidade alta" in html
    assert "não confirma os fatos da notícia" in html
    assert "O veículo desta notícia não pôde ser consultado na base de veículos" in html
    assert "Pontuação parcial dos sinais avaliados: 100/100 · Cobertura dos sinais: 45% (baixa)" in html
    assert "Apenas o estilo de escrita contribuiu" in html
    assert "Negative Pontes" not in html
    assert "Somente estilo de escrita" not in html
    assert " · concluída" in html

    data["criteria"]["credibility"]["criterios"][0]["status"] = "ok"
    data["criteria"]["credibility_evidence"] = {
        "status": "matched", "checked_at": "2026-10-07", "providers": [
            {"source": "atlas", "status": "available", "reason_code": "incomplete_identity_coverage"}
        ], "evidence": [{"source": "atlas"}],
    }
    matched_html = render(data)
    assert "O veículo desta notícia foi encontrado no Atlas da Notícia." in matched_html
    assert "cadastro parcial" in matched_html
    assert "no_snapshot" not in matched_html
