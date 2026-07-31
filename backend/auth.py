"""JWT auth, bcrypt, RBAC guards, session versioning."""
import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Depends
from typing import Callable

from db import coll

JWT_ALG = "HS256"
ACCESS_MINUTES = 60
REFRESH_DAYS = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, role: str, pv: int) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role, "pv": pv, "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_MINUTES),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALG)


def create_refresh_token(user_id: str, pv: int) -> str:
    payload = {
        "sub": user_id, "pv": pv, "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALG)


def _decode(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(request: Request) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = _decode(token, "access")
    user = await coll("users").find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # Session revocation: bump pw_version on password change/reset invalidates
    # every previously-issued token.
    if int(user.get("pw_version", 0)) != int(payload.get("pv", 0)):
        raise HTTPException(status_code=401, detail="Session revoked")
    user.pop("_id", None)
    user.pop("password_hash", None)
    return user


def require_role(*roles: str) -> Callable:
    async def _guard(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Forbidden: insufficient role")
        # Force password change before any operational endpoint is reachable.
        if user.get("must_change_password"):
            raise HTTPException(status_code=428, detail="PASSWORD_CHANGE_REQUIRED")
        return user
    return _guard


def set_auth_cookies(response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token", value=access_token,
        httponly=True, secure=True, samesite="none",
        max_age=ACCESS_MINUTES * 60, path="/",
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token,
        httponly=True, secure=True, samesite="none",
        max_age=REFRESH_DAYS * 86400, path="/",
    )


def clear_auth_cookies(response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def decode_refresh(token: str) -> dict:
    return _decode(token, "refresh")


# --- Brute-force / rate-limit -------------------------------------------
MAX_FAILED = 5
LOCKOUT_MINUTES = 15


async def check_lockout(identifier: str):
    rec = await coll("login_attempts").find_one({"identifier": identifier})
    if not rec:
        return
    if rec.get("count", 0) >= MAX_FAILED:
        last = rec.get("last_at")
        if last and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last and datetime.now(timezone.utc) - last < timedelta(minutes=LOCKOUT_MINUTES):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
        await coll("login_attempts").delete_one({"identifier": identifier})


async def record_failed_login(identifier: str):
    await coll("login_attempts").update_one(
        {"identifier": identifier},
        {"$inc": {"count": 1}, "$set": {"last_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def clear_failed_logins(identifier: str):
    await coll("login_attempts").delete_one({"identifier": identifier})


# --- Password reset rate-limit ------------------------------------------
async def check_reset_rate(email: str, *, per_hour: int = 3):
    key = f"reset::{email}"
    rec = await coll("login_attempts").find_one({"identifier": key})
    if not rec:
        return
    last = rec.get("last_at")
    if last and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if last and datetime.now(timezone.utc) - last < timedelta(hours=1) and rec.get("count", 0) >= per_hour:
        raise HTTPException(status_code=429, detail="Too many reset requests. Try again later.")


async def record_reset_attempt(email: str):
    key = f"reset::{email}"
    await coll("login_attempts").update_one(
        {"identifier": key},
        {"$inc": {"count": 1}, "$set": {"last_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
