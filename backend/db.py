"""MongoDB client, collections, and index setup."""
from motor.motor_asyncio import AsyncIOMotorClient
import os

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


# Collection accessors (thin wrappers so tests can override)
def coll(name: str):
    return get_db()[name]


COLLECTIONS = {
    # Auth & audit
    "users": "users",
    "login_attempts": "login_attempts",
    "password_reset_tokens": "password_reset_tokens",
    "audit_log": "audit_log",
    # Reference
    "cohorts": "cohorts",
    "people": "people",
    "model_definitions": "model_definitions",
    "organizations_current": "organizations_current",
    "assignments": "assignments",
    # Current authoritative records (Lovable)
    "records_current": "records_current",
    "duplicate_links_current": "duplicate_links_current",
    # Immutable historical
    "historical_organizations": "historical_organizations",
    "historical_activities": "historical_activities",
    "historical_arbitrations": "historical_arbitrations",
    "historical_duplicate_links": "historical_duplicate_links",
    "historical_batch_plans": "historical_batch_plans",
    "historical_batch_kpis": "historical_batch_kpis",
    # Crosswalks (advisory only)
    "crosswalk_organizations": "crosswalk_organizations",
    "crosswalk_models": "crosswalk_models",
    "crosswalk_records": "crosswalk_records",
    # Mapping decisions (REVIEW_REQUIRED queue)
    "mappings": "mappings",
    # Quality
    "quality_checks": "quality_checks",
    "source_inventory": "source_inventory",
    "migration_runs": "migration_runs",
}


async def ensure_indexes():
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
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
    await db.mappings.create_index([("kind", 1), ("status", 1)])
    await db.mappings.create_index("key", unique=True)
