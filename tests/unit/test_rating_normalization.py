from news_analysis.criteria.rating_normalization import normalize_rating


def test_normalizes_recognized_ratings():
    assert normalize_rating("Verdadeiro") == 1.0
    assert normalize_rating("Meia verdade") == 0.5
    assert normalize_rating("Falso") == 0.0


def test_unmapped_rating_remains_unnormalized():
    assert normalize_rating("Sem escala editorial") is None
