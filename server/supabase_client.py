import os
from typing import Any, Dict, Optional

try:
    from supabase import create_client, Client
except Exception:  # pragma: no cover
    create_client = None
    Client = None


_client: Optional[Client] = None


def _get_client() -> Optional[Client]:
    global _client
    if _client:
        return _client
    if not create_client:
        return None
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    _client = create_client(url, key)
    return _client


def insert_report(report: Dict[str, Any]) -> Dict[str, Any]:
    client = _get_client()
    if not client:
        return {"status": "skipped", "reason": "Supabase env not configured"}
    try:
        data = client.table("reports").insert(report).execute()
        return {"status": "ok", "data": getattr(data, "data", data)}
    except Exception as e:
        return {"status": "error", "error": str(e)}