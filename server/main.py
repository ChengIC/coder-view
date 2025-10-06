import os
import uuid
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .utils.archive import save_folder_upload
from .evaluator.metrics import evaluate_codebase
from .evaluator.openai_client import summarize_with_llm
from .supabase_client import insert_report

APP_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = APP_DIR / "uploads"
WORK_DIR = APP_DIR / "workdir"
UPLOADS_DIR.mkdir(exist_ok=True)
WORK_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Codebase Evaluator API")

# Allow local dev frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/evaluate")
async def evaluate(
    files: List[UploadFile] = File(...),
    project_name: Optional[str] = Form(default=None),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files received. Please upload a folder with files.")

    run_id = str(uuid.uuid4())
    extract_path = WORK_DIR / run_id

    # Save all files, preserving relative paths
    await save_folder_upload(files, extract_path)

    # Infer project name from first file relative root if not provided
    inferred_name = None
    try:
        first = files[0].filename or ""
        parts = Path(first).parts
        inferred_name = parts[0] if parts else None
    except Exception:
        inferred_name = None

    # Evaluate metrics
    metrics = evaluate_codebase(extract_path)

    # Summarize with LLM (optional if env configured)
    summary = summarize_with_llm(metrics)

    report: Dict[str, Any] = {
        "run_id": run_id,
        "project_name": project_name or inferred_name or "uploaded-folder",
        "metrics": metrics,
        "summary": summary,
    }

    # Store in Supabase (if env configured)
    supabase_result = insert_report(report)

    return JSONResponse(content={
        "report": report,
        "supabase": supabase_result,
    })