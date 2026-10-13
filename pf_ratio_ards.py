#!/usr/bin/env python3
"""
PaO2/FiO2 Ratio & Berlin ARDS Classifier
==========================================
Real clinical calculators for respiratory failure assessment:

- P/F Ratio = PaO2 / FiO2
- Berlin ARDS Definition (2012):
    Mild:     P/F 201-300  (with PEEP >= 5 cmH2O)
    Moderate: P/F 101-200  (with PEEP >= 5 cmH2O)
    Severe:   P/F <= 100   (with PEEP >= 5 cmH2O)
- Oxygenation Index (OI) = (FiO2 * MAP * 100) / PaO2
- A-a Gradient: A-aDO2 = (FiO2 * (Patm - PH2O)) - (PaO2 + PaCO2 / 0.8)
  Normal A-aDO2 = (Age / 4) + 4
- SpO2/FiO2 ratio (surrogate for P/F)
- Estimated PaO2 from SpO2 (Severinghaus-like estimation)

Stdlib only. Author: Dr. Abu Suraih Sakhri. License: MIT.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PATM_DEFAULT = 760.0   # mmHg, standard atmospheric pressure at sea level
PH2O_DEFAULT = 47.0    # mmHg, water vapour pressure at 37 C
RQ = 0.8               # respiratory quotient

def _finite(name: str, value: float, minimum: float | None = None,
            maximum: float | None = None, strict_min: bool = False) -> None:
    """Reject non-finite values and measurements outside accepted ranges."""
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if minimum is not None and (value <= minimum if strict_min else value < minimum):
        op = ">" if strict_min else ">="
        raise ValueError(f"{name} must be {op} {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")


def _oxygen_fraction(fio2: float) -> None:
    _finite("FiO2", fio2, 0, 1, strict_min=True)


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def pf_ratio(pao2: float, fio2: float) -> float:
    """Calculate PaO2 / FiO2 with PaO2 in mmHg and FiO2 as a fraction."""
    _finite("PaO2", pao2, 0)
    _oxygen_fraction(fio2)
    return pao2 / fio2

def spo2_fio2_ratio(spo2: float, fio2: float) -> float:
    """Compute SpO2/FiO2; clinical interpretation is limited at high SpO2."""
    _finite("SpO2", spo2, 0, 100)
    _oxygen_fraction(fio2)
    return spo2 / fio2

def estimate_pao2_from_spo2(spo2: float) -> float:
    """Estimate PaO2 from SpO2 using a clinical approximation of the
    oxyhemoglobin dissociation curve (Severinghaus-derived).

    Piecewise linear approximation based on standard curve data points:
        SpO2 90% -> PaO2 ~60 mmHg
        SpO2 95% -> PaO2 ~80 mmHg
        SpO2 100% -> PaO2 ~100 mmHg

    For SpO2 < 90%, uses the steep portion of the curve.

    Args:
        spo2: Oxygen saturation percentage (0-100).

    Returns:
        Estimated PaO2 in mmHg.
    """
    _finite("SpO2", spo2, 0, 100)
    if spo2 >= 90.0:
        # Flat portion: PaO2 ~60 at SpO2 90, ~100 at SpO2 100
        return 60.0 + (spo2 - 90.0) * 4.0
    elif spo2 >= 80.0:
        return 44.0 + (spo2 - 80.0) * 1.6
    elif spo2 >= 70.0:
        return 37.0 + (spo2 - 70.0) * 0.7
    elif spo2 >= 50.0:
        return 27.0 + (spo2 - 50.0) * 0.5
    else:
        return max(0.0, spo2 * 0.4)


def estimate_pf_from_spo2_fio2(spo2: float, fio2: float) -> float:
    """Estimate P/F ratio from SpO2 and FiO2.

    First estimates PaO2 from SpO2, then computes P/F.

    Args:
        spo2: Oxygen saturation percentage (0-100).
        fio2: Fraction of inspired oxygen (0.0 - 1.0).

    Returns:
        Estimated P/F ratio.
    """
    pao2_est = estimate_pao2_from_spo2(spo2)
    return pf_ratio(pao2_est, fio2)


def oxygenation_index(fio2: float, map_pressure: float, pao2: float) -> float:
    """Oxygenation Index = FiO2 * mean airway pressure * 100 / PaO2."""
    _oxygen_fraction(fio2)
    _finite("MAP", map_pressure, 0)
    _finite("PaO2", pao2, 0, strict_min=True)
    return (fio2 * map_pressure * 100.0) / pao2

def a_a_gradient(
    fio2: float, pao2: float, paco2: float,
    patm: float = PATM_DEFAULT, ph2o: float = PH2O_DEFAULT,
    rq: float = RQ,
) -> float:
    """Simplified alveolar gas equation (fixed respiratory quotient)."""
    _oxygen_fraction(fio2)
    _finite("PaO2", pao2, 0)
    _finite("PaCO2", paco2, 0)
    _finite("Patm", patm, 0, strict_min=True)
    _finite("PH2O", ph2o, 0)
    _finite("RQ", rq, 0, strict_min=True)
    if ph2o >= patm:
        raise ValueError("PH2O must be less than Patm")
    return fio2 * (patm - ph2o) - paco2 / rq - pao2

def normal_a_a_gradient(age: float, fio2: float = 0.21) -> float:
    """Calculate expected normal A-a gradient for age.

    Normal A-aDO2 = (Age / 4) + 4  (on room air, FiO2 0.21)

    On supplemental O2, the expected gradient increases. A common
    adjustment is to add ~5-7 mmHg for each 10% increase in FiO2 above 0.21.

    Args:
        age: Patient age in years.
        fio2: Fraction of inspired oxygen. Default 0.21 (room air).

    Returns:
        Expected normal A-a gradient in mmHg.
    """
    _finite("Age", age, 0)
    _oxygen_fraction(fio2)
    base = (age / 4.0) + 4.0
    # Adjustment for supplemental O2
    if fio2 > 0.21:
        base += (fio2 - 0.21) / 0.1 * 5.0
    return base


def berlin_ards_classification(
    pao2: float,
    fio2: float,
    peep: Optional[float] = None,
) -> Dict[str, Any]:
    """Return Berlin oxygenation range, not a confirmed clinical diagnosis."""
    pf = pf_ratio(pao2, fio2)
    if peep is not None:
        _finite("PEEP", peep, 0)
    if pf > 300:
        severity = "No ARDS (P/F > 300)"
    elif pf > 200:
        severity = "Mild ARDS oxygenation range (200 < P/F <= 300)"
    elif pf > 100:
        severity = "Moderate ARDS oxygenation range (100 < P/F <= 200)"
    else:
        severity = "Severe ARDS oxygenation range (P/F <= 100)"

    meets_peep = peep is not None and peep >= 5
    if peep is None:
        warning = "PEEP/CPAP not supplied; Berlin positive-pressure criterion unverified."
    elif peep < 5:
        warning = f"PEEP/CPAP {peep} cmH2O is below the Berlin minimum of 5 cmH2O."
    else:
        warning = None

    return {
        "pf_ratio": round(pf, 1),
        "severity": severity,
        "peep_warning": warning,
        "meets_peep_criteria": meets_peep,
        "ards_diagnosis_confirmed": False,
        "clinical_criteria_warning": (
            "Oxygenation range alone cannot diagnose ARDS: confirm acute onset, "
            "bilateral opacities, and respiratory failure not primarily cardiac."
        ),
    }

def comprehensive_respiratory_assessment(
    pao2: float,
    fio2: float,
    paco2: float,
    peep: Optional[float] = None,
    map_pressure: Optional[float] = None,
    age: Optional[float] = None,
    spo2: Optional[float] = None,
    patm: float = PATM_DEFAULT,
) -> Dict[str, Any]:
    """Full respiratory assessment combining all calculators.

    Args:
        pao2: Arterial O2 partial pressure (mmHg).
        fio2: Fraction of inspired oxygen (0.0 - 1.0).
        paco2: Arterial CO2 partial pressure (mmHg).
        peep: PEEP in cmH2O (optional).
        map_pressure: Mean airway pressure in cmH2O (optional, for OI).
        age: Patient age in years (optional, for normal A-a gradient).
        spo2: SpO2 percentage (optional, for S/F ratio and estimated P/F).
        patm: Atmospheric pressure (mmHg).

    Returns:
        Dict with all computed metrics.
    """
    result: Dict[str, Any] = {}

    # P/F ratio and Berlin classification
    ards = berlin_ards_classification(pao2, fio2, peep)
    result.update(ards)

    # A-a gradient
    aa = a_a_gradient(fio2, pao2, paco2, patm=patm)
    result["a_a_gradient"] = round(aa, 1)

    if age is not None:
        expected_aa = normal_a_a_gradient(age, fio2)
        result["normal_a_a_gradient"] = round(expected_aa, 1)
        result["a_a_gradient_elevated"] = aa > expected_aa

    # Oxygenation Index
    if map_pressure is not None:
        oi = oxygenation_index(fio2, map_pressure, pao2)
        result["oxygenation_index"] = round(oi, 1)

    # SpO2-based estimates
    if spo2 is not None:
        sf = spo2_fio2_ratio(spo2, fio2)
        result["spo2_fio2_ratio"] = round(sf, 1)
        est_pao2 = estimate_pao2_from_spo2(spo2)
        result["estimated_pao2_from_spo2"] = round(est_pao2, 1)
        est_pf = pf_ratio(est_pao2, fio2)
        result["estimated_pf_from_spo2"] = round(est_pf, 1)

    return result


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_csv(input_path: str, output_path: str) -> int:
    """Process CSV rows, allowing heterogeneous optional output metrics."""
    import os
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("Input and output CSV paths must differ")
    results: List[Dict[str, Any]] = []
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"pao2", "fio2", "paco2"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV requires columns: pao2, fio2, paco2")
        for row_number, row in enumerate(reader, start=2):
            try:
                if None in row:
                    raise ValueError("more cells than CSV header")
                def optional(field: str) -> Optional[float]:
                    value = row.get(field)
                    return float(value) if value is not None and value.strip() else None
                patm = optional("patm")
                res = comprehensive_respiratory_assessment(
                    pao2=float(row["pao2"]),
                    fio2=float(row["fio2"]),
                    paco2=float(row["paco2"]),
                    peep=optional("peep"), map_pressure=optional("map"),
                    age=optional("age"), spo2=optional("spo2"),
                    patm=patm if patm is not None else PATM_DEFAULT,
                )
                res["patient_id"] = row.get("patient_id", "")
                results.append(res)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"Invalid CSV data at row {row_number}: {exc}") from exc

    base_columns = ["patient_id", "pf_ratio", "severity", "peep_warning",
                    "meets_peep_criteria", "ards_diagnosis_confirmed",
                    "clinical_criteria_warning", "a_a_gradient"]
    fields = base_columns + sorted({key for row in results for key in row} - set(base_columns))
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    return len(results)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pf_ratio_ards",
        description="PaO2/FiO2 Ratio & Berlin ARDS Classifier — real clinical calculators.",
    )
    sub = p.add_subparsers(dest="cmd")

    # Single assessment
    s = sub.add_parser("single", help="Single patient respiratory assessment")
    s.add_argument("--pao2", type=float, required=True, help="PaO2 (mmHg)")
    s.add_argument("--fio2", type=float, required=True, help="FiO2 (0.0-1.0)")
    s.add_argument("--paco2", type=float, required=True, help="PaCO2 (mmHg)")
    s.add_argument("--peep", type=float, default=None, help="PEEP (cmH2O)")
    s.add_argument("--map", type=float, default=None, help="Mean airway pressure (cmH2O)")
    s.add_argument("--age", type=float, default=None, help="Patient age (years)")
    s.add_argument("--spo2", type=float, default=None, help="SpO2 (%%)")
    s.add_argument("--patm", type=float, default=PATM_DEFAULT, help="Atmospheric pressure (mmHg)")

    # P/F ratio only
    pf = sub.add_parser("pf", help="Calculate P/F ratio only")
    pf.add_argument("--pao2", type=float, required=True, help="PaO2 (mmHg)")
    pf.add_argument("--fio2", type=float, required=True, help="FiO2 (0.0-1.0)")

    # Berlin classification only
    bc = sub.add_parser("berlin", help="Berlin ARDS classification")
    bc.add_argument("--pao2", type=float, required=True, help="PaO2 (mmHg)")
    bc.add_argument("--fio2", type=float, required=True, help="FiO2 (0.0-1.0)")
    bc.add_argument("--peep", type=float, default=None, help="PEEP (cmH2O)")

    # Batch
    b = sub.add_parser("batch", help="Batch process CSV")
    b.add_argument("-i", "--input", required=True, help="Input CSV path")
    b.add_argument("-o", "--output", default="results.csv", help="Output CSV path")

    # Audit - process a task through the enterprise supervisor
    a = sub.add_parser("audit", help="Run enterprise audit on a task")
    a.add_argument("--task-id", required=True, help="Task identifier")
    a.add_argument("--target", default="AUDIT-TARGET", help="Target identifier")
    a.add_argument("--primary", type=float, default=10.0, help="Primary metric")
    a.add_argument("--secondary", type=float, default=5.0, help="Secondary metric")
    a.add_argument("--descriptor", default="NOMINAL", help="Status descriptor")
    a.add_argument("--critical", action="store_true", help="Critical flag")

    # Chat - supervisory conversational assistant
    c = sub.add_parser("chat", help="Supervisory conversational assistant")
    c.add_argument("query", nargs="+", help="Query text for the supervisor")

    # Verify audit - verify cryptographic audit trail integrity
    sub.add_parser("verify-audit", help="Verify HMAC-SHA256 audit trail integrity")

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "single":
        res = comprehensive_respiratory_assessment(
            pao2=args.pao2, fio2=args.fio2, paco2=args.paco2,
            peep=args.peep, map_pressure=args.map, age=args.age,
            spo2=args.spo2, patm=args.patm,
        )
        print(json.dumps(res, indent=2))
        return 0

    if args.cmd == "pf":
        val = pf_ratio(args.pao2, args.fio2)
        print(json.dumps({"pf_ratio": round(val, 1)}, indent=2))
        return 0

    if args.cmd == "berlin":
        res = berlin_ards_classification(args.pao2, args.fio2, args.peep)
        print(json.dumps(res, indent=2))
        return 0

    if args.cmd == "batch":
        n = process_csv(args.input, args.output)
        print(f"Processed {n} records -> {args.output}")
        return 0

    if args.cmd == "audit":
        from agents.models import SystemTaskPayload
        from agents.supervisor import SystemSupervisor
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.descriptor,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print(json.dumps(dossier.to_dict(), indent=2, default=str))
        return 0

    if args.cmd == "chat":
        from agents.supervisor import SystemSupervisor
        supervisor = SystemSupervisor(model_provider="mock")
        query = " ".join(args.query)
        response = supervisor.query_supervisory_chat(query)
        print(json.dumps({"response": response}, indent=2))
        return 0

    if args.cmd == "verify-audit":
        from agents.base import AuditLogger
        valid = AuditLogger.verify_integrity()
        trail_len = len(AuditLogger.get_trail())
        print(json.dumps({"audit_valid": valid, "trail_length": trail_len}, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
