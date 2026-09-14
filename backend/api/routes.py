from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core.orchestrator import Orchestrator

logger = logging.getLogger("devops_api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

router = APIRouter()
orchestrator = Orchestrator()


@router.get("/health")
def health() -> dict[str, str]:
    logger.info("GET /health called")
    return {"status": "ok"}


@router.get("/samples")
def list_samples() -> dict[str, Any]:
    logger.info("GET /samples called")
    return {"samples": orchestrator.list_sample_logs()}


@router.post("/analyze")
async def analyze_logs(
    file: UploadFile | None = File(default=None),
    sample_name: str | None = Form(default=None),
) -> dict[str, Any]:
    logger.info("POST /analyze called with file=%s sample_name=%s", bool(file), sample_name)

    if file is not None:
        upload_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = Path(file.filename or "uploaded.log").name
        saved_path = upload_dir / safe_filename

        with saved_path.open("wb") as handle:
            content = await file.read()
            handle.write(content)

        logger.info("Agent: uploaded log file saved to %s", saved_path)
        return orchestrator.analyze_log_file(saved_path)

    if sample_name:
        logger.info("Agent: analyzing sample log %s", sample_name)
        return orchestrator.analyze_sample(sample_name)

    raise HTTPException(status_code=400, detail="Provide either a log file upload or a sample_name.")
