"""Auth routes: login, logout, refresh, me, change-password."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from datetime import datetime, timezone

from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, decode_refresh,
    get_current_user, check_lockout, record_failed_login, clear_failed_logins,
)
from db import coll
from models import LoginIn, ChangePasswordIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name_ar": user.get("name_ar"),
        "role": user["role"],
        "person_id": user.get("person_id"),
        "must_change_password": user.get("must_change_password", False),
    }


@router.post("/login")
async def login(payload: LoginIn, request: Request, response: Response):
    email = payload.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    # Use email as identifier for brute-force so multi-pod / proxied deployments
    # still enforce the 5-attempt lockout consistently.
    identifier = email
    await check_lockout(identifier)

    user = await coll("users").find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        await record_failed_login(identifier)
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")

    await clear_failed_logins(identifier)
    access = create_access_token(user["id"], user["email"], user["role"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    await coll("audit_log").insert_one({
        "user_email": email,
        "user_id": user["id"],
        "action": "login",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
    })
    return {"user": _user_out(user), "access_token": access}


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    await coll("audit_log").insert_one({
        "user_email": user["email"],
        "user_id": user["id"],
        "action": "logout",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return _user_out(user)


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_refresh(token)
    user = await coll("users").find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access = create_access_token(user["id"], user["email"], user["role"])
    new_refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, new_refresh)
    return {"ok": True}


@router.post("/change-password")
async def change_password(payload: ChangePasswordIn, user: dict = Depends(get_current_user)):
    db_user = await coll("users").find_one({"id": user["id"]})
    if not verify_password(payload.current_password, db_user["password_hash"]):
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
    await coll("users").update_one(
        {"id": user["id"]},
        {"$set": {
            "password_hash": hash_password(payload.new_password),
            "must_change_password": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    await coll("audit_log").insert_one({
        "user_email": user["email"],
        "user_id": user["id"],
        "action": "change_password",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}
