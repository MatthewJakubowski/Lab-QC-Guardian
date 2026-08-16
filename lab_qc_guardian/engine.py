"""
Lab-QC-Guardian v2.0 - Westgard Multirule Decision Engine
Deterministic, sliding-window clinical quality control rule evaluator (ISO 15189 compliance).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RuleViolationType(str, Enum):
    NONE = "BRAK"
    WARNING = "OSTRZEŻENIE"
    RANDOM_ERROR = "BŁĄD LOSOWY"
    SYSTEMATIC_ERROR = "BŁĄD SYSTEMATYCZNY"


class ActionStatus(str, Enum):
    ACCEPT = "ZAAKCEPTOWANO"
    WARNING_ACCEPT = "OSTRZEŻENIE (AKCEPTACJA Z NADZOREM)"
    REJECT = "ODRZUCONO (SERIA WSTRZYMANA)"


@dataclass
class QCPoint:
    """Pojedynczy wynik kontroli jakości."""
    run_id: int
    level: str
    value: float
    z_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RuleViolation:
    rule_name: str
    violation_type: RuleViolationType
    affected_level: str
    description: str
    run_indices: List[int]


@dataclass
class RunEvaluationResult:
    """Zbiorczy wynik ewaluacji pojedynczej serii pomiarowej."""
    run_id: int
    status: ActionStatus
    violations: List[RuleViolation] = field(default_factory=list)
    level_z_scores: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_rejected(self) -> bool:
        return self.status == ActionStatus.REJECT


@dataclass
class ControlTarget:
    """Wartości docelowe przypisane do danego poziomu materiału kontrolnego."""
    level: str
    target_mean: float
    target_sd: float


class WestgardEngine:
    """
    Deterministyczny silnik ewaluacji kaskady reguł Westgarda:
    - 1_2s: Ostrzeżenie (bramka otwierająca pełną kaskadę)
    - 1_3s: Odrzucenie (Błąd losowy)
    - 2_2s: Odrzucenie (Błąd systematyczny - wewnątrz poziomu lub między poziomami)
    - R_4s: Odrzucenie (Błąd losowy - rozstęp >= 4 SD w serii lub między kolejnymi seriami)
    - 4_1s: Odrzucenie/Błąd systematyczny (4 kolejne pomiary > 1 SD lub < -1 SD)
    - 10_x: Odrzucenie/Przesunięcie systematyczne (10 kolejnych pomiarów po jednej stronie średniej)
    """

    def __init__(self, targets: Dict[str, ControlTarget], window_size: int = 15):
        self.targets = targets
        self.window_size = window_size
        self.history: Dict[str, List[QCPoint]] = {level: [] for level in targets.keys()}
        self.run_counter: int = 0

    def calculate_z(self, level: str, value: float) -> float:
        if level not in self.targets:
            raise KeyError(f"Poziom kontroli '{level}' nie został zdefiniowany w parametrach.")
        tgt = self.targets[level]
        return (value - tgt.target_mean) / tgt.target_sd

    def evaluate_run(self, measurements: Dict[str, float]) -> RunEvaluationResult:
        self.run_counter += 1
        current_run_id = self.run_counter
        current_points: Dict[str, QCPoint] = {}
        z_scores_map: Dict[str, float] = {}

        for level, value in measurements.items():
            z = self.calculate_z(level, value)
            point = QCPoint(run_id=current_run_id, level=level, value=value, z_score=z)
            self.history[level].append(point)
            current_points[level] = point
            z_scores_map[level] = round(z, 2)

            if len(self.history[level]) > self.window_size:
                self.history[level].pop(0)

        violations: List[RuleViolation] = []

        warning_triggered = any(abs(pt.z_score) > 2.0 for pt in current_points.values())

        if not warning_triggered:
            return RunEvaluationResult(
                run_id=current_run_id,
                status=ActionStatus.ACCEPT,
                violations=[],
                level_z_scores=z_scores_map
            )

        for level, pt in current_points.items():
            if abs(pt.z_score) > 2.0:
                violations.append(
                    RuleViolation(
                        rule_name="1_2s",
                        violation_type=RuleViolationType.WARNING,
                        affected_level=level,
                        description=f"Wartość z-score ({pt.z_score:.2f}) przekracza ±2 SD. Uruchomiono kaskadę.",
                        run_indices=[current_run_id]
                    )
                )

        # 1_3s (Błąd losowy)
        for level, pt in current_points.items():
            if abs(pt.z_score) > 3.0:
                violations.append(
                    RuleViolation(
                        rule_name="1_3s",
                        violation_type=RuleViolationType.RANDOM_ERROR,
                        affected_level=level,
                        description=f"Przekroczenie progu krytycznego ±3 SD (z = {pt.z_score:.2f}).",
                        run_indices=[current_run_id]
                    )
                )

        # 2_2s Within-Control (Błąd systematyczny w obrębie poziomu)
        for level, hist in self.history.items():
            if len(hist) >= 2:
                z1, z2 = hist[-1].z_score, hist[-2].z_score
                if (z1 > 2.0 and z2 > 2.0) or (z1 < -2.0 and z2 < -2.0):
                    violations.append(
                        RuleViolation(
                            rule_name="2_2s (Within-Control)",
                            violation_type=RuleViolationType.SYSTEMATIC_ERROR,
                            affected_level=level,
                            description=f"Dwa kolejne pomiary przekraczają ten sam próg 2 SD (z1={z2:.2f}, z2={z1:.2f}).",
                            run_indices=[hist[-2].run_id, hist[-1].run_id]
                        )
                    )

        # 2_2s Across-Controls (Błąd systematyczny między poziomami)
        if len(current_points) >= 2:
            levels = list(current_points.keys())
            for i in range(len(levels)):
                for j in range(i + 1, len(levels)):
                    z_a = current_points[levels[i]].z_score
                    z_b = current_points[levels[j]].z_score
                    if (z_a > 2.0 and z_b > 2.0) or (z_a < -2.0 and z_b < -2.0):
                        violations.append(
                            RuleViolation(
                                rule_name="2_2s (Across-Controls)",
                                violation_type=RuleViolationType.SYSTEMATIC_ERROR,
                                affected_level=f"{levels[i]} & {levels[j]}",
                                description="Oba poziomy w bieżącej serii przekraczają ten sam limit 2 SD.",
                                run_indices=[current_run_id]
                            )
                        )

        # R_4s Across-Controls (Błąd losowy w serii)
        if len(current_points) >= 2:
            z_vals = [pt.z_score for pt in current_points.values()]
            range_r4s = max(z_vals) - min(z_vals)
            if range_r4s >= 4.0:
                violations.append(
                    RuleViolation(
                        rule_name="R_4s (Across-Controls)",
                        violation_type=RuleViolationType.RANDOM_ERROR,
                        affected_level="Multi-Level",
                        description=f"Rozstęp z-score w serii wynosi {range_r4s:.2f} SD (>= 4.0 SD).",
                        run_indices=[current_run_id]
                    )
                )

        # R_4s Consecutive-Runs (Błąd losowy między seriami)
        for level, hist in self.history.items():
            if len(hist) >= 2:
                range_single = abs(hist[-1].z_score - hist[-2].z_score)
                if range_single >= 4.0:
                    violations.append(
                        RuleViolation(
                            rule_name="R_4s (Consecutive-Runs)",
                            violation_type=RuleViolationType.RANDOM_ERROR,
                            affected_level=level,
                            description=f"Rozstęp między seriami wynosi {range_single:.2f} SD (>= 4.0 SD).",
                            run_indices=[hist[-2].run_id, hist[-1].run_id]
                        )
                    )

        # 4_1s (Błąd systematyczny / dryf)
        for level, hist in self.history.items():
            if len(hist) >= 4:
                last_4_z = [pt.z_score for pt in hist[-4:]]
                if all(z > 1.0 for z in last_4_z) or all(z < -1.0 for z in last_4_z):
                    violations.append(
                        RuleViolation(
                            rule_name="4_1s",
                            violation_type=RuleViolationType.SYSTEMATIC_ERROR,
                            affected_level=level,
                            description="4 kolejne wyniki przekraczają ten sam próg 1 SD.",
                            run_indices=[pt.run_id for pt in hist[-4:]]
                        )
                    )

        # 10_x (Przesunięcie systematyczne średniej)
        for level, hist in self.history.items():
            if len(hist) >= 10:
                last_10_z = [pt.z_score for pt in hist[-10:]]
                if all(z > 0.0 for z in last_10_z) or all(z < 0.0 for z in last_10_z):
                    violations.append(
                        RuleViolation(
                            rule_name="10_x",
                            violation_type=RuleViolationType.SYSTEMATIC_ERROR,
                            affected_level=level,
                            description="10 kolejnych wyników znajduje się po tej samej stronie średniej docelowej.",
                            run_indices=[pt.run_id for pt in hist[-10:]]
                        )
                    )

        has_rejections = any(
            v.violation_type in (RuleViolationType.RANDOM_ERROR, RuleViolationType.SYSTEMATIC_ERROR)
            for v in violations
        )

        status = ActionStatus.REJECT if has_rejections else ActionStatus.WARNING_ACCEPT

        return RunEvaluationResult(
            run_id=current_run_id,
            status=status,
            violations=violations,
            level_z_scores=z_scores_map
        )
