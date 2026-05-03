import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


TOKEN_EXPIRE_HOURS = 12
ALGORITHM          = "HS256"
bearer_scheme      = HTTPBearer()


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    """FastAPI dependency — raises 401 if token is missing or invalid."""
    try:
        payload = jwt.decode(credentials.credentials, _secret(), algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def check_credentials(username: str, password: str) -> bool:
    return (
        username == os.environ["ADMIN_USERNAME"] and
        password == os.environ["ADMIN_PASSWORD"]
    )
