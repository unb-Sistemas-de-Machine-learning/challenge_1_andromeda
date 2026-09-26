from news_analysis.pipeline.version import current_pipeline_version, derive_pipeline_id


def test_current_pipeline_version_has_required_metadata():
    version = current_pipeline_version()
    assert version.id.startswith("pipeline-")
    assert version.rules_version
    assert version.fact_check_mapping_version
    assert version.writing_model_name == "vzani/portuguese-fake-news-classifier-bertimbau-combined"
    assert "fastapi" in version.dependency_versions


def test_pipeline_identifier_changes_when_version_inputs_change():
    base = derive_pipeline_id(deps={"fastapi": "1"}, writing_model_revision="a")
    assert derive_pipeline_id(deps={"fastapi": "2"}, writing_model_revision="a") != base
    assert derive_pipeline_id(deps={"fastapi": "1"}, writing_model_revision="b") != base
    assert derive_pipeline_id(deps={"fastapi": "1"}, rules_version="other") != base
    assert derive_pipeline_id(deps={"fastapi": "1"}, fact_check_mapping_version="other") != base
    assert derive_pipeline_id(deps={"fastapi": "1"}, intended_weights={"source_credibility": 1.0}) != base
