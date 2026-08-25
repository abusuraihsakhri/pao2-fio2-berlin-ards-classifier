#!/usr/bin/env python3
"""Tests for PaO2/FiO2 Ratio & Berlin ARDS Classifier.

Run with: python -m pytest test_pf_ratio_ards.py -v
    or:   python test_pf_ratio_ards.py
"""
import json
import math
import os
import sys
import tempfile
import unittest

from pf_ratio_ards import (
    pf_ratio,
    spo2_fio2_ratio,
    estimate_pao2_from_spo2,
    estimate_pf_from_spo2_fio2,
    oxygenation_index,
    a_a_gradient,
    normal_a_a_gradient,
    berlin_ards_classification,
    comprehensive_respiratory_assessment,
    process_csv,
    main,
)


class TestPFRatio(unittest.TestCase):
    """Test P/F ratio calculation."""

    def test_normal_room_air(self):
        """Normal PaO2 100 on room air (FiO2 0.21) gives ~476."""
        result = pf_ratio(100.0, 0.21)
        self.assertAlmostEqual(result, 476.2, delta=1.0)

    def test_high_fio2(self):
        """PaO2 200 on FiO2 1.0 gives 200."""
        self.assertAlmostEqual(pf_ratio(200.0, 1.0), 200.0)

    def test_zero_pao2(self):
        """PaO2 0 gives ratio 0."""
        self.assertAlmostEqual(pf_ratio(0.0, 0.5), 0.0)

    def test_fio2_zero_raises(self):
        """FiO2 of 0 must raise ValueError."""
        with self.assertRaises(ValueError):
            pf_ratio(100.0, 0.0)

    def test_negative_pao2_raises(self):
        """Negative PaO2 must raise ValueError."""
        with self.assertRaises(ValueError):
            pf_ratio(-10.0, 0.5)

    def test_moderate_ards(self):
        """P/F of 150 (moderate ARDS range)."""
        result = pf_ratio(60.0, 0.4)
        self.assertAlmostEqual(result, 150.0)


class TestSpO2FiO2Ratio(unittest.TestCase):
    """Test SpO2/FiO2 ratio."""

    def test_normal(self):
        """SpO2 100% on room air: S/F ~476."""
        result = spo2_fio2_ratio(100.0, 0.21)
        self.assertAlmostEqual(result, 476.2, delta=1.0)

    def test_low_spo2(self):
        """SpO2 80% on 50% O2: S/F = 160."""
        self.assertAlmostEqual(spo2_fio2_ratio(80.0, 0.5), 160.0)

    def test_invalid_spo2(self):
        """SpO2 > 100 raises ValueError."""
        with self.assertRaises(ValueError):
            spo2_fio2_ratio(105.0, 0.5)


class TestEstimatePaO2(unittest.TestCase):
    """Test PaO2 estimation from SpO2."""

    def test_spo2_100(self):
        """SpO2 100% should estimate PaO2 around 100+ mmHg."""
        result = estimate_pao2_from_spo2(100.0)
        self.assertGreater(result, 80.0)

    def test_spo2_95(self):
        """SpO2 95% should estimate PaO2 around 80 mmHg."""
        result = estimate_pao2_from_spo2(95.0)
        self.assertGreater(result, 60.0)
        self.assertLess(result, 120.0)

    def test_spo2_90(self):
        """SpO2 90% should estimate PaO2 around 60 mmHg."""
        result = estimate_pao2_from_spo2(90.0)
        self.assertGreater(result, 40.0)
        self.assertLess(result, 80.0)

    def test_spo2_50_low_range(self):
        """SpO2 50% uses steep portion approximation."""
        result = estimate_pao2_from_spo2(50.0)
        self.assertAlmostEqual(result, 27.0)

    def test_spo2_0(self):
        """SpO2 0% gives PaO2 0."""
        self.assertAlmostEqual(estimate_pao2_from_spo2(0.0), 0.0)

    def test_invalid_spo2(self):
        with self.assertRaises(ValueError):
            estimate_pao2_from_spo2(110.0)


class TestOxygenationIndex(unittest.TestCase):
    """Test Oxygenation Index."""

    def test_normal(self):
        """OI with normal values."""
        result = oxygenation_index(0.4, 15.0, 100.0)
        self.assertAlmostEqual(result, 6.0)

    def test_high_oi(self):
        """High OI indicates poor oxygenation."""
        result = oxygenation_index(1.0, 25.0, 50.0)
        self.assertAlmostEqual(result, 50.0)

    def test_zero_pao2_raises(self):
        with self.assertRaises(ValueError):
            oxygenation_index(0.5, 15.0, 0.0)


