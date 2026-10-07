"""Serializable scoring policy; credentials and local paths are never included."""
import hashlib
import json
import math

from news_analysis.criteria.credibility_config import CONFIG, CredibilityConfig

SOURCE_SCORE_CAP = 35


def scoring_policy(config: CredibilityConfig = CONFIG) -> dict:
    return {
        'version': 'source-policy-v5-institutional-full-score',
        'weights': list(config.weights),
        'base_score_maximum': sum(config.weights) - config.weights[3],
        'institutional_bonus': config.weights[3],
        'transparency_weights': list(config.transparency_weights),
        'age_bands': [[limit if math.isfinite(limit) else None, points]
                      for limit, points in config.age_bands],
        'age_cap': config.age_cap,
        'transparency_threshold': config.transparency_threshold,
        'institutional_tlds': list(config.institutional_tlds),
        'non_institutional_tld_action': 'neutral',
        'low_coverage': config.low_coverage,
        'high_coverage': config.high_coverage,
        'veto_threshold': config.veto_threshold,
        'final_score_cap': SOURCE_SCORE_CAP,
        'unavailable_action': 'zero_points_within_fixed_base; abstain_if_all_base_signals_unavailable',
        'recognized_list_enabled': config.recognized_path is not None,
        'blocklist_enabled': config.blocklist_path is not None,
        'atlas_enabled': config.atlas.enabled,
        'atlas_mapping_version': config.atlas.mapping_version,
        'atlas_refresh_after': config.atlas.refresh_after,
        'atlas_max_age': config.atlas.max_age,
    }


def policy_hash(policy: dict) -> str:
    encoded = json.dumps(policy, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()
