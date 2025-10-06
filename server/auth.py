import os
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .logger import logger

security = HTTPBearer(auto_error=False)

class AuthUser:
    def __init__(self, user_id: str, email: str, metadata: Dict[str, Any] = None):
        self.user_id = user_id
        self.email = email
        self.metadata = metadata or {}

def verify_supabase_token(token: str) -> Optional[AuthUser]:
    """Verify Supabase JWT token and return user info."""
    try:
        # Get Supabase JWT secret from environment
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            logger.warning("SUPABASE_JWT_SECRET not configured")
            return None
        
        # Decode JWT token
        payload = jwt.decode(
            token, 
            jwt_secret, 
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            logger.warning("Invalid token: missing user ID")
            return None
        
        logger.debug(f"Authenticated user: {email} ({user_id})")
        return AuthUser(
            user_id=user_id,
            email=email,
            metadata=payload
        )
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[AuthUser]:
    """FastAPI dependency to get current authenticated user."""
    if not credentials:
        return None
    
    return verify_supabase_token(credentials.credentials)

def require_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> AuthUser:
    """FastAPI dependency that requires authentication."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = verify_supabase_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[AuthUser]:
    """FastAPI dependency for optional authentication."""
    if not credentials:
        return None
    
    return verify_supabase_token(credentials.credentials)