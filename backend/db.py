"""MongoDB client, collections, indexes, and immutable guard."""
from motor.motor_asyncio import AsyncIOMotorClient
import os

from immutable import HISTORICAL_COLLECTIONS, ImmutableCollection, _is_migration_mode

_client: AsyncIOMotorClient | None = None
_db = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return _client


def get_db():
    global _db
    if _db is None:
        _db = get_client()[os.environ["DB_NAME"]]
    return _db


def coll(name: str):
    """Return collection accessor, wrapped in immutable guard for historical
    collections outside migration mode."""
    db = get_db()
    inner = db[name]
    if name in HISTORICAL_COLLECTIONS and not _is_migration_mode():
        return ImmutableCollection(inner, name, db["audit_log"])
    return inner


def raw_coll(name: str):
    """Escape hatch — direct DB access. USE ONLY IN MIGRATION SCRIPTS."""
    return get_db()[name]


async def ensure_indexes():
    db = get_db()
    # One-time migration: users created before pw_version existed
    await db.users.update_many({"pw_version": {"$exists": False}}, {"$set": {"pw_version": 0}})
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.audit_log.create_index([("created_at", -1)])
    await db.audit_log.create_index([("user_email", 1), ("created_at", -1)])
    await db.records_current.create_index("migration_id", unique=True)
    await db.records_current.create_index([("evaluator_person_id", 1)])
    await db.records_current.create_index([("consultant_person_id", 1)])
    await db.records_current.create_index([("organization_id", 1)])
    await db.records_current.create_index([("status", 1)])
    await db.organizations_current.create_index("organization_id", unique=True)
    await db.historical_organizations.create_index("legacy_org_id", unique=True)
    await db.historical_activities.create_index("legacy_activity_id", unique=True)
    await db.historical_arbitrations.create_index("legacy_review_id", unique=True)
    await db.historical_arbitrations.create_index([("evaluator_name", 1)])
    await db.historical_arbitrations.create_index([("cohort", 1)])
    await db.mappings.create_index([("kind", 1), ("status", 1)])
    await db.mappings.create_index("key", unique=True)
