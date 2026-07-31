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

app.include_router(api)

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    await ensure_indexes()