class TestAGradient(unittest.TestCase):
    """Test A-a gradient calculations."""

    def test_room_air_normal(self):
        """Normal young adult on room air."""
        # PAO2 = 0.21*(760-47) - 40/0.8 = 0.21*713 - 50 = 149.73 - 50 = 99.73
        # A-a = 99.73 - 95 = 4.73
        result = a_a_gradient(0.21, 95.0, 40.0)
        self.assertAlmostEqual(result, 4.73, delta=0.5)

    def test_high_fio2(self):
        """A-a gradient increases with higher FiO2."""
        result = a_a_gradient(1.0, 400.0, 40.0)
        # PAO2 = 1.0*(760-47) - 40/0.8 = 713 - 50 = 663
        # A-a = 663 - 400 = 263
        self.assertAlmostEqual(result, 263.0, delta=1.0)

    def test_normal_a_a_young(self):
        """Normal A-a gradient for 20-year-old on room air."""
        result = normal_a_a_gradient(20.0)
        self.assertAlmostEqual(result, 9.0)  # 20/4 + 4 = 9

    def test_normal_a_a_old(self):
        """Normal A-a gradient increases with age."""
        result = normal_a_a_gradient(80.0)
        self.assertAlmostEqual(result, 24.0)  # 80/4 + 4 = 24


class TestBerlinClassification(unittest.TestCase):
    """Test Berlin ARDS classification."""

    def test_no_ards(self):
        """P/F > 300 is not ARDS."""
        result = berlin_ards_classification(400.0, 1.0)
        self.assertIn("No ARDS", result["severity"])

    def test_mild_ards(self):
        """P/F 250 is mild ARDS."""
        result = berlin_ards_classification(125.0, 0.5)
        self.assertAlmostEqual(result["pf_ratio"], 250.0)
        self.assertIn("Mild", result["severity"])

    def test_moderate_ards(self):
        """P/F 150 is moderate ARDS."""
        result = berlin_ards_classification(60.0, 0.4)
        self.assertAlmostEqual(result["pf_ratio"], 150.0)
        self.assertIn("Moderate", result["severity"])

    def test_severe_ards(self):
        """P/F 80 is severe ARDS."""
        result = berlin_ards_classification(40.0, 0.5)
        self.assertAlmostEqual(result["pf_ratio"], 80.0)
        self.assertIn("Severe", result["severity"])

    def test_boundary_mild_moderate(self):
        """P/F exactly 200 is moderate ARDS (Berlin: 101-200)."""
        result = berlin_ards_classification(100.0, 0.5)
        self.assertIn("Moderate", result["severity"])

    def test_boundary_moderate_severe(self):
        """P/F exactly 100 is severe ARDS (Berlin: <=100)."""
        result = berlin_ards_classification(50.0, 0.5)
        self.assertIn("Severe", result["severity"])

    def test_peep_warning(self):
        """PEEP below 5 should generate a warning."""
        result = berlin_ards_classification(60.0, 0.4, peep=3.0)
        self.assertIsNotNone(result["peep_warning"])
        self.assertFalse(result["meets_peep_criteria"])

    def test_peep_adequate(self):
        """PEEP >= 5 should not generate a warning."""
        result = berlin_ards_classification(60.0, 0.4, peep=10.0)
        self.assertIsNone(result["peep_warning"])
        self.assertTrue(result["meets_peep_criteria"])


class TestComprehensiveAssessment(unittest.TestCase):
    """Test comprehensive respiratory assessment."""

    def test_full_assessment(self):
        """Full assessment with all parameters."""
        result = comprehensive_respiratory_assessment(
            pao2=80.0, fio2=0.5, paco2=40.0, peep=10.0,
            map_pressure=15.0, age=65.0, spo2=95.0,
        )
        self.assertIn("pf_ratio", result)
        self.assertIn("severity", result)
        self.assertIn("a_a_gradient", result)
        self.assertIn("oxygenation_index", result)
        self.assertIn("spo2_fio2_ratio", result)
        self.assertIn("estimated_pao2_from_spo2", result)
        self.assertAlmostEqual(result["pf_ratio"], 160.0)

    def test_minimal_assessment(self):
        """Assessment with only required parameters."""
        result = comprehensive_respiratory_assessment(
            pao2=100.0, fio2=0.21, paco2=40.0,
        )
        self.assertIn("pf_ratio", result)
        self.assertIn("a_a_gradient", result)
        self.assertNotIn("oxygenation_index", result)


class TestBatchProcessing(unittest.TestCase):
    """Test CSV batch processing."""

    def test_batch_csv(self):
        """Process a CSV file with multiple patients."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inp = os.path.join(tmpdir, "in.csv")
            out = os.path.join(tmpdir, "out.csv")
            with open(inp, "w") as f:
                f.write("patient_id,pao2,fio2,paco2,peep\n")
                f.write("P001,80,0.5,40,10\n")
                f.write("P002,200,1.0,35,5\n")
                f.write("P003,50,0.6,45,8\n")
            n = process_csv(inp, out)
            self.assertEqual(n, 3)
            self.assertTrue(os.path.exists(out))


class TestCLI(unittest.TestCase):
    """Test CLI interface."""

    def test_pf_command(self):
        """Test 'pf' subcommand."""
        ret = main(["pf", "--pao2", "100", "--fio2", "0.5"])
        self.assertEqual(ret, 0)

    def test_berlin_command(self):
        """Test 'berlin' subcommand."""
        ret = main(["berlin", "--pao2", "60", "--fio2", "0.4", "--peep", "10"])
        self.assertEqual(ret, 0)

    def test_single_command(self):
        """Test 'single' subcommand."""
        ret = main(["single", "--pao2", "80", "--fio2", "0.5", "--paco2", "40"])
        self.assertEqual(ret, 0)

    def test_no_command(self):
        """No command returns 1."""
        ret = main([])
        self.assertEqual(ret, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
