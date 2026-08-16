"""
Lab-QC-Guardian v2.0 - Test Suite
Unit tests for Westgard Multirules Engine and Six Sigma Metrology (pytest).
"""

import pytest
from lab_qc_guardian.engine import (
    ActionStatus,
    ControlTarget,
    RuleViolationType,
    WestgardEngine,
)
from lab_qc_guardian.metrics import MetrologyEngine, QualityTier


@pytest.fixture
def dual_level_engine() -> WestgardEngine:
    """Fixture definiujący dwa poziomy kontroli: Level 1 (Normal) i Level 2 (Pathological)."""
    targets = {
        "Level 1": ControlTarget(level="Level 1", target_mean=100.0, target_sd=2.0),
        "Level 2": ControlTarget(level="Level 2", target_mean=200.0, target_sd=4.0),
    }
    return WestgardEngine(targets=targets, window_size=15)


def test_in_control_acceptance(dual_level_engine: WestgardEngine):
    """Wyniki w granicach +/- 1 SD powinny zostać zaakceptowane bez ostrzeżeń."""
    res = dual_level_engine.evaluate_run({"Level 1": 100.5, "Level 2": 199.0})
    assert res.status == ActionStatus.ACCEPT
    assert not res.is_rejected
    assert len(res.violations) == 0


def test_rule_1_2s_warning_only(dual_level_engine: WestgardEngine):
    """Reguła 1_2s jest wyłącznie ostrzeżeniem i nie powinna blokować serii pomiarowej."""
    # Level 1 na poziomie 104.5 (+2.25 SD) -> Ostrzeżenie
    res = dual_level_engine.evaluate_run({"Level 1": 104.5, "Level 2": 200.0})
    assert res.status == ActionStatus.WARNING_ACCEPT
    assert not res.is_rejected
    assert any(v.rule_name == "1_2s" and v.violation_type == RuleViolationType.WARNING for v in res.violations)


def test_rule_1_3s_random_error(dual_level_engine: WestgardEngine):
    """Przekroczenie +/- 3 SD na jednym poziomie powinno natychmiast odrzucić serię (błąd losowy)."""
    # Level 1 na poziomie 107.0 (+3.5 SD)
    res = dual_level_engine.evaluate_run({"Level 1": 107.0, "Level 2": 200.0})
    assert res.status == ActionStatus.REJECT
    assert res.is_rejected
    assert any(v.rule_name == "1_3s" and v.violation_type == RuleViolationType.RANDOM_ERROR for v in res.violations)


def test_rule_2_2s_within_control(dual_level_engine: WestgardEngine):
    """Dwa kolejne pomiary tego samego poziomu powyżej +2 SD powinny wywołać odrzucenie serii."""
    # Seria 1: +2.1 SD (Ostrzeżenie 1_2s)
    res1 = dual_level_engine.evaluate_run({"Level 1": 104.2, "Level 2": 200.0})
    assert res1.status == ActionStatus.WARNING_ACCEPT

    # Seria 2: +2.2 SD -> Aktywacja 2_2s Within-Control
    res2 = dual_level_engine.evaluate_run({"Level 1": 104.4, "Level 2": 200.0})
    assert res2.status == ActionStatus.REJECT
    assert any(v.rule_name == "2_2s (Within-Control)" and v.violation_type == RuleViolationType.SYSTEMATIC_ERROR for v in res2.violations)


def test_rule_2_2s_across_controls(dual_level_engine: WestgardEngine):
    """Oba poziomy w tej samej serii przekraczające +2 SD powinny odrzucić serię."""
    # Level 1 = 104.5 (+2.25 SD), Level 2 = 209.0 (+2.25 SD)
    res = dual_level_engine.evaluate_run({"Level 1": 104.5, "Level 2": 209.0})
    assert res.status == ActionStatus.REJECT
    assert any(v.rule_name == "2_2s (Across-Controls)" for v in res.violations)


def test_rule_r_4s_across_controls(dual_level_engine: WestgardEngine):
    """Rozstęp między poziomami w serii >= 4 SD to błąd losowy."""
    # Level 1 = +2.1 SD (104.2), Level 2 = -2.1 SD (191.6) -> Rozstęp = 4.2 SD
    res = dual_level_engine.evaluate_run({"Level 1": 104.2, "Level 2": 191.6})
    assert res.status == ActionStatus.REJECT
    assert any(v.rule_name == "R_4s (Across-Controls)" and v.violation_type == RuleViolationType.RANDOM_ERROR for v in res.violations)


def test_rule_4_1s_systematic_drift(dual_level_engine: WestgardEngine):
    """4 kolejne pomiary powyżej +1 SD powinny zasygnalizować błąd systematyczny / dryf."""
    for _ in range(3):
        dual_level_engine.evaluate_run({"Level 1": 102.5, "Level 2": 200.0})

    res4 = dual_level_engine.evaluate_run({"Level 1": 102.5, "Level 2": 200.0})
    assert any(v.rule_name == "4_1s" and v.violation_type == RuleViolationType.SYSTEMATIC_ERROR for v in res4.violations)


def test_rule_10_x_mean_shift(dual_level_engine: WestgardEngine):
    """10 kolejnych wyników po tej samej stronie średniej docelowej to przesunięcie analityczne."""
    for _ in range(9):
        dual_level_engine.evaluate_run({"Level 1": 100.8, "Level 2": 200.0})

    res10 = dual_level_engine.evaluate_run({"Level 1": 100.9, "Level 2": 200.0})
    assert any(v.rule_name == "10_x" and v.violation_type == RuleViolationType.SYSTEMATIC_ERROR for v in res10.violations)


def test_metrology_six_sigma_evaluation():
    """Weryfikacja kalkulatora metryki Six Sigma."""
    values = [99.0, 100.0, 101.0]
    evaluation = MetrologyEngine.evaluate_six_sigma(
        analyte_name="Glukoza",
        level_name="Level 1",
        values=values,
        target_mean=100.0,
        tea_percent=6.0,
    )
    assert evaluation.sigma_metric == 6.0
    assert evaluation.quality_tier == QualityTier.WORLD_CLASS
    assert "1_3s" in evaluation.recommended_qc_rule_frequency
