from news_analysis.criteria.rating_normalization import normalize_rating


def test_normalizes_recognized_ratings():
    assert normalize_rating("Verdadeiro") == 1.0
    assert normalize_rating("Meia verdade") == 0.5
    assert normalize_rating("Falso") == 0.0


def test_unmapped_rating_remains_unnormalized():
    assert normalize_rating("Sem escala editorial") is None


def test_unknown_or_negated_phrases_do_not_match_substrings():
    assert normalize_rating("Mostly false") == 0.25
    assert normalize_rating("Não é verdade") == 0.0
    assert normalize_rating("not true") is None
    assert normalize_rating("This is true but misleading") is None
    assert normalize_rating("Verdadeiro em outro contexto") is None
