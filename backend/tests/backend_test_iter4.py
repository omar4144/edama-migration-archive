"""Iteration 4 backend tests — Canonical Deduplication Layer.

Covers:
  * dedup.normalize_url pure-function behaviour
  * GET /api/admin/canonical/report contract + stats sanity
  * GET /api/admin/canonical/submissions filters (org_id, match_status)
  * GET /api/admin/canonical/submissions/{canonical_id} detail + members
  * RBAC: consultant + evaluator get 403 on canonical/report
  * Historical write-guard regression (PATCH → 405)
  * Reconciliation summary regression (raw source counts unchanged)
  * Idempotency of build_canonical.py
"""
import os
import sys
import subprocess
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://sustainability-ops-4.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("omarzabarmawi@hotmail.com", "Edama@2026!Owner")
CONSULTANT = ("consultant.test@edama.local", "Consult@2026!Test")
EVALUATOR = ("evaluator.test@edama.local", "Eval@2026!Test")


# ----------------------- Fixtures -----------------------
def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def consultant():
    return _login(*CONSULTANT)


@pytest.fixture(scope="module")
def evaluator():
    return _login(*EVALUATOR)


@pytest.fixture(scope="module")
def report(admin):
    r = admin.get(f"{API}/admin/canonical/report", timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


# ----------------------- URL Normalization -----------------------
sys.path.insert(0, "/app/backend")
from dedup import normalize_url  # noqa: E402


class TestNormalizeUrl:
    def test_gdocs_spreadsheet(self):
        key, fid = normalize_url(
            "https://docs.google.com/spreadsheets/d/1OAJIlQgd3xpZkSqmuNCX4ZUjmNYr22Nf/edit?usp=sharing&ouid=x"
        )
        assert key == "gdrive:1OAJIlQgd3xpZkSqmuNCX4ZUjmNYr22Nf"
        assert fid == "1OAJIlQgd3xpZkSqmuNCX4ZUjmNYr22Nf"

    def test_drive_file(self):
        # docs.google.com regex only — drive.google.com URLs aren't captured by GDRIVE_RE.
        # This test documents actual behaviour.
        key, fid = normalize_url(
            "https://drive.google.com/file/d/1APcxwe7jeBhEfHmY3GlzF3gSlF4aqSPI/view"
        )
        # Falls back to generic path stripping (strips /view suffix)
        assert key is not None
        # Either regex-matched or fallback-normalized — assert deterministic + no /view
        assert "/view" not in (key or "")

    def test_none_empty(self):
        assert normalize_url(None) == (None, None)
        assert normalize_url("") == (None, None)
        assert normalize_url("   ") == (None, None)

    def test_generic_strip_edit_lower(self):
        key, fid = normalize_url("https://example.com/Foo/Bar/edit")
        assert fid is None
        assert key == "https://example.com/foo/bar"


# ----------------------- Canonical Report -----------------------
class TestCanonicalReport:
    def test_report_status_and_shape(self, report):
        assert "report" in report
        assert "by_match_status" in report and isinstance(report["by_match_status"], dict)
        assert "samples" in report and isinstance(report["samples"], list)
        assert len(report["samples"]) >= 1 and len(report["samples"]) <= 20

    def test_stats_expected_numbers(self, report):
        s = report["report"]["stats"]
        assert s["raw_current"] == 2565
        assert s["raw_legacy"] == 3403
        assert s["canonical_total"] == 4020
        assert s["exact_cross_source"] == 1018
        assert s["current_only"] == 499
        assert s["review_required"] == 226
        assert s["legacy_only"] == 2277
        assert s["internal_dup_current"] == 822
        assert s["internal_dup_legacy"] == 108
        assert s["duplicate_groups"] == 195
        assert s["hours_operational_deduped"] == pytest.approx(45077.5, rel=1e-3)

    def test_sum_of_statuses_equals_total(self, report):
        s = report["report"]["stats"]
        assert (s["exact_cross_source"] + s["current_only"] + s["review_required"]
                + s["legacy_only"]) == s["canonical_total"]

    def test_by_match_status_matches_stats(self, report):
        s = report["report"]["stats"]
        bms = report["by_match_status"]
        assert bms.get("EXACT_CROSS_SOURCE_MATCH") == s["exact_cross_source"]
        assert bms.get("CURRENT_ONLY") == s["current_only"]
        assert bms.get("REVIEW_REQUIRED") == s["review_required"]
        assert bms.get("LEGACY_ONLY") == s["legacy_only"]

    def test_sample_shape(self, report):
        for s in report["samples"]:
            assert "canonical_id" in s
            assert "match_status" in s
            assert "match_reason" in s
            assert "confidence" in s
            assert "organization_name" in s
            assert "primary_source" in s
            assert "primary_source_id" in s
            assert isinstance(s.get("members"), list) and len(s["members"]) >= 1
            for m in s["members"]:
                assert m["source"] in ("current", "legacy")
                assert "raw_id" in m
                assert "confidence" in m
                assert "evidence" in m

    def test_sample_contains_org_a01_01_exact(self, report):
        matches = [s for s in report["samples"]
                   if s.get("organization_id") == "ORG-A01-01"
                   and s.get("match_status") == "EXACT_CROSS_SOURCE_MATCH"]
        assert matches, "expected at least one ORG-A01-01 EXACT sample (جمعية المشي والجري)"

    def test_sample_contains_batool_evaluator(self, report):
        matches = [s for s in report["samples"]
                   if s.get("evaluator_name") == "بتول الرويلي"
                   and s.get("match_status") == "EXACT_CROSS_SOURCE_MATCH"]
        assert matches, "expected at least one بتول الرويلي EXACT sample"

    def test_exact_sample_has_current_and_legacy_members(self, report):
        exact = [s for s in report["samples"]
                 if s.get("match_status") == "EXACT_CROSS_SOURCE_MATCH"]
        assert exact
        for s in exact:
            sources = {m["source"] for m in s["members"]}
            assert "current" in sources and "legacy" in sources, \
                f"EXACT canonical {s['canonical_id']} missing current+legacy members"


# ----------------------- Submissions List -----------------------
class TestCanonicalSubmissions:
    @pytest.mark.parametrize("status,expected", [
        ("EXACT_CROSS_SOURCE_MATCH", 1018),
        ("REVIEW_REQUIRED", 226),
        ("LEGACY_ONLY", 2277),
        ("CURRENT_ONLY", 499),
    ])
    def test_filter_by_match_status(self, admin, status, expected):
        r = admin.get(f"{API}/admin/canonical/submissions",
                      params={"match_status": status, "limit": 1}, timeout=30)
        assert r.status_code == 200
        assert r.json()["total"] == expected

    def test_filter_by_org_a01_01(self, admin):
        r = admin.get(f"{API}/admin/canonical/submissions",
                      params={"org_id": "ORG-A01-01", "limit": 200}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        for it in data["items"]:
            assert it["organization_id"] == "ORG-A01-01"

    def test_org_a01_01_members_link_back_to_raw(self, admin):
        r = admin.get(f"{API}/admin/canonical/submissions",
                      params={"org_id": "ORG-A01-01",
                              "match_status": "EXACT_CROSS_SOURCE_MATCH",
                              "limit": 5}, timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        assert items
        target = items[0]["canonical_id"]
        det = admin.get(f"{API}/admin/canonical/submissions/{target}", timeout=30)
        assert det.status_code == 200
        body = det.json()
        sources = {m["source"] for m in body["members"]}
        assert "current" in sources and "legacy" in sources

    def test_detail_404(self, admin):
        r = admin.get(f"{API}/admin/canonical/submissions/CANON-DOES-NOT-EXIST",
                      timeout=15)
        assert r.status_code == 404


# ----------------------- RBAC -----------------------
class TestRBAC:
    def test_consultant_forbidden_report(self, consultant):
        r = consultant.get(f"{API}/admin/canonical/report", timeout=15)
        assert r.status_code == 403

    def test_evaluator_forbidden_report(self, evaluator):
        r = evaluator.get(f"{API}/admin/canonical/report", timeout=15)
        assert r.status_code == 403

    def test_consultant_forbidden_submissions(self, consultant):
        r = consultant.get(f"{API}/admin/canonical/submissions", timeout=15)
        assert r.status_code == 403


# ----------------------- Regressions -----------------------
class TestRegressions:
    def test_historical_write_guard_405(self, admin):
        r = admin.patch(f"{API}/admin/historical/arbitrations/anything",
                        json={"foo": "bar"}, timeout=15)
        assert r.status_code == 405

    def test_reconciliation_summary_counts_unchanged(self, admin):
        r = admin.get(f"{API}/reconciliation/summary", timeout=30)
        assert r.status_code == 200
        c = r.json().get("counts", {})
        # source counts derivation-only, must be identical to iter2/iter3
        assert c.get("records_current") == 2565
        assert c.get("organizations_current") == 57
        assert c.get("historical_arbitrations") == 3403
        assert c.get("historical_activities") == 3760
        assert c.get("historical_organizations") == 118


# ----------------------- Idempotency -----------------------
class TestIdempotency:
    def test_rebuild_produces_same_totals(self, admin):
        # Run build_canonical.py again and compare
        before = admin.get(f"{API}/admin/canonical/report", timeout=60).json()
        b_stats = before["report"]["stats"]

        proc = subprocess.run(
            ["python", "migrations/build_canonical.py"],
            cwd="/app/backend", capture_output=True, text=True, timeout=180,
        )
        assert proc.returncode == 0, f"build_canonical failed: {proc.stderr}"

        after = admin.get(f"{API}/admin/canonical/report", timeout=60).json()
        a_stats = after["report"]["stats"]

        for k in ("raw_current", "raw_legacy", "canonical_total",
                  "exact_cross_source", "current_only", "review_required",
                  "legacy_only", "duplicate_groups"):
            assert a_stats[k] == b_stats[k], f"idempotency broken for {k}: {b_stats[k]} → {a_stats[k]}"
