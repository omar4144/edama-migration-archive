"""Seed auth accounts: owner admin + optional test consultant/evaluator.
Linked to real Lovable people where applicable.
"""
from __future__ import annotations
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Migration mode: seed script also needs to update users (users is not in the
# historical set, but keep it consistent for any future protected collections).
os.environ["EDAMA_MIGRATION_MODE"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from db import coll, ensure_indexes  # noqa: E402
from auth import hash_password, verify_password  # noqa: E402
from models import new_id  # noqa: E402


async def upsert_user(email: str, password: str, name_ar: str, role: str,
                     person_id: str | None = None, must_change: bool = False):
    now = datetime.now(timezone.utc).isoformat()
    existing = await coll("users").find_one({"email": email})
    if existing is None:
        await coll("users").insert_one({
            "id": new_id(),
            "email": email,
            "password_hash": hash_password(password),
            "name_ar": name_ar,
            "role": role,
            "person_id": person_id,
            "must_change_password": must_change,
            "pw_version": 0,
            "created_at": now,
            "updated_at": now,
        })
        print(f"[seed] created {role}: {email}")
    else:
        updates = {"name_ar": name_ar, "role": role, "person_id": person_id,
                   "updated_at": now}
        if not verify_password(password, existing["password_hash"]):
            updates["password_hash"] = hash_password(password)
        await coll("users").update_one({"email": email}, {"$set": updates})
        print(f"[seed] updated {role}: {email}")


async def main():
    await ensure_indexes()
    # Owner / admin — real signed-in user
    await upsert_user(
        email=os.environ["ADMIN_EMAIL"],
        password=os.environ["ADMIN_PASSWORD"],
        name_ar="مالك المنصة",
        role="admin",
        must_change=False,  # owner sets their own from env
    )
    # Test consultant — linked to first real Lovable consultant person
    cons_person = await coll("people").find_one({"role": "consultant"})
    await upsert_user(
        email=os.environ["CONSULTANT_TEST_EMAIL"],
        password=os.environ["CONSULTANT_TEST_PASSWORD"],
        name_ar="حساب اختبار — مستشار",
        role="consultant",
        person_id=cons_person.get("person_id") if cons_person else None,
        must_change=True,
    )
    # Test evaluator — linked to first real Lovable evaluator person
    eval_person = await coll("people").find_one({"role": "evaluator"})
    await upsert_user(
        email=os.environ["EVALUATOR_TEST_EMAIL"],
        password=os.environ["EVALUATOR_TEST_PASSWORD"],
        name_ar="حساب اختبار — محكّم",
        role="evaluator",
        person_id=eval_person.get("person_id") if eval_person else None,
        must_change=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
