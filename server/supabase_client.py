import os
from typing import Any, Dict, Optional

from logger import logger

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    create_client = None
    Client = None
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase library not available - install with: pip install supabase")


_client: Optional[Client] = None


def test_supabase_connection() -> Dict[str, Any]:
    """Test Supabase connection and return status."""
    if not SUPABASE_AVAILABLE:
        return {
            "status": "error",
            "message": "Supabase library not installed"
        }
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        return {
            "status": "error",
            "message": "SUPABASE_URL or SUPABASE_*_KEY not configured"
        }
    
    try:
        logger.info(f"Testing Supabase connection to {url}")
        client = create_client(url, key)
        
        # Test with a simple query to a system table
        table_name = os.getenv("SUPABASE_TABLE", "reports")
        
        # Try to get table info (this will fail gracefully if table doesn't exist)
        try:
            result = client.table(table_name).select("*").limit(1).execute()
            logger.info(f"Supabase connection successful - table '{table_name}' accessible")
            return {
                "status": "ok",
                "url": url,
                "table": table_name,
                "key_type": "service_role" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "anon"
            }
        except Exception as table_error:
            logger.warning(f"Supabase connected but table '{table_name}' may not exist: {table_error}")
            return {
                "status": "warning",
                "message": f"Connected but table '{table_name}' not accessible",
                "url": url,
                "table": table_name
            }
            
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        return {
            "status": "error",
            "message": f"Connection failed: {e}"
        }


def _get_client() -> Optional[Client]:
    """Get or create Supabase client."""
    global _client
    
    if _client:
        return _client
        
    if not SUPABASE_AVAILABLE:
        logger.warning("Supabase library not available")
        return None
        
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        logger.warning("Supabase credentials not configured")
        return None
        
    try:
        _client = create_client(url, key)
        logger.info("Supabase client created successfully")
        return _client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


def insert_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Insert evaluation report into Supabase."""
    client = _get_client()
    
    if not client:
        logger.info("Supabase not configured - skipping report storage")
        return {"status": "skipped", "reason": "Supabase not configured"}
    
    table_name = os.getenv("SUPABASE_TABLE", "reports")
    
    try:
        logger.info(f"Inserting report {report.get('run_id', 'unknown')} into table '{table_name}'")
        
        # Extract LLM metadata from summary
        summary = report.get('summary', {})
        llm_metadata = summary.pop('_llm_metadata', {}) if isinstance(summary, dict) else {}
        
        # Log what we're storing (without sensitive data)
        metrics = report.get('metrics', {})
        logger.info(f"Report details: project={report.get('project_name', 'unknown')}, "
                   f"files={metrics.get('file_count', 0)}, "
                   f"has_llm_summary={bool(summary and summary != {})}, "
                   f"llm_used={'yes' if llm_metadata.get('success') else 'no'}")
        
        if summary and 'error' in summary:
            logger.warning(f"LLM summary contains error: {summary.get('error', 'unknown')}")
        elif llm_metadata.get('success'):
            logger.info(f"LLM summary successful - tokens: {llm_metadata.get('tokens_used', 0)}")
        
        # Prepare report data with LLM tracking fields
        report_data = report.copy()
        
        # Add timestamp if not present
        if "created_at" not in report_data:
            from datetime import datetime
            report_data["created_at"] = datetime.utcnow().isoformat()
        
        # Add LLM tracking fields from metadata
        if llm_metadata:
            if llm_metadata.get('request_time'):
                report_data["llm_request_time"] = llm_metadata['request_time']
            if llm_metadata.get('response_time'):
                report_data["llm_response_time"] = llm_metadata['response_time']
            if llm_metadata.get('tokens_used'):
                report_data["llm_tokens_used"] = llm_metadata['tokens_used']
            if llm_metadata.get('model'):
                report_data["llm_model_used"] = llm_metadata['model']
        
        result = client.table(table_name).insert(report_data).execute()
        
        if hasattr(result, 'data') and result.data:
            inserted_id = result.data[0].get('id', 'unknown')
            logger.info(f"Report inserted successfully with ID: {inserted_id}")
            
            # Insert detailed LLM log if we have metadata
            if llm_metadata and inserted_id != 'unknown':
                try:
                    # Extract error details if available
                    error_message = None
                    error_details = None
                    
                    if 'error' in summary:
                        error_message = summary.get('error')
                    
                    if llm_metadata.get('error_details'):
                        error_details = llm_metadata['error_details']
                        # If error_details is a dict, store as JSON, otherwise as string
                        if isinstance(error_details, dict):
                            error_message = error_details.get('error_message', error_message)
                    
                    llm_log_data = {
                         "report_id": inserted_id,
                         "run_id": report.get('run_id'),
                         "user_id": report.get('user_id'),  # Include user_id for LLM logs
                        "request_timestamp": llm_metadata.get('request_time'),
                        "response_timestamp": llm_metadata.get('response_time'),
                        "model_used": llm_metadata.get('model'),
                        "tokens_used": llm_metadata.get('tokens_used', 0),
                        "request_size": len(str(metrics)) + len(str(report.get('code_samples', {}))),
                        "response_size": len(str(summary)),
                        "success": llm_metadata.get('success', False),
                        "error_message": error_message,
                        "response_data": {
                            "summary": summary if llm_metadata.get('success') else None,
                            "error_details": error_details if error_details else None,
                            "metadata": llm_metadata
                        }
                    }
                    
                    llm_result = client.table("llm_logs").insert(llm_log_data).execute()
                    logger.info(f"LLM log inserted for report {inserted_id}")
                    
                    if error_details:
                        logger.info(f"Stored detailed OpenAI error: {error_message}")
                        
                except Exception as e:
                    logger.warning(f"Failed to insert LLM log: {e}")
            
            logger.info(f"Supabase storage: SUCCESS - Report {report.get('run_id')} stored in table '{table_name}'")
            return {
                "status": "ok",
                "data": result.data,
                "table": table_name,
                "inserted_id": inserted_id
            }
        else:
            logger.warning("Report insert returned no data")
            return {
                "status": "warning",
                "message": "Insert completed but no data returned",
                "table": table_name
            }
            
    except Exception as e:
        logger.error(f"Failed to insert report into Supabase: {e}")
        logger.error(f"Supabase storage: FAILED - Report {report.get('run_id')} could not be stored")
        return {
            "status": "error",
            "error": str(e),
            "table": table_name
        }


def get_user_reports(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """Get reports for a specific user."""
    client = _get_client()
    
    if not client:
        return {"status": "skipped", "reason": "Supabase not configured"}
    
    table_name = os.getenv("SUPABASE_TABLE", "reports")
    
    try:
        logger.info(f"Fetching {limit} reports for user {user_id}")
        
        result = client.table(table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        if hasattr(result, 'data'):
            logger.info(f"Retrieved {len(result.data)} reports for user")
            return {
                "status": "ok",
                "data": result.data,
                "count": len(result.data),
                "user_id": user_id
            }
        else:
            return {"status": "error", "message": "No data returned"}
            
    except Exception as e:
        logger.error(f"Failed to fetch user reports from Supabase: {e}")
        return {"status": "error", "error": str(e)}