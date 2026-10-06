from news_analysis.pipeline.version import current_pipeline_version, derive_pipeline_id


def test_current_pipeline_version_has_required_metadata():
    version = current_pipeline_version()
    assert version.id.startswith("pipeline-")
    assert version.rules_version
    assert version.fact_check_mapping_version
    assert version.writing_model_name == "vzani/portuguese-fake-news-classifier-bertimbau-combined"
    assert "fastapi" in version.dependency_versions
    assert version.credibility_policy_hash


def test_pipeline_identifier_changes_when_version_inputs_change():
    base = derive_pipeline_id(deps={"fastapi": "1"}, writing_model_revision="a")
    assert derive_pipeline_id(deps={"fastapi": "2"}, writing_model_revision="a") != base
    assert derive_pipeline_id(deps={"fastapi": "1"}, writing_model_revision="b") != base
    assert derive_pipeline_id(deps={"fastapi": "1"}, rules_version="other") != base
    assert derive_pipeline_id(deps={"fastapi": "1"}, fact_check_mapping_version="other") != base
    assert derive_pipeline_id(deps={"fastapi": "1"}, intended_weights={"verifiable_facts": 1.0}) != base


def test_effective_source_policy_changes_pipeline_id_without_exposing_secrets():
    from dataclasses import replace
    from news_analysis.criteria.credibility_config import AtlasConfig, CredibilityConfig
    from news_analysis.criteria.credibility_policy import scoring_policy
    config = CredibilityConfig()
    base = current_pipeline_version(config)
    for changed in (replace(config, veto_threshold=30), replace(config, age_cap=4),
                    replace(config, weights=(30, 30, 15, 20, 5)),
                    replace(config, atlas=AtlasConfig(enabled=True))):
        version = current_pipeline_version(changed)
        assert version.id != base.id
        assert version.credibility_policy_hash != base.credibility_policy_hash
    credentials = replace(config, atlas=AtlasConfig(auth_mode='account', email='private@example.com', password='secret-value'))
    assert scoring_policy(credentials) == scoring_policy(config)
    assert 'secret-value' not in str(scoring_policy(credentials))
