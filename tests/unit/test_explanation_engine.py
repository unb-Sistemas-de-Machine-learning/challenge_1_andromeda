from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch

from news_analysis.explanation import engine as engine_module
from news_analysis.explanation.context import build_explanation_context
from news_analysis.explanation.engine import FlanT5SmallEngine
from news_analysis.explanation.prompt import build_prompt
from tests.unit.test_explanation import make_analysis


@pytest.fixture
def loaded_engine(monkeypatch):
    tokenizer = Mock()
    tokenizer.return_value = {"input_ids": torch.ones((1, 100), dtype=torch.long)}
    tokenizer.decode.return_value = "Resumo de teste."
    model = Mock()
    model.generate.return_value = torch.ones((1, 30), dtype=torch.long)
    loader = Mock(return_value=(tokenizer, model))
    monkeypatch.setattr(engine_module, "_load_model", loader)
    engine = FlanT5SmallEngine(timeout_seconds=2)
    engine.prepare()
    return engine, tokenizer, model, loader


def test_model_is_reused_and_generation_has_a_time_budget(loaded_engine):
    engine, tokenizer, model, loader = loaded_engine
    context = build_explanation_context(make_analysis())

    def generate(**kwargs):
        assert torch.is_inference_mode_enabled()
        assert kwargs["num_beams"] == 1
        assert kwargs["use_cache"] is True
        assert kwargs["do_sample"] is False
        assert kwargs["max_new_tokens"] == 80
        assert 0 < kwargs["max_time"] <= 2
        assert "min_new_tokens" not in kwargs
        return torch.ones((1, 30), dtype=torch.long)

    model.generate.side_effect = generate
    for _ in range(2):
        engine.prepare()
        assert engine.generate(context) == "Resumo de teste."
    loader.assert_called_once()
    assert model.generate.call_count == 2
    assert tokenizer.call_args.kwargs["truncation"] is False


def test_long_input_is_compacted_without_losing_core_results(loaded_engine):
    engine, tokenizer, model, _ = loaded_engine
    context = build_explanation_context(make_analysis())
    context.negative_source_points = ["um detalhe de fonte muito longo " * 100]
    tokenizer.side_effect = [
        {"input_ids": torch.ones((1, 200), dtype=torch.long)},
        {"input_ids": torch.ones((1, 90), dtype=torch.long)},
    ]
    engine.generate(context)
    compact = tokenizer.call_args.args[0]
    assert "nota 40.0" in compact
    assert "evidências contrárias" in compact
    assert "há pontos negativos" in compact
    assert "há sinais de problemas" in compact
    assert "um detalhe" not in compact
    assert model.generate.call_args.kwargs["input_ids"].shape[-1] == 90


def test_too_small_input_budget_does_not_generate_from_truncated_facts(loaded_engine):
    engine, _, model, _ = loaded_engine
    engine.max_input_tokens = 10
    with pytest.raises(ValueError, match="sml_input_budget_too_small"):
        engine.generate(build_explanation_context(make_analysis()))
    model.generate.assert_not_called()
    assert not engine._lock.locked()


def test_time_exhausted_during_tokenization_skips_generation(loaded_engine, monkeypatch):
    engine, _, model, _ = loaded_engine
    clock = iter([0.0, 3.0])
    monkeypatch.setattr(engine_module, "time", SimpleNamespace(perf_counter=lambda: next(clock)))
    with pytest.raises(TimeoutError, match="sml_timeout"):
        engine.generate(build_explanation_context(make_analysis()))
    model.generate.assert_not_called()
    assert not engine._lock.locked()


def test_timed_out_output_is_discarded_and_lock_is_released(loaded_engine, monkeypatch):
    engine, _, _, _ = loaded_engine
    clock = iter([0.0, 0.1, 2.1])
    monkeypatch.setattr(engine_module, "time", SimpleNamespace(perf_counter=lambda: next(clock)))
    with pytest.raises(TimeoutError, match="sml_timeout"):
        engine.generate(build_explanation_context(make_analysis()))
    assert not engine._lock.locked()


def test_busy_engine_does_not_wait_indefinitely(loaded_engine):
    engine, _, model, _ = loaded_engine
    engine.timeout_seconds = 0
    engine._lock.acquire()
    try:
        with pytest.raises(TimeoutError, match="sml_timeout"):
            engine.generate(build_explanation_context(make_analysis()))
        model.generate.assert_not_called()
        assert engine._lock.locked()  # The waiting call must not release another call's lock.
    finally:
        engine._lock.release()


@pytest.mark.parametrize("state,expected", [
    ("SUPPORTED", "favoráveis"),
    ("REFUTED", "contrárias"),
    ("MIXED", "divergentes"),
    ("MATCHED_UNSCORED", "fontes relacionadas, mas faltam dados para concluir"),
    ("UNAVAILABLE", "Faltam evidências factuais para concluir"),
])
def test_prompt_preserves_factual_state_without_article_or_reviews(state, expected):
    context = build_explanation_context(make_analysis(state, coverage=40))
    context.fact_check.target_claim = "artigo inteiro " * 10000
    prompt = build_prompt(context)
    assert expected in prompt
    assert "artigo inteiro" not in prompt
    assert "cobertura parcial" in prompt
    assert len(prompt) < 500


def test_prompt_keeps_missing_criteria_and_source_veto_explicit():
    context = build_explanation_context(make_analysis("UNAVAILABLE"))
    context.source.available = False
    context.writing_style.available = False
    assert "Fonte: dados indisponíveis; escrita: dados indisponíveis" in build_prompt(context)
    context.source_veto_applied = True
    assert "veto aplicado à fonte" in build_prompt(context)
