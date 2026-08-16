"""
Lab-QC-Guardian v2.0 - Metrology & Six Sigma Quality Metrics Engine
Compliant with ISO 15189:2022 and Clinical Metrology Standards.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence


class QualityTier(str, Enum):
    WORLD_CLASS = "World Class (>= 6σ)"
    EXCELLENT = "Excellent (5σ - 5.9σ)"
    GOOD = "Good (4σ - 4.9σ)"
    MARGINAL = "Marginal (3σ - 3.9σ)"
    POOR = "Poor / Unacceptable (< 3σ)"


@dataclass(frozen=True)
class QCStatistics:
    """Parametry statystyczne próby kontrolnej."""
    count: int
    mean: float
    sd: float
    cv: float


@dataclass(frozen=True)
class SigmaEvaluation:
    """Kompleksowy raport z oceny metrologicznej Six Sigma."""
    analyte_name: str
    level_name: str
    target_mean: float
    calculated_mean: float
    sd: float
    cv_percent: float
    bias_percent: float
    tea_percent: float
    sigma_metric: float
    quality_tier: QualityTier
    recommended_qc_rule_frequency: str


class MetrologyEngine:
    """Kalkulator wskaźników precyzji, obciążenia (Bias) oraz metryki Six Sigma."""

    @staticmethod
    def calculate_mean(values: Sequence[float]) -> float:
        if not values:
            raise ValueError("Brak danych pomiarowych do obliczenia średniej.")
        return sum(values) / len(values)

    @staticmethod
    def calculate_sd(values: Sequence[float], mean: Optional[float] = None) -> float:
        n = len(values)
        if n < 2:
            raise ValueError("Wymagane są co najmniej 2 pomiary do wyznaczenia SD próby (n - 1).")
        mu = mean if mean is not None else MetrologyEngine.calculate_mean(values)
        variance = sum((x - mu) ** 2 for x in values) / (n - 1)
        return math.sqrt(variance)

    @staticmethod
    def calculate_cv(sd: float, mean: float) -> float:
        if mean == 0:
            raise ValueError("Średnia nie może wynosić 0 przy kalkulacji CV%.")
        return (sd / abs(mean)) * 100.0

    @staticmethod
    def calculate_bias(observed_mean: float, target_mean: float) -> float:
        """Oblicza błąd systematyczny względny (Bias%)."""
        if target_mean == 0:
            raise ValueError("Wartość docelowa (target_mean) nie może być zerowa.")
        return ((observed_mean - target_mean) / target_mean) * 100.0

    @staticmethod
    def calculate_z_score(value: float, mean: float, sd: float) -> float:
        if sd == 0:
            raise ValueError("Odchylenie standardowe (SD) nie może wynosić 0.")
        return (value - mean) / sd

    @classmethod
    def compute_dataset_statistics(cls, values: Sequence[float]) -> QCStatistics:
        mean_val = cls.calculate_mean(values)
        sd_val = cls.calculate_sd(values, mean=mean_val)
        cv_val = cls.calculate_cv(sd_val, mean_val)
        return QCStatistics(
            count=len(values),
            mean=mean_val,
            sd=sd_val,
            cv=cv_val,
        )

    @classmethod
    def evaluate_six_sigma(
        cls,
        analyte_name: str,
        level_name: str,
        values: Sequence[float],
        target_mean: float,
        tea_percent: float,
    ) -> SigmaEvaluation:
        stats = cls.compute_dataset_statistics(values)
        bias_pct = cls.calculate_bias(stats.mean, target_mean)
        abs_bias = abs(bias_pct)

        if stats.cv == 0:
            sigma = 6.0
        else:
            sigma = (tea_percent - abs_bias) / stats.cv

        if sigma >= 6.0:
            tier = QualityTier.WORLD_CLASS
            recommendation = "Pojedyncza reguła 1_3s (1 pomiar QC na serię)."
        elif 5.0 <= sigma < 6.0:
            tier = QualityTier.EXCELLENT
            recommendation = "Kaskada 1_3s / 2_2s / R_4s (1-2 pomiary QC na serię)."
        elif 4.0 <= sigma < 5.0:
            tier = QualityTier.GOOD
            recommendation = "Pełna kaskada 1_3s / 2_2s / R_4s / 4_1s (2 pomiary QC na serię)."
        elif 3.0 <= sigma < 4.0:
            tier = QualityTier.MARGINAL
            recommendation = "Pełna kaskada wielokrotna + zwiększona częstotliwość QC (np. 4 pomiary/serię)."
        else:
            tier = QualityTier.POOR
            recommendation = "Brak gotowości analitycznej. Wstrzymanie serii, rekalibracja i audyt metody."

        return SigmaEvaluation(
            analyte_name=analyte_name,
            level_name=level_name,
            target_mean=target_mean,
            calculated_mean=stats.mean,
            sd=stats.sd,
            cv_percent=stats.cv,
            bias_percent=bias_pct,
            tea_percent=tea_percent,
            sigma_metric=round(sigma, 2),
            quality_tier=tier,
            recommended_qc_rule_frequency=recommendation,
        )
