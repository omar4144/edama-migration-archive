"""Immutable historical collections guard (defense in depth at the DB layer).

The migration script sets EDAMA_MIGRATION_MODE=1 before importing this module to
bypass the guard for its own idempotent load. All other code paths — HTTP handlers,
bulk update jobs, direct scripts — get an ImmutableCollection wrapper that raises
on writes and records the attempt in audit_log.
"""
import asyncio
import os
from datetime import datetime, timezone
from fastapi import HTTPException


# Collections whose data was ingested from the archive and must never be mutated
# by the running application. Only the migration script may write to them.
HISTORICAL_COLLECTIONS = frozenset({
    "historical_organizations",
    "historical_activities",
    "historical_arbitrations",
    "historical_duplicate_links",
    "historical_batch_plans",
    "historical_batch_kpis",
    "crosswalk_organizations",
    "crosswalk_models",
    "crosswalk_records",
    "assignments",
    "source_inventory",
    "quality_checks",
})


class HistoricalWriteError(HTTPException):
    def __init__(self, coll_name: str, op: str):
        super().__init__(
            status_code=405,
            detail=f"IMMUTABLE_HISTORICAL: '{op}' غير مسموح على '{coll_name}' — الطبقة التاريخية للقراءة فقط.",
        )
        self.coll_name = coll_name
        self.op = op


def _is_migration_mode() -> bool:
    return os.environ.get("EDAMA_MIGRATION_MODE") == "1"


class ImmutableCollection:
    """Wraps a motor collection. Read ops pass through, write ops raise + audit."""

    _WRITE_OPS = {
        "insert_one", "insert_many",
        "update_one", "update_many", "replace_one",
        "delete_one", "delete_many",
        "find_one_and_update", "find_one_and_replace", "find_one_and_delete",
        "bulk_write", "drop", "rename",
    }

    def __init__(self, inner, name: str, audit_coll):
        self._inner = inner
        self._name = name
        self._audit_coll = audit_coll

    def __getattr__(self, item):
        if item in self._WRITE_OPS:
            return self._blocked(item)
        return getattr(self._inner, item)

    def _blocked(self, op: str):
        async def _fn(*args, **kwargs):
            # Log attempt then raise
            try:
                await self._audit_coll.insert_one({
                    "action": "historical_write_blocked",
                    "collection": self._name,
                    "op": op,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass
            raise HistoricalWriteError(self._name, op)
        return _fn
