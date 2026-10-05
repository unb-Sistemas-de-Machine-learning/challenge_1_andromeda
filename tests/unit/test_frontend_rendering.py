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
    criteria = {"writing_style": {"available": True, "score": 1, "intended_weight": 0.4}, "factual_claims": {"status": "NOT_IMPLEMENTED"}}
    if criterion is not None:
        criteria[key] = criterion
    return {"status": "SUCCESS", "final": {"score": 100, "coverage": 40, "formula": "1.00 * W * 100"}, "criteria": criteria}


def test_unavailable_fact_check_remains_visible_with_all_attempts():
    criterion = {"available": False, "status": "UNAVAILABLE", "intended_weight": 0.6, "reviews_count": 0, "applicable_reviews_count": 0, "scored_reviews_count": 0, "publishers_count": 0, "search_attempts": [{"query": f"consulta {i}", "claims_count": 0} for i in range(6)], "error": {"code": "CRITERION_UNAVAILABLE", "details": {"reason": "no_reviews_returned"}, "message": "No reviews"}}
    html = render(payload(criterion))
    assert "Checagem de fatos verificáveis" in html
    assert "O Google Fact Check não retornou" in html
    assert "consulta 5" in html
    assert "Consultas realizadas (6)" in html
    assert "Somente estilo de escrita" in html
    assert "Confiabilidade mais alta" not in html


def test_legacy_fact_key_and_error_attempts_are_supported():
    criterion = {"available": False, "status": "UNAVAILABLE", "search_attempts": [], "error": {"message": "No matching reviews", "details": {"attempted_queries": ["consulta antiga"]}}}
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
