"""FastAPI server entry."""
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import os
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from db import ensure_indexes
from routes.auth_routes import router as auth_router
from routes.reconciliation import router as reconciliation_router
from routes.admin import router as admin_router
from routes.consultant import router as consultant_router
from routes.evaluator import router as evaluator_router
from routes.dq import router as dq_router
from routes.historical import router as historical_router
from routes.exec_scene import router as exec_router
from routes.directory import router as directory_router
from routes.models_hub import router as models_hub_router
from routes.unified_org import router as unified_org_router
from routes.canonical import router as canonical_router


app = FastAPI(title="Edama — Musr'at Idama V8")

api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"service": "edama-v8", "status": "ok"}


@api.get("/health")
async def health():
    return {"status": "ok"}


api.include_router(auth_router)
api.include_router(reconciliation_router)
api.include_router(admin_router)
api.include_router(dq_router, prefix="/admin")  # /api/admin/dq/*
api.include_router(historical_router)  # already has /admin/* & /evaluator/* prefixes
api.include_router(consultant_router)
api.include_router(evaluator_router)
api.include_router(exec_router, prefix="/admin")  # /api/admin/exec/scene
api.include_router(directory_router, prefix="/admin")  # /api/admin/directory/*
api.include_router(models_hub_router, prefix="/admin")  # /api/admin/models-hub
api.include_router(unified_org_router, prefix="/admin/unified")  # /api/admin/unified/organizations
api.include_router(canonical_router, prefix="/admin")  # /api/admin/canonical/*

app.include_router(api)

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _cleanup_login_attempts():
    """Best-effort cleanup of stale brute-force records on startup so lockouts
    don't persist across restarts of a test environment."""
    from db import get_db
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    try:
        await get_db()["login_attempts"].delete_many({"last_at": {"$lt": cutoff}})
    except Exception:
        pass


@app.on_event("startup")
async def _startup():
    await ensure_indexes()
    await _cleanup_login_attempts()
