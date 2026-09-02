# Pao2 Fio2 Berlin ARDS Classifier

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

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

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`pf_ratio()`**: Calculate PaO2/FiO2 ratio.

Args:
    pao2: Arterial oxygen partial pressure in mmHg.
    fio2: Fraction of inspired oxygen (0.0 - 1.0).

Returns:
    P/F ratio as a float.

Raises:
    ValueError: If fio2 <= 0 or pao2 < 0.
- **`spo2_fio2_ratio()`**: Calculate SpO2/FiO2 ratio (surrogate for P/F ratio).

Normal ~476 when SpO2=100%, FiO2=0.21.

Args:
    spo2: Oxygen saturation percentage (0-100).
    fio2: Fraction of inspired oxygen (0.0 - 1.0).

Returns:
    S/F ratio.
- **`estimate_pao2_from_spo2()`**: Estimate PaO2 from SpO2 using a clinical approximation of the
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
- **`estimate_pf_from_spo2_fio2()`**: Estimate P/F ratio from SpO2 and FiO2.

First estimates PaO2 from SpO2, then computes P/F.

Args:
    spo2: Oxygen saturation percentage (0-100).
    fio2: Fraction of inspired oxygen (0.0 - 1.0).

Returns:
    Estimated P/F ratio.
- **`oxygenation_index()`**: Calculate Oxygenation Index (OI).

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

---

## 📐 Mathematical Formulation & Logic

```text
  """Calculate PaO2/FiO2 ratio.
  """Calculate SpO2/FiO2 ratio (surrogate for P/F ratio).
  """Calculate Oxygenation Index (OI).
  return (fio2 * map_pressure * 100.0) / pao2
  """Calculate A-a (alveolar-arterial) oxygen gradient.
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --input data.csv
```

### Parameter Reference
- `--interactive`: Launch guided terminal interactive wizard.
- `--input <path>`: Evaluate input from JSON or CSV specification.
- `--json`: Output deterministic structured results in JSON format.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Parameter / observation metric | Required |
| `v1` | Parameter / observation metric | Required |
| `v2` | Parameter / observation metric | Required |
| `v3` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t pao2-fio2-berlin-ards-classifier .
docker run -p 8000:8000 pao2-fio2-berlin-ards-classifier
```
