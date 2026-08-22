import pytest

from demand_workbench.models import (
    CrostonSbaModel,
    ModelRegistry,
    MovingAverageModel,
    SeasonalNaiveModel,
)


def test_seasonal_naive_repeats_last_week() -> None:
    assert SeasonalNaiveModel().predict([1, 2, 3, 4, 5, 6, 7], 9) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        1,
        2,
    ]


def test_moving_average_uses_recent_window() -> None:
    assert MovingAverageModel().predict([2, 4, 6], 2) == [4, 4]


def test_croston_handles_all_zero_history() -> None:
    assert CrostonSbaModel().predict([0, 0, 0], 3) == [0, 0, 0]


def test_registry_rejects_duplicate_names() -> None:
    registry = ModelRegistry()
    registry.register(SeasonalNaiveModel())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(SeasonalNaiveModel())


def test_models_reject_empty_history() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        SeasonalNaiveModel().predict([], 1)
