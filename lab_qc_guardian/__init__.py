"""
Lab-QC-Guardian v2.0
Statistical Quality Control & Metrology Engine for Clinical Laboratories.
"""

from .engine import (
    WestgardEngine,
    ControlTarget,
    QCPoint,
    RuleViolation,
    RuleViolationType,
    ActionStatus,
    RunEvaluationResult,
)
from .metrics import (
    MetrologyEngine,
    QCStatistics,
    SigmaEvaluation,
    QualityTier,
)
from .visualizer import LeveyJenningsPlotter

__version__ = "2.0.0"
__author__ = "Matthew Jakubowski"
__all__ = [
    "WestgardEngine",
    "ControlTarget",
    "QCPoint",
    "RuleViolation",
    "RuleViolationType",
    "ActionStatus",
    "RunEvaluationResult",
    "MetrologyEngine",
    "QCStatistics",
    "SigmaEvaluation",
    "QualityTier",
    "LeveyJenningsPlotter",
]
