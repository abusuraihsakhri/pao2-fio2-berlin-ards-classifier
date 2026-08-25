# PaO2/FiO2 Ratio & Berlin ARDS Classifier

Real clinical calculators for respiratory failure assessment. Stdlib-only Python.

## Calculators

| Calculator | Formula | Reference |
|:-----------|:--------|:----------|
| **P/F Ratio** | PaO2 / FiO2 | Common ICU metric |
| **Berlin ARDS** | Mild: P/F 201-300, Moderate: 101-200, Severe: ≤100 (PEEP ≥5) | ARDS Definition Task Force, JAMA 2012 |
| **Oxygenation Index** | (FiO2 × MAP × 100) / PaO2 | Pediatric critical care |
| **A-a Gradient** | (FiO2 × (Patm - PH2O)) - (PaO2 + PaCO2/0.8) | Standard gas equation |
| **Normal A-a** | (Age/4) + 4 | Age-adjusted reference |
| **SpO2/FiO2** | SpO2 / FiO2 (surrogate for P/F) | Rice et al., Chest 2005 |
| **PaO2 from SpO2** | Severinghaus approximation | Oxyhemoglobin dissociation curve |

## Quick Start

```bash
# Full respiratory assessment
python pf_ratio_ards.py single --pao2 80 --fio2 0.5 --paco2 40 --peep 10 --age 65 --spo2 95

# P/F ratio only
python pf_ratio_ards.py pf --pao2 100 --fio2 0.5

# Berlin classification
python pf_ratio_ards.py berlin --pao2 60 --fio2 0.4 --peep 10

# Batch CSV processing
python pf_ratio_ards.py batch -i patients.csv -o results.csv
```

## Python API

```python
from pf_ratio_ards import (
    pf_ratio, berlin_ards_classification, oxygenation_index,
    a_a_gradient, estimate_pao2_from_spo2, comprehensive_respiratory_assessment,
)

# P/F ratio
pf = pf_ratio(80.0, 0.5)  # 160.0

# Berlin classification
result = berlin_ards_classification(60.0, 0.4, peep=10.0)
# {"pf_ratio": 150.0, "severity": "Moderate ARDS (P/F 101-200)", ...}

# Full assessment
res = comprehensive_respiratory_assessment(
    pao2=80, fio2=0.5, paco2=40, peep=10, map_pressure=15, age=65, spo2=95
)
```

## Tests

```bash
python -m pytest test_pf_ratio_ards.py -v
```

## License

MIT
