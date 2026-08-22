import math

from demand_workbench.metrics import absolute_error_quantile, bias, mase, wape


def test_accuracy_metrics() -> None:
    actual = [10, 20]
    predicted = [12, 18]
    assert wape(actual, predicted) == 4 / 30
    assert bias(actual, predicted) == 0
    assert mase(actual, predicted, [8, 10, 12, 14], season=1) == 1


def test_zero_actual_is_explicit() -> None:
    assert wape([0, 0], [0, 0]) == 0
    assert math.isinf(wape([0, 0], [1, 0]))


def test_absolute_error_quantile_uses_nearest_rank() -> None:
    assert absolute_error_quantile([-1, 2, -8, 4], 0.75) == 4

