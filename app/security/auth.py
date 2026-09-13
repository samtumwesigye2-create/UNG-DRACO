import os

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from app.security.rbac import Principal


def verify_janus_token(token: str) -> Principal:
    issuer = os.getenv("JANUS_ISSUER")
    audience = os.getenv("JANUS_AUDIENCE")
    jwks_url = os.getenv("JANUS_JWKS_URL")
    if not issuer or not audience or not jwks_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="JANUS authentication is not configured")

    try:
        signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid JANUS token") from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JANUS token missing subject")

    raw_roles = payload.get("roles", [])
    roles = {raw_roles} if isinstance(raw_roles, str) else set(raw_roles)
    return Principal(subject=subject, roles=roles)


def get_current_principal(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    return verify_janus_token(authorization[7:].strip())
