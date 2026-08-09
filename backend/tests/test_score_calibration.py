import numpy as np
import pytest

from scripts.calibrate_detector_scores import inverse_platt_target, weighted_ece, wilson_interval


def test_inverse_platt_target_round_trips():
    coefficient = 1.7
    intercept = -0.3
    raw_score = inverse_platt_target(coefficient, intercept, 0.7)
    raw_logit = np.log(raw_score / (1 - raw_score))
    calibrated = 1 / (1 + np.exp(-(coefficient * raw_logit + intercept)))
    assert calibrated == pytest.approx(0.7)


def test_weighted_ece_is_zero_for_matching_bins():
    labels = np.array([0, 1])
    probabilities = np.array([0.0, 1.0])
    weights = np.array([1.0, 1.0])
    assert weighted_ece(labels, probabilities, weights) == pytest.approx(0.0)


def test_wilson_interval_contains_observed_rate():
    lower, upper = wilson_interval(80, 100)
    assert lower < 0.8 < upper
