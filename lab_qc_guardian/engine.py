from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RunStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    WARNING = "WARNING"
    REJECTED = "REJECTED"


class ViolationType(str, Enum):
    WARNING = "WARNING"
    RANDOM_ERROR = "RANDOM_ERROR"
    SYSTEMATIC_ERROR = "SYSTEMATIC_ERROR"


@dataclass(frozen=True)
class ControlTarget:
    level: str
    target_mean: float
    target_sd: float


@dataclass
class WestgardViolation:
    rule_name: str
    violation_type: ViolationType
    description: str
    affected_levels: List[str]


@dataclass
class RunEvaluationResult:
    status: RunStatus
    violations: List[WestgardViolation] = field(default_factory=list)
    z_scores: Dict[str, float] = field(default_factory=dict)


class WestgardEngine:
    """
    Deterministic Statistical Quality Control (SQC) Engine
    implementing multi-level sliding-window Westgard multirules.
    """

    def __init__(self, targets: Dict[str, ControlTarget], window_size: int = 15):
        self.targets = targets
        self.window_size = window_size
        self.history: Dict[str, List[float]] = {lvl: [] for lvl in targets.keys()}

    def _calculate_z(self, level: str, value: float) -> float:
        target = self.targets[level]
        if target.target_sd <= 0:
            raise ValueError(f"Target SD for {level} must be greater than 0.")
        return (value - target.target_mean) / target.target_sd

    def evaluate_run(self, measurements: Dict[str, float]) -> RunEvaluationResult:
        violations: List[WestgardViolation] = []
        current_z: Dict[str, float] = {}

        # 1. Oblicz z-score i zaktualizuj historię okna przesuwnego
        for level, val in measurements.items():
            if level in self.targets:
                z = self._calculate_z(level, val)
                current_z[level] = z
                self.history[level].append(z)
                if len(self.history[level]) > self.window_size:
                    self.history[level].pop(0)

        # 2. Reguła 1_3s (Błąd losowy - krytyczny)
        for level, z in current_z.items():
            if abs(z) > 3.0:
                violations.append(
                    WestgardViolation(
                        rule_name="1_3s",
                        violation_type=ViolationType.RANDOM_ERROR,
                        description=f"Control {level} value |z|={abs(z):.2f} > 3.0 SD threshold.",
                        affected_levels=[level],
                    )
                )

        # 3. Reguła 2_2s (Błąd systematyczny)
        # a) W obrębie tego samego poziomu (2 ostatnie serie)
        for level in current_z.keys():
            hist = self.history[level]
            if len(hist) >= 2:
                if (hist[-1] > 2.0 and hist[-2] > 2.0) or (hist[-1] < -2.0 and hist[-2] < -2.0):
                    violations.append(
                        WestgardViolation(
                            rule_name="2_2s",
                            violation_type=ViolationType.SYSTEMATIC_ERROR,
                            description=f"Level {level}: 2 consecutive results exceed 2.0 SD in same direction.",
                            affected_levels=[level],
                        )
                    )

        # b) Pomiędzy poziomami w bieżącej serii
        levels = list(current_z.keys())
        if len(levels) >= 2:
            z1, z2 = current_z[levels[0]], current_z[levels[1]]
            if (z1 > 2.0 and z2 > 2.0) or (z1 < -2.0 and z2 < -2.0):
                violations.append(
                    WestgardViolation(
                        rule_name="2_2s",
                        violation_type=ViolationType.SYSTEMATIC_ERROR,
                        description=f"Across controls ({levels[0]}, {levels[1]}): both exceed 2.0 SD in same direction.",
                        affected_levels=levels,
                    )
                )

        # 4. Reguła R_4s (Błąd losowy - rozstęp między poziomami >= 4 SD)
        if len(levels) >= 2:
            z_vals = [current_z[lvl] for lvl in levels]
            if max(z_vals) - min(z_vals) >= 4.0:
                violations.append(
                    WestgardViolation(
                        rule_name="R_4s",
                        violation_type=ViolationType.RANDOM_ERROR,
                        description=f"Range across controls is {max(z_vals) - min(z_vals):.2f} SD (>= 4.0 SD).",
                        affected_levels=levels,
                    )
                )

        # 5. Reguła 4_1s (Dryf systematyczny - 4 kolejne pomiary > 1 SD)
        for level in current_z.keys():
            hist = self.history[level]
            if len(hist) >= 4:
                last_4 = hist[-4:]
                if all(z > 1.0 for z in last_4) or all(z < -1.0 for z in last_4):
                    violations.append(
                        WestgardViolation(
                            rule_name="4_1s",
                            violation_type=ViolationType.SYSTEMATIC_ERROR,
                            description=f"Level {level}: 4 consecutive results exceed 1.0 SD on the same side.",
                            affected_levels=[level],
                        )
                    )

        # 6. Reguła 10_x (Przesunięcie analityczne - 10 kolejnych po tej samej stronie średniej)
        for level in current_z.keys():
            hist = self.history[level]
            if len(hist) >= 10:
                last_10 = hist[-10:]
                if all(z > 0 for z in last_10) or all(z < 0 for z in last_10):
                    violations.append(
                        WestgardViolation(
                            rule_name="10_x",
                            violation_type=ViolationType.SYSTEMATIC_ERROR,
                            description=f"Level {level}: 10 consecutive results fall on the same side of the mean.",
                            affected_levels=[level],
                        )
                    )

        # 7. Reguła 1_2s (Ostrzeżenie - tylko jeśli nie ma błędu krytycznego)
        for level, z in current_z.items():
            if abs(z) > 2.0 and not any(v.violation_type != ViolationType.WARNING for v in violations):
                violations.append(
                    WestgardViolation(
                        rule_name="1_2s",
                        violation_type=ViolationType.WARNING,
                        description=f"Level {level}: result |z|={abs(z):.2f} > 2.0 SD warning limit.",
                        affected_levels=[level],
                    )
                )

        # Ustalenie statusu serii analitycznej
        if any(v.violation_type in (ViolationType.RANDOM_ERROR, ViolationType.SYSTEMATIC_ERROR) for v in violations):
            status = RunStatus.REJECTED
        elif any(v.violation_type == ViolationType.WARNING for v in violations):
            status = RunStatus.WARNING
        else:
            status = RunStatus.ACCEPTED

        return RunEvaluationResult(status=status, violations=violations, z_scores=current_z)
