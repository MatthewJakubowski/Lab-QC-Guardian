"""
Lab-QC-Guardian v2.0 - Demonstration Runner
Executes multi-level Westgard multirule cascade, Six Sigma evaluation, and generates Levey-Jennings charts.
"""

from lab_qc_guardian import (
    ControlTarget,
    LeveyJenningsPlotter,
    MetrologyEngine,
    WestgardEngine,
)


def run_demo():
    print("=" * 60)
    print("🧪 Lab-QC-Guardian v2.0 | SQC & Clinical Metrology Engine")
    print("=" * 60)

    # 1. Definicja parametrów docelowych dla dwóch poziomów (np. Glukoza)
    targets = {
        "Level 1 (Normal)": ControlTarget(level="Level 1 (Normal)", target_mean=100.0, target_sd=2.0),
        "Level 2 (Pathological)": ControlTarget(level="Level 2 (Pathological)", target_mean=200.0, target_sd=4.0),
    }

    engine = WestgardEngine(targets=targets, window_size=15)

    # 2. Przykładowa seria pomiarowa z symulacją dryfu i naruszeń
    qc_runs = [
        {"Level 1 (Normal)": 99.5, "Level 2 (Pathological)": 198.5},
        {"Level 1 (Normal)": 100.8, "Level 2 (Pathological)": 201.2},
        {"Level 1 (Normal)": 101.5, "Level 2 (Pathological)": 203.0},
        {"Level 1 (Normal)": 104.5, "Level 2 (Pathological)": 202.0},  # 1_2s Ostrzeżenie na Level 1 (+2.25 SD)
        {"Level 1 (Normal)": 104.8, "Level 2 (Pathological)": 201.5},  # 2_2s Odrzucenie na Level 1 (2x > +2 SD)
        {"Level 1 (Normal)": 107.2, "Level 2 (Pathological)": 200.0},  # 1_3s Odrzucenie na Level 1 (+3.6 SD)
    ]

    print("\n[1/3] Ewaluacja kaskady reguł Westgarda w oknie kroczącym:")
    all_violations = []
    for run_idx, run_data in enumerate(qc_runs, start=1):
        result = engine.evaluate_run(run_data)
        status_icon = "❌" if result.is_rejected else ("⚠️" if result.violations else "✅")
        print(f"\nSeria #{result.run_id} {status_icon} Status: {result.status.value}")
        print(f"   z-scores: {result.level_z_scores}")

        if result.violations:
            for v in result.violations:
                all_violations.append(v)
                print(f"   └─ [{v.rule_name}] Typ: {v.violation_type.value} | Poziom: {v.affected_level}")
                print(f"      Opis: {v.description}")

    # 3. Analiza metrologiczna Six Sigma (dla danych Level 1)
    print("\n" + "=" * 60)
    print("[2/3] Ewaluacja Metrologiczna Six Sigma:")
    l1_values = [r["Level 1 (Normal)"] for r in qc_runs]
    sigma_eval = MetrologyEngine.evaluate_six_sigma(
        analyte_name="Glukoza",
        level_name="Level 1 (Normal)",
        values=l1_values,
        target_mean=100.0,
        tea_percent=6.0,  # Dopuszczalny Błąd Całkowity wg CLIA/RiliBÄK
    )

    print(f"Analit: {sigma_eval.analyte_name} | Poziom: {sigma_eval.level_name}")
    print(f"Średnia: {sigma_eval.calculated_mean:.2f} mg/dL (Docelowa: {sigma_eval.target_mean:.2f})")
    print(f"CV%: {sigma_eval.cv_percent:.2f}% | Bias%: {sigma_eval.bias_percent:+.2f}%")
    print(f"Sigma Metric: {sigma_eval.sigma_metric:.2f}σ -> Kategoria: {sigma_eval.quality_tier.value}")
    print(f"Rekomendacja QC: {sigma_eval.recommended_qc_rule_frequency}")

    # 4. Generowanie wykresu Leveya-Jenningsa
    print("\n" + "=" * 60)
    print("[3/3] Generowanie karty kontrolnej Leveya-Jenningsa...")
    plotter = LeveyJenningsPlotter(targets=targets, dark_mode=False)
    plotter.plot_level(
        level_name="Level 1 (Normal)",
        points=engine.history["Level 1 (Normal)"],
        violations=all_violations,
        analyte_name="Glukoza",
        unit="mg/dL",
        save_path="wykres_qc.png",
    )
    print("✅ Wykres zapisany pomyślnie jako 'wykres_qc.png'.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
