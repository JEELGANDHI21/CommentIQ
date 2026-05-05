"""
auth.py — JWT authentication using SQLite via database.py
==========================================================
Password hashing: sha256_crypt (passlib built-in, no bcrypt conflicts)
Token: signed JWT via python-jose
Rate limiting: stored in users table (persists across restarts)
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

import database as db

log = logging.getLogger(__name__)

SECRET_KEY           = os.getenv("SECRET_KEY", "change-me-use-openssl-rand-hex-32")
ALGORITHM            = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

pwd_ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
oauth2  = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


async def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = await db.get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2)) -> dict:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc

    user = await db.get_user(username)
    if not user:
        raise exc
    return user


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    username:     str
    usage:        dict