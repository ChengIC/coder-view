import os
import json
from typing import Any, Dict, Optional

import requests
from ..logger import logger


def test_llm_connection() -> Dict[str, Any]:
    """Test LLM API connection and return status."""
    base_url = os.getenv("LLM_API_BASE")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    if not base_url or not api_key:
        return {
            "status": "error",
            "message": "LLM_API_BASE or LLM_API_KEY not configured"
        }
    
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    test_payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 5,
        "temperature": 0.1,
    }
    
    try:
        logger.info(f"Testing LLM connection to {base_url}")
        resp = requests.post(url, headers=headers, json=test_payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            logger.info("LLM connection test successful")
            return {"status": "ok", "model": model, "url": base_url}
        else:
            logger.warning("LLM returned unexpected response format")
            return {"status": "warning", "message": "Unexpected response format"}
            
    except requests.exceptions.Timeout:
        logger.error("LLM connection timeout")
        return {"status": "error", "message": "Connection timeout"}
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to LLM API at {base_url}")
        return {"status": "error", "message": "Connection failed"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"LLM API HTTP error: {e}")
        return {"status": "error", "message": f"HTTP error: {e}"}
    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return {"status": "error", "message": str(e)}


def summarize_with_llm(metrics: Dict[str, Any], code_samples: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
    """Generate LLM summary of codebase metrics and code samples."""
    from datetime import datetime
    
    base_url = os.getenv("LLM_API_BASE")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    if not base_url or not api_key:
        logger.warning("LLM not configured - skipping summary generation")
        return None

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Create comprehensive analysis prompt
    prompt = (
        "You are a senior code reviewer and software architect. Analyze the provided codebase metrics "
        "and code samples to generate a comprehensive evaluation report. Return a JSON object with these keys:\n"
        "- 'overview': Overall assessment of code quality\n"
        "- 'risks': Array of specific risks and issues found\n"
        "- 'recommendations': Array of actionable improvement suggestions\n"
        "- 'code_patterns': Analysis of coding patterns and practices\n"
        "- 'architecture_notes': Comments on code structure and organization\n"
        "- 'priority_fixes': Top 3 most critical issues to address first"
    )

    # Prepare content with metrics and code samples
    content_parts = [f"METRICS:\n{json.dumps(metrics, indent=2)}"]
    
    if code_samples:
        content_parts.append("\nCODE SAMPLES:")
        for file_path, code_content in code_samples.items():
            content_parts.append(f"\n--- {file_path} ---\n{code_content}")
    
    user_content = "\n".join(content_parts)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content},
    ]

    # Log what we're sending (with code sample info)
    logger.info(f"Sending to LLM: file_count={metrics.get('file_count', 0)}, "
                f"code_samples={len(code_samples) if code_samples else 0} files, "
                f"total_content_size={len(user_content)} characters")
    
    if code_samples:
        logger.info(f"Code sample files: {list(code_samples.keys())}")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2000,
    }
    
    # Add response_format for compatible APIs
    if "gpt" in model.lower() or "claude" in model.lower():
        payload["response_format"] = {"type": "json_object"}

    # Record timing and track API usage
    request_start = datetime.utcnow()
    
    try:
        logger.info(f"Requesting LLM summary using model {model}")
        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        
        response_end = datetime.utcnow()
        
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        
        # Extract token usage
        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)
        
        if not content:
            logger.warning("LLM returned empty content")
            return {
                "text": "No summary returned from LLM.",
                "_llm_metadata": {
                    "request_time": request_start.isoformat(),
                    "response_time": response_end.isoformat(),
                    "model": model,
                    "tokens_used": tokens_used,
                    "success": False
                }
            }
        
        logger.info(f"LLM summary generated successfully - tokens used: {tokens_used}")
        
        # Try to parse as JSON first
        try:
            parsed = json.loads(content)
            logger.debug("LLM returned valid JSON")
            
            # Add metadata for tracking
            parsed["_llm_metadata"] = {
                "request_time": request_start.isoformat(),
                "response_time": response_end.isoformat(),
                "model": model,
                "tokens_used": tokens_used,
                "success": True
            }
            return parsed
        except json.JSONDecodeError:
            logger.info("LLM returned text instead of JSON, wrapping in text field")
            return {
                "text": content,
                "_llm_metadata": {
                    "request_time": request_start.isoformat(),
                    "response_time": response_end.isoformat(),
                    "model": model,
                    "tokens_used": tokens_used,
                    "success": True
                }
            }
            
    except requests.exceptions.Timeout:
        logger.error("LLM request timeout")
        return {
            "error": "LLM request timeout",
            "_llm_metadata": {
                "request_time": request_start.isoformat(),
                "response_time": datetime.utcnow().isoformat(),
                "model": model,
                "tokens_used": 0,
                "success": False
            }
        }
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to LLM API at {base_url}")
        return {
            "error": "Cannot connect to LLM API",
            "_llm_metadata": {
                "request_time": request_start.isoformat(),
                "response_time": datetime.utcnow().isoformat(),
                "model": model,
                "tokens_used": 0,
                "success": False
            }
        }
    except requests.exceptions.HTTPError as e:
        logger.error(f"LLM API HTTP error: {e}")
        return {
            "error": f"LLM API error: {e}",
            "_llm_metadata": {
                "request_time": request_start.isoformat(),
                "response_time": datetime.utcnow().isoformat(),
                "model": model,
                "tokens_used": 0,
                "success": False
            }
        }
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return {
            "error": f"LLM request failed: {e}",
            "_llm_metadata": {
                "request_time": request_start.isoformat(),
                "response_time": datetime.utcnow().isoformat(),
                "model": model,
                "tokens_used": 0,
                "success": False
            }
        }