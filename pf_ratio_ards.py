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


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def pf_ratio(pao2: float, fio2: float) -> float:
    """Calculate PaO2/FiO2 ratio.

    Args:
        pao2: Arterial oxygen partial pressure in mmHg.
        fio2: Fraction of inspired oxygen (0.0 - 1.0).

    Returns:
        P/F ratio as a float.

    Raises:
        ValueError: If fio2 <= 0 or pao2 < 0.
    """
    if fio2 <= 0:
        raise ValueError("FiO2 must be > 0")
    if pao2 < 0:
        raise ValueError("PaO2 must be >= 0")
    return pao2 / fio2


def spo2_fio2_ratio(spo2: float, fio2: float) -> float:
    """Calculate SpO2/FiO2 ratio (surrogate for P/F ratio).

    Normal ~476 when SpO2=100%, FiO2=0.21.

    Args:
        spo2: Oxygen saturation percentage (0-100).
        fio2: Fraction of inspired oxygen (0.0 - 1.0).

    Returns:
        S/F ratio.
    """
    if fio2 <= 0:
        raise ValueError("FiO2 must be > 0")
    if spo2 < 0 or spo2 > 100:
        raise ValueError("SpO2 must be between 0 and 100")
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
    if spo2 < 0 or spo2 > 100:
        raise ValueError("SpO2 must be between 0 and 100")
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
    """Calculate Oxygenation Index (OI).

    OI = (FiO2 * MAP * 100) / PaO2

    Higher OI indicates worse oxygenation. OI > 40 is associated with
    high mortality in pediatric ARDS.

    Args:
        fio2: Fraction of inspired oxygen (0.0 - 1.0).
        map_pressure: Mean airway pressure in cmH2O.
        pao2: Arterial oxygen partial pressure in mmHg.

    Returns:
        Oxygenation Index.

    Raises:
        ValueError: If pao2 <= 0.
    """
    if pao2 <= 0:
        raise ValueError("PaO2 must be > 0 for OI calculation")
    if fio2 < 0 or fio2 > 1:
        raise ValueError("FiO2 must be between 0 and 1")
    if map_pressure < 0:
        raise ValueError("MAP must be >= 0")
    return (fio2 * map_pressure * 100.0) / pao2


def a_a_gradient(
    fio2: float,
    pao2: float,
    paco2: float,
    patm: float = PATM_DEFAULT,
    ph2o: float = PH2O_DEFAULT,
    rq: float = RQ,
) -> float:
    """Calculate A-a (alveolar-arterial) oxygen gradient.

    A-aDO2 = (FiO2 * (Patm - PH2O)) - (PaO2 + PaCO2 / RQ)

    Args:
        fio2: Fraction of inspired oxygen (0.0 - 1.0).
        pao2: Arterial O2 partial pressure (mmHg).
        paco2: Arterial CO2 partial pressure (mmHg).
        patm: Atmospheric pressure (mmHg). Default 760.
        ph2o: Water vapour pressure (mmHg). Default 47.
        rq: Respiratory quotient. Default 0.8.

    Returns:
        A-a gradient in mmHg.
    """
    pao2_alveolar = fio2 * (patm - ph2o) - (paco2 / rq)
    return pao2_alveolar - pao2


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
    """Classify ARDS severity per the Berlin Definition (2012).

    The Berlin definition requires:
    - Acute onset (within 1 week of known insult)
    - Bilateral opacities on imaging (not fully explained by effusions/atelectasis)
    - Respiratory failure not fully explained by cardiac failure/fluid overload
    - P/F ratio measured with PEEP >= 5 cmH2O

    This function classifies based on P/F ratio and optionally validates PEEP.

    Args:
        pao2: Arterial O2 partial pressure (mmHg).
        fio2: Fraction of inspired oxygen (0.0 - 1.0).
        peep: Positive end-expiratory pressure (cmH2O). If provided and < 5,
              a warning is included since Berlin requires PEEP >= 5.

    Returns:
        Dict with keys: pf_ratio, severity, peep_warning, meets_peep_criteria.
    """
    pf = pf_ratio(pao2, fio2)

    peep_warning = None
    meets_peep = True
    if peep is not None and peep < 5.0:
        peep_warning = (
            f"PEEP {peep} cmH2O is below the Berlin minimum of 5 cmH2O. "
            "Classification may not be valid per Berlin definition."
        )
        meets_peep = False

    if pf > 300:
        severity = "No ARDS (P/F > 300)"
    elif pf > 200:
        severity = "Mild ARDS (P/F 201-300)"
    elif pf > 100:
        severity = "Moderate ARDS (P/F 101-200)"
    else:
        severity = "Severe ARDS (P/F <= 100)"

    return {
        "pf_ratio": round(pf, 1),
        "severity": severity,
        "peep_warning": peep_warning,
        "meets_peep_criteria": meets_peep,
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
    """Process a CSV of patient respiratory data and write results.

    Expected columns: pao2, fio2, paco2
    Optional columns: peep, map, age, spo2, patm, patient_id

    Returns number of records processed.
    """
    results: List[Dict[str, Any]] = []
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pao2 = float(row["pao2"])
            fio2_val = float(row["fio2"])
            paco2 = float(row["paco2"])
            peep = float(row["peep"]) if "peep" in row and row["peep"] else None
            map_p = float(row["map"]) if "map" in row and row["map"] else None
            age = float(row["age"]) if "age" in row and row["age"] else None
            spo2 = float(row["spo2"]) if "spo2" in row and row["spo2"] else None
            patm = float(row["patm"]) if "patm" in row and row["patm"] else PATM_DEFAULT
            pid = row.get("patient_id", "")

            res = comprehensive_respiratory_assessment(
                pao2, fio2_val, paco2, peep=peep, map_pressure=map_p,
                age=age, spo2=spo2, patm=patm,
            )
            res["patient_id"] = pid
            results.append(res)

    fieldnames = list(results[0].keys()) if results else []
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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
