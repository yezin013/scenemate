"""Supabase JWT 검증 — Bearer 토큰에서 user_id(UUID) 추출."""
import os
import logging
import jwt
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv(Path(__file__).parent / ".env")
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"].strip()

logger = logging.getLogger(__name__)
_bearer = HTTPBearer()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Authorization: Bearer <token> 검증 후 user UUID 반환."""
    try:
        payload = jwt.decode(
            creds.credentials,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload["sub"]
    except Exception as e:
        logger.error("JWT decode failed [%s] %s", type(e).__name__, e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
