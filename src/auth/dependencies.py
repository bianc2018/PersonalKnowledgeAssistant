from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from src.config import get_settings
from src.auth.crypto import cache_master_key, get_cached_master_key, get_no_auth_master_key
from src.db.connection import get_db

security = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, token: str):
        self.token = token


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]
) -> CurrentUser:
    settings = get_settings()
    db = await get_db()
    try:
        async with db.execute(
            "SELECT password_enabled FROM system_config WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()

        password_enabled = bool(row[0]) if row else True

        if not password_enabled:
            cache_master_key("no-auth", get_no_auth_master_key())
            return CurrentUser(token="no-auth")

        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = credentials.credentials
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            exp = payload.get("exp")
            if exp is None or datetime.now(timezone.utc).timestamp() > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        master_key = get_cached_master_key(token)
        if master_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalidated, please login again",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(token=token)
    finally:
        await db.close()
