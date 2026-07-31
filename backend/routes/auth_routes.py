"""Auth routes: login, logout, refresh, me, change-password, forgot/reset."""
import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, Depends

from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, decode_refresh,
    get_current_user, check_lockout, record_failed_login, clear_failed_logins,
    check_reset_rate, record_reset_attempt,
)
from db import coll
from models import LoginIn, ChangePasswordIn, ForgotPasswordIn, ResetPasswordIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

MAIL_SINK = Path(__file__).resolve().parent.parent / "dev_mail_sink.log"


def _user_out(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name_ar": user.get("name_ar"),
        "role": user["role"],
        "person_id": user.get("person_id"),
        "must_change_password": user.get("must_change_password", False),
    }


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _log_mail(subject: str, to: str, body: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] to={to} subject={subject}\n{body}\n---\n"
    try:
        MAIL_SINK.parent.mkdir(parents=True, exist_ok=True)
        with MAIL_SINK.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    # Never expose reset token in HTTP response


@router.post("/login")
async def login(payload: LoginIn, request: Request, response: Response):
    email = payload.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = email
    await check_lockout(identifier)

    user = await coll("users").find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        await record_failed_login(identifier)
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")

    await clear_failed_logins(identifier)
    pv = int(user.get("pw_version", 0))
    access = create_access_token(user["id"], user["email"], user["role"], pv)
    refresh = create_refresh_token(user["id"], pv)
    set_auth_cookies(response, access, refresh)
    await coll("audit_log").insert_one({
        "user_email": email, "user_id": user["id"],
        "action": "login",
        "created_at": datetime.now(timezone.utc).isoformat(), "ip": ip,
    })
    return {"user": _user_out(user), "access_token": access}


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    await coll("audit_log").insert_one({
        "user_email": user["email"], "user_id": user["id"],
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
    if int(user.get("pw_version", 0)) != int(payload.get("pv", 0)):
        raise HTTPException(status_code=401, detail="Session revoked")
    pv = int(user.get("pw_version", 0))
    access = create_access_token(user["id"], user["email"], user["role"], pv)
    new_refresh = create_refresh_token(user["id"], pv)
    set_auth_cookies(response, access, new_refresh)
    return {"ok": True}


@router.post("/change-password")
async def change_password(payload: ChangePasswordIn, response: Response,
                          user: dict = Depends(get_current_user)):
    """Works even when must_change_password=True (this route bypasses require_role)."""
    db_user = await coll("users").find_one({"id": user["id"]})
    if not verify_password(payload.current_password, db_user["password_hash"]):
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
    if verify_password(payload.new_password, db_user["password_hash"]):
        raise HTTPException(status_code=400, detail="كلمة المرور الجديدة يجب أن تختلف عن الحالية")
    new_pv = int(db_user.get("pw_version", 0)) + 1
    now = datetime.now(timezone.utc).isoformat()
    await coll("users").update_one(
        {"id": user["id"]},
        {"$set": {
            "password_hash": hash_password(payload.new_password),
            "must_change_password": False,
            "pw_version": new_pv,
            "updated_at": now,
        }},
    )
    # Rotate cookies immediately so the caller stays authenticated
    access = create_access_token(user["id"], user["email"], user["role"], new_pv)
    refresh = create_refresh_token(user["id"], new_pv)
    set_auth_cookies(response, access, refresh)
    await coll("audit_log").insert_one({
        "user_email": user["email"], "user_id": user["id"],
        "action": "change_password",
        "created_at": now,
    })
    return {"ok": True, "access_token": access}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordIn):
    """Always returns ok — never reveals whether the email is registered."""
    email = payload.email
    await check_reset_rate(email)
    await record_reset_attempt(email)
    user = await coll("users").find_one({"email": email})
    if user:
        raw = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await coll("password_reset_tokens").insert_one({
            "token_hash": token_hash,
            "user_id": user["id"],
            "email": user["email"],
            "expires_at": expires_at,
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        base = os.environ.get("RESET_URL_BASE", "https://sustainability-ops-4.preview.emergentagent.com/reset-password")
        reset_link = f"{base}?token={raw}"
        _log_mail(
            subject="إعادة تعيين كلمة المرور — Edama",
            to=user["email"],
            body=f"مرحباً {user.get('name_ar','')},\n\nلإعادة تعيين كلمة المرور استخدم الرابط التالي (صالح لساعة واحدة):\n{reset_link}\n\nإن لم تطلب ذلك، تجاهل هذه الرسالة."
        )
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordIn):
    token_hash = _hash_token(payload.token)
    rec = await coll("password_reset_tokens").find_one({"token_hash": token_hash})
    if not rec:
        raise HTTPException(status_code=400, detail="رمز غير صالح أو منتهي")
    if rec.get("used"):
        raise HTTPException(status_code=400, detail="الرمز مستخدم مسبقاً")
    exp = rec.get("expires_at")
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp and datetime.now(timezone.utc) >= exp:
        raise HTTPException(status_code=400, detail="انتهت صلاحية الرمز")
    user = await coll("users").find_one({"id": rec["user_id"]})
    if not user:
        raise HTTPException(status_code=400, detail="رمز غير صالح")
    new_pv = int(user.get("pw_version", 0)) + 1
    now = datetime.now(timezone.utc).isoformat()
    await coll("users").update_one(
        {"id": user["id"]},
        {"$set": {
            "password_hash": hash_password(payload.new_password),
            "must_change_password": False,
            "pw_version": new_pv,
            "updated_at": now,
        }},
    )
    await coll("password_reset_tokens").update_one(
        {"token_hash": token_hash},
        {"$set": {"used": True, "used_at": now}},
    )
    # Clear brute-force on this email
    await coll("login_attempts").delete_one({"identifier": user["email"]})
    await coll("audit_log").insert_one({
        "user_email": user["email"], "user_id": user["id"],
        "action": "reset_password",
        "created_at": now,
    })
    return {"ok": True}
