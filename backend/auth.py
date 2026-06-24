"""Supabase JWT 검증 — Bearer 토큰에서 user_id(UUID) 추출 (RS256 + JWKS)."""
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
    """Authorization: Bearer <token> → RS256 검증 후 user UUID 반환."""
    token = creds.credentials
    try:
        # Step 1: JWT 헤더 파싱 (비검증) — alg/kid 확인
        header = jwt.get_unverified_header(token)
        logger.info("JWT header: alg=%s kid=%s", header.get("alg"), header.get("kid"))
    except Exception as e:
        logger.error("JWT header parse failed [%s] %s", type(e).__name__, e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    try:
        # Step 2: JWKS에서 서명 키 조회
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        logger.info("JWKS signing key: alg=%s", signing_key.algorithm_name)
    except Exception as e:
        logger.error("JWKS key lookup failed [%s] %s", type(e).__name__, e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    try:
        # Step 3: 서명 검증 및 페이로드 추출
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="authenticated",
        )
        return payload["sub"]
    except Exception as e:
        logger.error("JWT decode failed [%s] %s", type(e).__name__, e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
