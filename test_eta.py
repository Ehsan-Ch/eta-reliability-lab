import unittest
from build import ROOT, render
from eta import GROUPS, calibrate, conformal_radius, evaluate, experiment, fit_point, voyages


class ETATests(unittest.TestCase):
    def test_calibration_rank_and_small_sample(self):
        self.assertEqual(conformal_radius(list(range(1, 20)), 90), 18)
        with self.assertRaises(ValueError):
            conformal_radius([1, 2], 95)

    def test_interval_bounds_and_inclusive_coverage(self):
        r = {"plan": 3, "observed": 5, "group": "short", "weather": "fair", "queue": "light"}
        radii = {m: {"short": 2} for m in ("fixed", "pooled", "grouped")}
        c = evaluate([r], {("short", "fair", "light"): 0}, radii)[0]
        self.assertEqual(c["intervals"]["fixed"], {"lower": 1, "upper": 5, "width": 4, "covered": True})

    def test_increasing_nominal_levels_do_not_narrow_intervals(self):
        training = voyages(102, 1800)
        calibration = voyages(203, 900)
        fitted = fit_point(training)
        lower = calibrate(calibration, fitted, 80)
        upper = calibrate(calibration, fitted, 95)
        for method in lower:
            for group in GROUPS:
                self.assertLessEqual(lower[method][group], upper[method][group])

    def test_groups_reconcile_to_overall(self):
        for level in experiment()["levels"].values():
            for profile in level["profiles"].values():
                for method, total in profile["all"]["metrics"].items():
                    for key in ("covered", "count"):
                        self.assertEqual(total[key], sum(profile[g]["metrics"][method][key] for g in GROUPS))

    def test_committed_report_reproduces(self):
        self.assertEqual((ROOT / "index.html").read_text(encoding="utf-8"), render())
