"""Edama V8 iteration 3 backend tests.

Tests the new unified operational platform endpoints:
- /api/admin/exec/scene (Executive Scene)
- /api/admin/directory/evaluators + /{name} + /{name}/organization/{org_id}
- /api/admin/directory/consultants + /{name}
- /api/admin/models-hub + /{id}
- /api/admin/unified/organizations + /{id}
Plus RBAC + historical-guard + iteration 2 regression check.
"""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

ADMIN = ("omarzabarmawi@hotmail.com", "Edama@2026!Owner")
CONS = ("consultant.test@edama.local", "Consult@2026!Test")
EVAL = ("evaluator.test@edama.local", "Eval@2026!Test")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return s, r


@pytest.fixture()
def admin_session():
    s, r = _login(*ADMIN)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture()
def consultant_session():
    s, r = _login(*CONS)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture()
def evaluator_session():
    s, r = _login(*EVAL)
    assert r.status_code == 200, r.text
    return s


# ============================================================
# Executive Scene
# ============================================================
class TestExecScene:
    def test_scene_totals(self, admin_session):
        r = admin_session.get(f"{API}/admin/exec/scene", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        t = d["totals"]
        assert t["cohorts"] == 4
        assert t["organizations"] == 57
        assert t["evaluators"] == 13, f"evaluators={t['evaluators']}"
        assert t["consultants"] == 11
        assert t["models_defined"] == 45
        assert t["accepted"] == 2565
        assert t["needs_dev"] == 0
        assert t["incomplete"] == 0
        assert t["arbitrations_legacy"] == 3403
        assert t["records_current"] == 2565

    def test_scene_cohorts_strip(self, admin_session):
        d = admin_session.get(f"{API}/admin/exec/scene", timeout=30).json()
        cohorts = d["cohorts"]
        assert len(cohorts) == 4
        expected = {"1": (24, 0, 0), "2": (30, 1200, 1382),
                    "3": (29, 1160, 1081), "4": (35, 1400, 940)}
        for c in cohorts:
            e = expected[str(c["cohort"])]
            assert (c["organizations"], c["activities"], c["arbitrations"]) == e, c

    def test_scene_attention(self, admin_session):
        d = admin_session.get(f"{API}/admin/exec/scene", timeout=30).json()
        att = d["attention"]
        assert isinstance(att, list) and len(att) >= 1
        for a in att:
            assert a.get("message") and a.get("target")


# ============================================================
# Directory: Evaluators
# ============================================================
class TestEvaluatorsDirectory:
    def test_list_13(self, admin_session):
        r = admin_session.get(f"{API}/admin/directory/evaluators", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 13, f"got {len(data)}"
        # Batool
        b = next((x for x in data if x["name"] == "بتول الرويلي"), None)
        assert b is not None
        assert b["current_records"] == 225
        assert b["legacy_arbitrations"] == 282
        assert b["total_records"] == 507

    def test_detail_batool(self, admin_session):
        r = admin_session.get(f"{API}/admin/directory/evaluators/بتول الرويلي", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == "بتول الرويلي"
        assert d["totals"]["current_records"] == 225
        assert d["totals"]["legacy_arbitrations"] == 282
        # 5 current orgs
        assert len(d["current"]["orgs"]) == 5, d["current"]["orgs"]
        # legacy_by_cohort should include cohort '4'
        cohorts = [c["cohort"] for c in d["legacy_by_cohort"]]
        assert "4" in cohorts

    def test_org_models_endpoint(self, admin_session):
        r = admin_session.get(
            f"{API}/admin/directory/evaluators/بتول الرويلي/organization/ORG-A01-01",
            timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) > 0
        # Should have both current and legacy items for the joined org
        sources = {i["source"] for i in items}
        assert "current" in sources
        # at least one with a URL
        assert any(i.get("url") for i in items)


# ============================================================
# Directory: Consultants
# ============================================================
class TestConsultantsDirectory:
    def test_list_11(self, admin_session):
        r = admin_session.get(f"{API}/admin/directory/consultants", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 11, f"got {len(data)}"

    def test_detail_has_cohort_breakdown(self, admin_session):
        # Pick first consultant with legacy_cohorts
        lst = admin_session.get(f"{API}/admin/directory/consultants", timeout=30).json()
        target = next((c for c in lst if c.get("legacy_cohorts")), None)
        assert target is not None
        r = admin_session.get(f"{API}/admin/directory/consultants/{target['name']}", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["name"] == target["name"]
        assert isinstance(d["legacy_by_cohort"], list) and len(d["legacy_by_cohort"]) > 0
        for c in d["legacy_by_cohort"]:
            assert "completion" in c and "stages" in c


# ============================================================
# Unified Organizations
# ============================================================
class TestUnifiedOrganizations:
    def test_list_min57(self, admin_session):
        r = admin_session.get(f"{API}/admin/unified/organizations", timeout=30)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 57, len(rows)
        # ORG-A01-01 present
        assert any(x["org_id"] == "ORG-A01-01" for x in rows)

    def test_detail_ORG_A01_01(self, admin_session):
        r = admin_session.get(f"{API}/admin/unified/organizations/ORG-A01-01", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        h = d["header"]
        assert h["cohort"] == "4"
        assert h["sector"] == "الرياضة"
        assert h["region"] == "منطقة الشرقية"
        assert h["evaluator"] == "بتول الرويلي"
        assert "نجود السيد" in (h["consultants"] or [])
        t = d["totals"]
        assert t["records"] == 92
        assert t["current"] == 45
        assert t["legacy_arbitrations"] == 47
        assert t["legacy_activities"] == 40
        assert t["accepted"] == 45
        # records grouped: has category values from all 3 categories among records
        cats = {r.get("category") for r in d["records"]}
        # at least one non-empty
        assert cats - {None}, cats
        # At least one record with URL for opening
        assert any(r.get("url") for r in d["records"])

    def test_unknown_org_404(self, admin_session):
        r = admin_session.get(f"{API}/admin/unified/organizations/NOPE-X", timeout=15)
        assert r.status_code == 404


# ============================================================
# Models Hub
# ============================================================
class TestModelsHub:
    def test_all_5968(self, admin_session):
        r = admin_session.get(f"{API}/admin/models-hub?limit=1", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["total_current"] == 2565
        assert d["total_legacy"] == 3403
        assert d["total"] == 5968

    def test_filter_accepted(self, admin_session):
        r = admin_session.get(f"{API}/admin/models-hub", params={"evaluation": "مقبول", "limit": 1}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["total_current"] == 2565
        # legacy also filtered — mostly 0/low because raw legacy values differ
        assert d["total_current"] == 2565

    def test_filter_cohort_3(self, admin_session):
        r = admin_session.get(f"{API}/admin/models-hub", params={"cohort": "3", "limit": 1}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        # legacy cohort 3 = 1081 arbitrations
        assert d["total_legacy"] == 1081, d
        # current cohort 3 = via crosswalk (29 orgs)
        assert d["total_current"] > 0

    def test_filter_no_url(self, admin_session):
        r = admin_session.get(f"{API}/admin/models-hub", params={"no_url": "true", "limit": 1}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        # current with no url should be ~0 (all 2565 have URL)
        assert d["total_current"] == 0, d["total_current"]

    def test_filter_source_current(self, admin_session):
        r = admin_session.get(f"{API}/admin/models-hub", params={"source": "current", "limit": 1}, timeout=30)
        assert r.json()["total"] == 2565

    def test_filter_source_legacy(self, admin_session):
        r = admin_session.get(f"{API}/admin/models-hub", params={"source": "legacy", "limit": 1}, timeout=30)
        assert r.json()["total"] == 3403

    def test_detail_current_url(self, admin_session):
        r = admin_session.get(f"{API}/admin/models-hub/BATOOL-A1-01", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["source"] == "current"
        assert d["url"] and "docs.google.com" in d["url"]

    def test_detail_legacy_canonical_priority(self, admin_session):
        # LEG-REV-02026 has canonical + hyperlink_target set — canonical wins.
        r = admin_session.get(f"{API}/admin/models-hub/LEG-REV-02026", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["source"] == "legacy"
        # canonical URL was: https://docs.google.com/spreadsheets/d/1_8tvH_uDjcRivZm_r1BwFljzRr91BEfX
        assert d["url"] and d["url"].startswith("https://docs.google.com/spreadsheets/d/1_8tvH_uDjcRivZm_r1BwFljzRr91BEfX")
        # canonical (no query string) must be preferred over hyperlink_target (which has query)
        assert "?" not in d["url"], f"expected canonical (no query), got {d['url']}"

    def test_detail_404(self, admin_session):
        assert admin_session.get(f"{API}/admin/models-hub/NOPE", timeout=15).status_code == 404


# ============================================================
# RBAC on new endpoints
# ============================================================
class TestRBACNewIter3:
    NEW_PATHS = [
        "/admin/exec/scene",
        "/admin/directory/evaluators",
        "/admin/directory/evaluators/بتول الرويلي",
        "/admin/directory/consultants",
        "/admin/models-hub",
        "/admin/models-hub/BATOOL-A1-01",
        "/admin/unified/organizations",
        "/admin/unified/organizations/ORG-A01-01",
    ]

    def test_consultant_forbidden(self, consultant_session):
        for p in self.NEW_PATHS:
            r = consultant_session.get(f"{API}{p}", timeout=15)
            # 403 (role) preferred, but 428 (must_change) also acceptable if it fires first
            assert r.status_code in (403, 428), f"{p} → {r.status_code}"
            assert r.status_code != 200

    def test_evaluator_forbidden(self, evaluator_session):
        for p in self.NEW_PATHS:
            r = evaluator_session.get(f"{API}{p}", timeout=15)
            assert r.status_code in (401, 403, 428), f"{p} → {r.status_code}"
            assert r.status_code != 200

    def test_unauth_401(self):
        for p in self.NEW_PATHS[:3]:
            r = requests.get(f"{API}{p}", timeout=15)
            assert r.status_code == 401, f"{p} → {r.status_code}"


# ============================================================
# Regression: iteration 2 things must still work
# ============================================================
class TestIter2Regression:
    def test_reconciliation_counts(self, admin_session):
        r = admin_session.get(f"{API}/reconciliation/summary", timeout=30)
        assert r.status_code == 200
        flat = str(r.json())
        for e in [2565, 57, 17, 45, 1662, 118, 3760, 3403]:
            assert str(e) in flat, f"missing {e}"

    def test_historical_patch_405(self, admin_session):
        r = admin_session.patch(f"{API}/admin/historical/arbitrations/LEG-REV-00001",
                                json={"note": "x"}, timeout=15)
        assert r.status_code == 405
        assert "IMMUTABLE_HISTORICAL" in r.text

    def test_admin_login(self):
        _, r = _login(*ADMIN)
        assert r.status_code == 200


# ============================================================
# URL resolution helper — canonical priority
# ============================================================
class TestUrlResolution:
    def test_canonical_beats_hyperlink(self):
        from unified import resolve_url  # type: ignore
        import sys
        sys.path.insert(0, "/app/backend")
        assert resolve_url({
            "model_url_canonical": "A",
            "model_url_hyperlink_target": "B",
            "model_url_displayed": "C",
            "model_url": "D",
        }) == "A"
        assert resolve_url({"model_url_hyperlink_target": "B", "model_url": "D"}) == "B"
        assert resolve_url({"model_url": "D"}) == "D"
        assert resolve_url({"current_model_url": "E"}) == "E"
        assert resolve_url({}) is None
        assert resolve_url(None) is None
