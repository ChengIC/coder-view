import os
import uuid
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .utils.archive import process_folder_upload
from .evaluator.metrics import evaluate_codebase_from_contents
from .evaluator.openai_client import summarize_with_llm, test_llm_connection
from .supabase_client import insert_report, test_supabase_connection, get_recent_reports
from .logger import logger

APP_DIR = Path(__file__).resolve().parent

# Load environment variables from server/.env if present
load_dotenv(APP_DIR / ".env")

app = FastAPI(title="Codebase Evaluator API")

# Allow local dev frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Codebase Evaluator API starting up")


@app.get("/health")
def health() -> Dict[str, str]:
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {"status": "ok"}


@app.get("/status")
def status() -> Dict[str, Any]:
    """Detailed status check including LLM and Supabase connectivity."""
    logger.info("Status check requested")
    
    llm_status = test_llm_connection()
    supabase_status = test_supabase_connection()
    
    return {
        "api": {"status": "ok"},
        "llm": llm_status,
        "supabase": supabase_status,
        "environment": {
            "app_dir": str(APP_DIR),
            "logs_dir": str(APP_DIR / "logs")
        }
    }


@app.get("/reports")
def recent_reports(limit: int = 10) -> Dict[str, Any]:
    """Get recent evaluation reports from Supabase."""
    logger.info(f"Recent reports requested (limit: {limit})")
    return get_recent_reports(limit)


@app.post("/evaluate")
async def evaluate(
    files: List[UploadFile] = File(...),
    project_name: Optional[str] = Form(default=None),
):
    """Evaluate uploaded codebase files and return metrics report."""
    run_id = str(uuid.uuid4())
    logger.info(f"Starting evaluation {run_id} with {len(files)} files")
    
    if not files:
        logger.warning("No files received in evaluation request")
        raise HTTPException(status_code=400, detail="No files received. Please upload a folder with files.")

    try:
        # Process files directly in memory
        logger.info(f"Processing {len(files)} files in memory")
        file_contents = await process_folder_upload(files)
        
        if not file_contents:
            logger.warning("No valid files found in upload")
            raise HTTPException(status_code=400, detail="No valid text files found in upload.")

        # Infer project name from first file relative root if not provided
        inferred_name = None
        try:
            first_file = next(iter(file_contents.keys()))
            parts = Path(first_file).parts
            inferred_name = parts[0] if parts else None
            logger.debug(f"Inferred project name: {inferred_name}")
        except Exception as e:
            logger.warning(f"Could not infer project name: {e}")
            inferred_name = None

        final_project_name = project_name or inferred_name or "uploaded-folder"
        logger.info(f"Evaluating project: {final_project_name}")

        # Evaluate metrics directly from file contents
        logger.info("Starting codebase metrics evaluation")
        metrics = evaluate_codebase_from_contents(file_contents)
        logger.info(f"Metrics evaluation completed - found {metrics.get('file_count', 0)} files")

        # Extract code samples for LLM analysis
        code_samples = metrics.pop('code_samples', {})
        
        # Summarize with LLM (optional if env configured)
        logger.info("Requesting LLM summary with code samples")
        summary = summarize_with_llm(metrics, code_samples)
        if summary:
            logger.info("LLM summary generated successfully")
        else:
            logger.info("LLM summary skipped (not configured)")

        report: Dict[str, Any] = {
            "run_id": run_id,
            "project_name": final_project_name,
            "metrics": metrics,
            "summary": summary,
        }

        # Store in Supabase (if env configured)
        logger.info("Storing report in Supabase")
        supabase_result = insert_report(report)
        logger.info(f"Supabase storage result: {supabase_result.get('status', 'unknown')}")

        logger.info(f"Evaluation {run_id} completed successfully")
        
        return JSONResponse(content={
            "report": report,
            "supabase": supabase_result,
        })
        
    except Exception as e:
        logger.error(f"Evaluation {run_id} failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Log startup information and test connections."""
    logger.info("=== Codebase Evaluator API Started ===")
    logger.info(f"App directory: {APP_DIR}")
    
    # Test connections on startup
    llm_status = test_llm_connection()
    logger.info(f"LLM connection status: {llm_status.get('status', 'unknown')}")
    
    supabase_status = test_supabase_connection()
    logger.info(f"Supabase connection status: {supabase_status.get('status', 'unknown')}")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information."""
    logger.info("=== Codebase Evaluator API Shutting Down ===")