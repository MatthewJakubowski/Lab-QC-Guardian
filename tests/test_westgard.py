import pytest
from lab_qc_guardian.engine import (
    ControlTarget,
    RunStatus,
    ViolationType,
    WestgardEngine,
)
from lab_qc_guardian.metrics import MetrologyEngine


@pytest.fixture
def dual_level_engine():
    targets = {
        "Level 1": ControlTarget(level="Level 1", target_mean=100.0, target_sd=2.0),
        "Level 2": ControlTarget(level="Level 2", target_mean=200.0, target_sd=4.0),
    }
    return WestgardEngine(targets=targets, window_size=15)


def test_in_control_acceptance(dual_level_engine):
    res = dual_level_engine.evaluate_run({"Level 1": 100.5, "Level 2": 201.0})
    assert res.status == RunStatus.ACCEPTED
    assert len(res.violations) == 0


def test_rule_1_2s_warning_only(dual_level_engine):
    res = dual_level_engine.evaluate_run({"Level 1": 104.5, "Level 2": 200.0})
    assert res.status == RunStatus.WARNING
    assert any(v.rule_name == "1_2s" and v.violation_type == ViolationType.WARNING for v in res.violations)


def test_rule_1_3s_random_error(dual_level_engine):
    res = dual_level_engine.evaluate_run({"Level 1": 106.5, "Level 2": 200.0})
    assert res.status == RunStatus.REJECTED
    assert any(v.rule_name == "1_3s" and v.violation_type == ViolationType.RANDOM_ERROR for v in res.violations)


def test_rule_2_2s_within_control(dual_level_engine):
    dual_level_engine.evaluate_run({"Level 1": 104.5, "Level 2": 200.0})
    res = dual_level_engine.evaluate_run({"Level 1": 104.2, "Level 2": 200.0})
    assert res.status == RunStatus.REJECTED
    assert any(v.rule_name == "2_2s" and v.violation_type == ViolationType.SYSTEMATIC_ERROR for v in res.violations)


def test_rule_2_2s_across_controls(dual_level_engine):
    res = dual_level_engine.evaluate_run({"Level 1": 104.5, "Level 2": 209.0})
    assert res.status == RunStatus.REJECTED
    assert any(v.rule_name == "2_2s" and v.violation_type == ViolationType.SYSTEMATIC_ERROR for v in res.violations)


def test_rule_r_4s_across_controls(dual_level_engine):
    res = dual_level_engine.evaluate_run({"Level 1": 105.0, "Level 2": 190.0})
    assert res.status == RunStatus.REJECTED
    assert any(v.rule_name == "R_4s" and v.violation_type == ViolationType.RANDOM_ERROR for v in res.violations)


def test_rule_4_1s_systematic_drift(dual_level_engine):
    for _ in range(3):
        dual_level_engine.evaluate_run({"Level 1": 102.5, "Level 2": 200.0})
    res4 = dual_level_engine.evaluate_run({"Level 1": 102.5, "Level 2": 200.0})
    assert any(v.rule_name == "4_1s" and v.violation_type == ViolationType.SYSTEMATIC_ERROR for v in res4.violations)
    assert res4.status == RunStatus.REJECTED


def test_rule_10_x_mean_shift(dual_level_engine):
    for _ in range(9):
        dual_level_engine.evaluate_run({"Level 1": 100.8, "Level 2": 200.0})
    res10 = dual_level_engine.evaluate_run({"Level 1": 100.8, "Level 2": 200.0})
    assert any(v.rule_name == "10_x" and v.violation_type == ViolationType.SYSTEMATIC_ERROR for v in res10.violations)
    assert res10.status == RunStatus.REJECTED


def test_metrology_six_sigma_evaluation():
    metrics = MetrologyEngine.calculate_sigma(tea_percent=10.0, bias_percent=1.0, cv_percent=1.5)
    assert round(metrics.sigma_metric, 2) == 6.0
    assert metrics.quality_tier == "World Class"
