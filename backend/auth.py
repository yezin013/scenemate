"""Supabase JWT 검증 — Bearer 토큰에서 user_id(UUID) 추출 (ES256 + JWKS)."""
import os
import logging
import jwt
from jwt import PyJWKClient
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv(Path(__file__).parent / ".env")
_supabase_url = os.environ["SUPABASE_URL"].strip().rstrip("/")
_JWKS_URL = f"{_supabase_url}/auth/v1/.well-known/jwks.json"

logger = logging.getLogger(__name__)
_bearer = HTTPBearer()
_jwks_client = PyJWKClient(_JWKS_URL, cache_keys=True)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Authorization: Bearer <token> → ES256 검증 후 user UUID 반환."""
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(creds.credentials)
        payload = jwt.decode(
            creds.credentials,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
        return payload["sub"]
    except Exception as e:
        logger.error("JWT auth failed [%s] %s", type(e).__name__, e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
