"""
FastAPI REST API Server for Pao2 Fio2 Berlin Ards Classifier.
"""
from typing import Dict, Any, List
import os
import secrets
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor
from pf_ratio_ards import comprehensive_respiratory_assessment, berlin_ards_classification

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Pao2 Fio2 Berlin Ards Classifier API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "pao2-fio2-berlin-ards-classifier", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs(x_admin_key: str | None = Header(default=None)):
    key = os.getenv("AUDIT_ADMIN_KEY")
    if not key or not x_admin_key or not secrets.compare_digest(x_admin_key, key):
        raise HTTPException(status_code=403, detail="Audit logs require configured admin access")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}

class AssessmentInput(BaseModel):
    pao2: float
    fio2: float
    paco2: float | None = None
    peep: float | None = None
    map_pressure: float | None = None
    age: float | None = None
    spo2: float | None = None
    patm: float = 760.0


@app.post("/api/assessment")
def api_assessment(payload: AssessmentInput):
    """Calculate oxygenation metrics; never assert an ARDS diagnosis."""
    try:
        values = payload.model_dump()
        if values.pop("paco2") is None:
            return berlin_ards_classification(
                values["pao2"], values["fio2"], values["peep"]
            )
        return comprehensive_respiratory_assessment(
            payload.pao2, payload.fio2, payload.paco2,
            peep=payload.peep, map_pressure=payload.map_pressure,
            age=payload.age, spo2=payload.spo2, patm=payload.patm
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# A local API deployment also serves the same dependency-free browser UI.
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "web", html=True), name="web")
