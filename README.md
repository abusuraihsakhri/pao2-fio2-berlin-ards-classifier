# PaO2/FiO2 Ratio & Berlin ARDS Classifier

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** Berlin Definition (2012), ISO/IEC Quality Frameworks

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Clinical calculators for respiratory failure assessment based on the Berlin ARDS Definition (2012):

- **P/F Ratio** = PaO2 / FiO2
- **Berlin ARDS Classification:**
    - Mild:     P/F 201-300  (with PEEP >= 5 cmH2O)
    - Moderate: P/F 101-200  (with PEEP >= 5 cmH2O)
    - Severe:   P/F <= 100   (with PEEP >= 5 cmH2O)
- **Oxygenation Index (OI)** = (FiO2 * MAP * 100) / PaO2
- **A-a Gradient:** A-aDO2 = (FiO2 * (Patm - PH2O)) - (PaCO2 / RQ)
  - Normal A-aDO2 = (Age / 4) + 4
- **SpO2/FiO2 ratio** (surrogate for P/F)
- **Estimated PaO2 from SpO2** (Severinghaus-like piecewise approximation)

Author: Dr. Abu Suraih Sakhri. License: MIT.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`pf_ratio(pao2, fio2)`**: Calculate PaO2/FiO2 ratio.
- **`spo2_fio2_ratio(spo2, fio2)`**: Calculate SpO2/FiO2 ratio (surrogate for P/F ratio).
- **`estimate_pao2_from_spo2(spo2)`**: Estimate PaO2 from SpO2 using piecewise linear approximation of the oxyhemoglobin dissociation curve.
- **`estimate_pf_from_spo2_fio2(spo2, fio2)`**: Estimate P/F ratio from SpO2 and FiO2.
- **`oxygenation_index(fio2, map_pressure, pao2)`**: Calculate Oxygenation Index (OI).
- **`a_a_gradient(fio2, pao2, paco2, patm, ph2o, rq)`**: Calculate A-a (alveolar-arterial) oxygen gradient.
- **`normal_a_a_gradient(age, fio2)`**: Calculate expected normal A-a gradient for age.
- **`berlin_ards_classification(pao2, fio2, peep)`**: Classify ARDS severity per Berlin Definition.
- **`comprehensive_respiratory_assessment(...)`**: Full respiratory assessment combining all calculators.

---

## 💻 CLI Quickstart & Usage

### Installation
```bash
pip install -e ".[dev]"
```

### Single Patient Assessment
```bash
python cli.py single --pao2 80 --fio2 0.5 --paco2 40 --peep 10 --age 65 --spo2 95
```

### P/F Ratio Only
```bash
python cli.py pf --pao2 100 --fio2 0.21
```

### Berlin ARDS Classification
```bash
python cli.py berlin --pao2 60 --fio2 0.4 --peep 10
```

### Batch CSV Processing
```bash
python cli.py batch -i input.csv -o results.csv
```

### Enterprise Audit
```bash
python cli.py audit --task-id TASK-001 --primary 12.0 --secondary 4.0
```

### Supervisory Chat
```bash
python cli.py chat "Explain the Berlin criteria"
```

### Verify Audit Trail
```bash
python cli.py verify-audit
```

### Input Data Schema (CSV)

| Field | Description | Requirement |
|:------|:------------|:------------|
| `pao2` | Arterial O2 partial pressure (mmHg) | Required |
| `fio2` | Fraction of inspired oxygen (0.0-1.0) | Required |
| `paco2` | Arterial CO2 partial pressure (mmHg) | Required |
| `peep` | Positive end-expiratory pressure (cmH2O) | Optional |
| `map` | Mean airway pressure (cmH2O) | Optional |
| `age` | Patient age (years) | Optional |
| `spo2` | Oxygen saturation (%) | Optional |
| `patm` | Atmospheric pressure (mmHg) | Optional |
| `patient_id` | Patient identifier | Optional |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Regex-based inspection blocking SSNs, MRNs, phone numbers, emails, DOBs, and patient names from outbound data.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **LLM Reasoning Adapter:** Agnostic integration for local Ollama instances, Claude, OpenAI, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI REST API:** OpenAPI 3.1 REST endpoints with Prometheus-compatible metrics.

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Run with coverage:

```bash
pytest -v --tb=short
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

### Docker Build & Run
```bash
docker build -t pao2-fio2-berlin-ards-classifier .
docker run -e AUDIT_SECRET_KEY=your-secure-key pao2-fio2-berlin-ards-classifier
```

### Docker Compose
```bash
AUDIT_SECRET_KEY=your-secure-key docker-compose up
```

---

## 🔒 Security Configuration

Set the `AUDIT_SECRET_KEY` environment variable in production to ensure cryptographic audit trail integrity:

```bash
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

---

## 📁 Project Structure

```
pao2-fio2-berlin-ards-classifier/
├── pf_ratio_ards.py          # Core calculation module & CLI
├── cli.py                    # CLI entry point
├── enrichment.py             # Enrichment feature engines
├── simulator.py              # High-throughput simulation
├── agents/                   # Enterprise agent framework
│   ├── base.py               # PHI guard, audit trail, security
│   ├── models.py             # Pydantic data models
│   ├── supervisor.py         # Multi-agent orchestrator
│   ├── workers.py            # Specialized domain workers
│   ├── llm_factory.py        # LLM provider factory
│   ├── api.py                # FastAPI REST endpoints
│   ├── metrics.py            # Prometheus metrics
│   ├── streamer.py           # WebSocket telemetry
│   └── learning.py           # Bayesian calibration engine
├── tests/                    # Pytest test suite
├── web/                      # Operations console (HTML)
├── Dockerfile                # Container definition
├── docker-compose.yml        # Multi-service orchestration
└── pyproject.toml            # Python package configuration
```
