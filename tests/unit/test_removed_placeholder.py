from pathlib import Path

from news_analysis.api.app import INDEX_HTML, app


def test_only_implemented_criteria_are_in_api_and_frontend():
    schemas = app.openapi()['components']['schemas']
    criteria = schemas['CriteriaSet']['properties']
    assert set(criteria) == {'verifiable_facts', 'writing_style', 'credibility', 'credibility_evidence'}
    assert 'ReservedCriterionResult' not in schemas
    assert 'reservedCard' not in INDEX_HTML
    assert 'Modelo planejado' not in INDEX_HTML
    assert not Path('src/news_analysis/criteria/factual_claims.py').exists()
