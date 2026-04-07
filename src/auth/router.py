from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel

from src.config import get_settings
from src.auth.crypto import (
    cache_master_key,
    derive_master_key,
    generate_salt,
    hash_password,
    verify_password,
)
from src.db.connection import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str
    remember_me: bool = False


class LoginData(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    data: LoginData


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    settings = get_settings()
    db = await get_db()
    try:
        async with db.execute(
            "SELECT password_hash, salt FROM system_config WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()

        if row is None or row[0] is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System not initialized",
            )

        password_hash, salt = row
        if not verify_password(body.password, password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
            )

        master_key = derive_master_key(body.password, salt)
        expires_delta = timedelta(days=settings.remember_me_days if body.remember_me else 1)
        expires_at = datetime.now(timezone.utc) + expires_delta
        token = jwt.encode(
            {"exp": expires_at},
            settings.secret_key,
            algorithm="HS256",
        )
        cache_master_key(token, master_key)

        return LoginResponse(
            data=LoginData(
                token=token,
                expires_in=int(expires_delta.total_seconds()),
            )
        )
    finally:
        await db.close()
