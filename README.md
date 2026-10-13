# PaO₂/FiO₂ Ratio & Berlin ARDS Classifier

Clinical-education utilities for oxygenation assessment using the **Berlin (2012)** PaO₂/FiO₂ severity ranges. Includes a dependency-free browser calculator, a Python library/CLI, CSV batch processing, and an optional FastAPI service.

**Important:** An oxygenation ratio is **not an ARDS diagnosis**. The Berlin definition also requires acute timing, bilateral opacities, noncardiogenic origin of edema, and relevant positive airway pressure (PEEP ≥5 cmH₂O; CPAP is permitted for mild ARDS). The [2024 Global Definition](https://doi.org/10.1164/rccm.202303-0558WS) adds other pathways and is **not** implemented here.

## Browser calculator

The `web/` directory contains a responsive static HTML/JavaScript app with no framework, build step, external scripts, or Python runtime. It supports:

- P/F oxygenation category: severe (≤100), moderate (>100–200), mild (>200–300), outside range (>300).
- Validation for missing PEEP and out-of-range/non-finite measurements.
- Optional A–a gradient, oxygenation index, age-based room-air A–a heuristic and SpO₂/FiO₂ ratio.
- JSON result export and local CSV batch import/export (5 MB / 10,000 rows maximum).
- Explicit interpretation warnings; **no diagnostic confirmation**.

To serve the static app locally:

```bash
python -m http.server 8080 --directory web
# Open http://localhost:8080/
```

The browser calculations are implemented directly in JavaScript; **Pyodide/PyScript is not required**. Browser compatibility: modern browsers with ES modules, File API, and Blob download support. On the static site, calculations and files remain in the browser; no application requests are made to a server.

## Python CLI and library

Requires Python 3.10 or later.

```bash
python -m pip install -e ".[dev]"
pf-ratio-ards pf --pao2 100 --fio2 0.21
pf-ratio-ards berlin --pao2 60 --fio2 0.4 --peep 10
pf-ratio-ards single --pao2 80 --fio2 0.5 --paco2 40 --peep 10 --age 65 --spo2 95
pf-ratio-ards batch --input sample.csv --output results.csv
```

Required batch columns: `pao2`, `fio2`, `paco2`. Optional: `peep`, `map`, `age`, `spo2`, `patm`, `patient_id`. FiO₂ uses a fraction (e.g. 0.5), PaO₂/PaCO₂ use mmHg. Invalid data stop the batch operation with a row number. No files are overwritten until all rows validate.

The library exposes `pf_ratio`, `berlin_ards_classification`, `comprehensive_respiratory_assessment`, `oxygenation_index`, `a_a_gradient`, and supporting functions in `pf_ratio_ards.py`. SpO₂-to-PaO₂ estimation is an **unvalidated piecewise approximation for educational use only**; it is not suitable for oxygenation-based clinical decisions. Age-adjusted expected A–a values are room-air heuristics.

## Optional API / Docker

```bash
python -m pip install -e ".[web]"
uvicorn agents.api:app --host 127.0.0.1 --port 8000
# API documentation: http://127.0.0.1:8000/docs
```

`POST /api/assessment` calculates oxygenation measures with input validation. The API serves the browser app at `/`. The existing demonstration audit endpoints (`/api/audit`, `/api/chat`, `/metrics`) remain, but the generic worker thresholds and mock chat are **not clinical rules or medical guidance**. `/api/audit/logs` requires `AUDIT_ADMIN_KEY` and the matching `X-Admin-Key` header.

To start the containerized service:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
```

Compose binds `127.0.0.1:8000` by default. To enable protected audit-log access, separately configure `AUDIT_ADMIN_KEY`. HMAC audit records are in-memory and do not survive a restart; the signing key must be kept secret.

## Privacy and security limitations

- The static browser app does not use telemetry, cookies, local storage, or external application services. CSV/JSON exports stay on the user's machine; avoid entering identifiable patient information.
- Optional Python CLI/API processes data in its local/container process. Batch exports can include `patient_id`; users are responsible for access controls and retention.
- Audit and supervisor features use **regex-based pattern screening**, not comprehensive PHI de-identification or HIPAA certification. Never assume arbitrary patient text is safe because a regex check passes.
- The audit ledger supports HMAC-chain integrity checks, but is not a durable, independently timestamped audit system.
- No external LLM provider is configured; supervisory chat uses a demonstration mock.

## Tests and CI

```bash
python -m pip install -e ".[web,dev]"
python -m pytest -q
node --check web/app.mjs
node --test web/calculator.test.mjs
```

GitHub Actions tests Python 3.10–3.12 and the browser calculation module. A separate workflow publishes `web/` to GitHub Pages when Pages is enabled in repository settings.

## References and license

- ARDS Definition Task Force. *Acute respiratory distress syndrome: the Berlin Definition*. JAMA. 2012;307:2526–2533. [doi:10.1001/jama.2012.5669](https://doi.org/10.1001/jama.2012.5669).
- Matthay MA, et al. *A New Global Definition of Acute Respiratory Distress Syndrome*. AJRCCM. 2024. [doi:10.1164/rccm.202303-0558WS](https://doi.org/10.1164/rccm.202303-0558WS).

License: [MIT](LICENSE). Maintainer: Dr. Abu Suraih Sakhri.
