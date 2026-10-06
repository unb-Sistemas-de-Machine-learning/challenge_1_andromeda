from pathlib import Path

import yaml

from news_analysis.api.app import app


def test_contract_file_defines_expected_paths_and_statuses():
    contract = yaml.safe_load(Path("specs/001-news-analysis/contracts/openapi.yaml").read_text())
    assert set(contract["paths"]) == {"/analyses", "/analyses/{analysis_id}"}
    statuses = contract["components"]["schemas"]["AnalysisStatus"]["enum"]
    assert "RATE_LIMITED" in statuses
    assert "ARTICLE_EXTRACTION_FAILED" in statuses


def test_generated_openapi_contains_contract_paths():
    generated = app.openapi()
    assert "/analyses" in generated["paths"]
    assert "/analyses/{analysis_id}" in generated["paths"]
    assert "post" in generated["paths"]["/analyses"]
    assert "get" in generated["paths"]["/analyses/{analysis_id}"]


def test_stored_contract_schemas_match_runtime_including_historical_and_audit_fields():
    from news_analysis.api.schemas import ErrorResponse
    contract = yaml.safe_load(Path('specs/001-news-analysis/contracts/openapi.yaml').read_text(encoding='utf-8'))
    generated = dict(app.openapi()['components']['schemas'])
    generated['AnalysisResponse'] = generated.pop('Analysis')
    error = ErrorResponse.model_json_schema(ref_template='#/components/schemas/{model}')
    error.pop('$defs', None)
    generated['ErrorResponse'] = error
    assert contract['components']['schemas'] == generated
