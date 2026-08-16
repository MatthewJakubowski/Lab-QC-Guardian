"""
Lab-QC-Guardian v2.0 - Levey-Jennings Visualization Engine
Generates multi-level Levey-Jennings control charts with highlighted Westgard rule violations.
"""

from __future__ import annotations

from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from .engine import ControlTarget, QCPoint, RuleViolation


class LeveyJenningsPlotter:
    """Moduł renderujący wykresy Leveya-Jenningsa dla kontroli jedno- i wielopoziomowych."""

    def __init__(self, targets: Dict[str, ControlTarget], dark_mode: bool = False):
        self.targets = targets
        self.dark_mode = dark_mode
        self._setup_style()

    def _setup_style(self) -> None:
        if self.dark_mode:
            plt.style.use("dark_background")
            self.bg_color = "#121212"
            self.grid_color = "#2a2a2a"
            self.text_color = "#e0e0e0"
            self.mean_color = "#00e676"
            self.sd2_color = "#ffb74d"
            self.sd3_color = "#ff5252"
        else:
            plt.style.use("default")
            self.bg_color = "#ffffff"
            self.grid_color = "#e8e8e8"
            self.text_color = "#212121"
            self.mean_color = "#2e7d32"
            self.sd2_color = "#f57c00"
            self.sd3_color = "#d32f2f"

    def plot_level(
        self,
        level_name: str,
        points: List[QCPoint],
        violations: Optional[List[RuleViolation]] = None,
        analyte_name: str = "Analit",
        unit: str = "mg/dL",
        save_path: Optional[str] = None,
    ) -> plt.Figure:
        """Generuje kartę kontrolną dla pojedynczego poziomu."""
        if level_name not in self.targets:
            raise KeyError(f"Poziom '{level_name}' nie posiada zdefiniowanego celu (ControlTarget).")

        target = self.targets[level_name]
        mean = target.target_mean
        sd = target.target_sd

        fig, ax = plt.subplots(figsize=(12, 6), dpi=120)
        fig.patch.set_facecolor(self.bg_color)
        ax.set_facecolor(self.bg_color)

        runs = [p.run_id for p in points]
        values = [p.value for p in points]

        # 1. Linie statystyczne SD
        sd_lines = [
            (mean + 3 * sd, "+3 SD", self.sd3_color, ":"),
            (mean + 2 * sd, "+2 SD", self.sd2_color, "--"),
            (mean + 1 * sd, "+1 SD", "#9e9e9e", "-."),
            (mean, f"Średnia ({mean:.2f})", self.mean_color, "-"),
            (mean - 1 * sd, "-1 SD", "#9e9e9e", "-."),
            (mean - 2 * sd, "-2 SD", self.sd2_color, "--"),
            (mean - 3 * sd, "-3 SD", self.sd3_color, ":"),
        ]

        for val, label, col, ls in sd_lines:
            lw = 1.6 if val == mean else (1.2 if "3 SD" in label or "2 SD" in label else 0.8)
            ax.axhline(val, color=col, linestyle=ls, linewidth=lw, alpha=0.85, label=label)

        # 2. Punkty pomiarowe
        ax.plot(runs, values, color="#1976d2", marker="o", markersize=6, linewidth=1.5, label="Wyniki QC", zorder=3)

        # 3. Oznaczenie naruszeń reguł
        if violations:
            violation_runs = set()
            for v in violations:
                if v.affected_level in (level_name, "Multi-Level") or level_name in v.affected_level:
                    for r_idx in v.run_indices:
                        violation_runs.add(r_idx)

            v_points = [p for p in points if p.run_id in violation_runs]
            if v_points:
                ax.scatter(
                    [p.run_id for p in v_points],
                    [p.value for p in v_points],
                    color="#d50000",
                    s=120,
                    edgecolors="#ffffff",
                    linewidth=1.5,
                    zorder=5,
                    label="Naruszenie reguły",
                )

        # 4. Formatowanie osi i opisów
        ax.set_title(
            f"Karta Kontrolna Leveya-Jenningsa — {analyte_name} [{level_name}]\n(Wartości docelowe: Śr = {mean:.2f} {unit}, SD = {sd:.2f})",
            fontsize=13,
            fontweight="bold",
            color=self.text_color,
            pad=14,
        )
        ax.set_xlabel("Numer serii analitycznej (Run ID)", fontsize=10, color=self.text_color, labelpad=8)
        ax.set_ylabel(f"Stężenie ({unit})", fontsize=10, color=self.text_color, labelpad=8)

        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.grid(True, linestyle=":", alpha=0.6, color=self.grid_color)
        ax.tick_params(colors=self.text_color)

        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=True, fontsize=9)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=300)

        return fig
