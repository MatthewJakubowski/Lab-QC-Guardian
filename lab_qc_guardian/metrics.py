from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SigmaResult:
    sigma_metric: float
    quality_tier: str
    recommended_qc_rule_frequency: str
    tea_percent: float
    bias_percent: float
    cv_percent: float


class MetrologyEngine:
    """
    Metrology calculations engine for Clinical Laboratory SQC (Six Sigma & Bias/CV).
    """

    @staticmethod
    def calculate_bias(mean: float, target_mean: float) -> float:
        if target_mean == 0:
            raise ValueError("Target mean cannot be zero.")
        return ((mean - target_mean) / target_mean) * 100.0

    @staticmethod
    def calculate_cv(sd: float, mean: float) -> float:
        if mean == 0:
            raise ValueError("Mean cannot be zero.")
        return (sd / mean) * 100.0

    @staticmethod
    def calculate_sigma(tea_percent: float, bias_percent: float, cv_percent: float) -> SigmaResult:
        if cv_percent <= 0:
            raise ValueError("CV% must be greater than 0.")

        sigma = (tea_percent - abs(bias_percent)) / cv_percent
        sigma_rounded = round(sigma, 2)

        if sigma_rounded >= 6.0:
            tier = "World Class"
            protocol = "Single 1_3s rule (1 QC run per analytical batch)"
        elif sigma_rounded >= 5.0:
            tier = "Excellent"
            protocol = "1_3s / 2_2s / R_4s cascade (1-2 QC runs per batch)"
        elif sigma_rounded >= 4.0:
            tier = "Good"
            protocol = "Full cascade: 1_3s / 2_2s / R_4s / 4_1s (2 QC runs per batch)"
        elif sigma_rounded >= 3.0:
            tier = "Marginal"
            protocol = "Full multirule cascade + increased QC frequency (4 QC runs per batch)"
        else:
            tier = "Unacceptable"
            protocol = "Halt patient testing, recalibrate and troubleshoot"

        return SigmaResult(
            sigma_metric=sigma_rounded,
            quality_tier=tier,
            recommended_qc_rule_frequency=protocol,
            tea_percent=tea_percent,
            bias_percent=bias_percent,
            cv_percent=cv_percent,
        )
