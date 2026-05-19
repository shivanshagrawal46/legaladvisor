"""
JWT authentication for the Legal Advisor web app.

Single hardcoded user (no DB needed for authentication):
  email:    rakeshsir@mtreh.com
  password: MangoTree@12345
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ── secrets ──────────────────────────────────────────────────────────────────
SECRET_KEY = "mango-tree-legal-advisor-jwt-secret-2026-xK9pL2mN"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8   # 8-hour session

# ── single authorised user ────────────────────────────────────────────────────
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

_USERS = {
    "rakeshsir@mtreh.com": {
        "email": "rakeshsir@mtreh.com",
        "name": "Rakesh Sir",
        "hashed_password": _pwd_ctx.hash("MangoTree@12345"),
    }
}

# ── schemas ───────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str
    name: str
    email: str


class TokenData(BaseModel):
    email: Optional[str] = None


class User(BaseModel):
    email: str
    name: str


# ── helpers ───────────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = _USERS.get(email)
    if not user:
        return None
    if not _verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credentials_exc
    except JWTError:
        raise credentials_exc
    user = _USERS.get(email)
    if not user:
        raise credentials_exc
    return User(email=user["email"], name=user["name"])
