"""Edama V8 backend integration tests.

Covers auth (admin/consultant/evaluator), reconciliation counts, RBAC 401/403 guards,
REVIEW_REQUIRED queue behaviour, consultant/evaluator scoped endpoints, brute force lockout.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sustainability-ops-4.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("omarzabarmawi@hotmail.com", "Edama@2026!Owner")
CONS = ("consultant.test@edama.local", "Consult@2026!Test")
EVAL = ("evaluator.test@edama.local", "Eval@2026!Test")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return s, r


@pytest.fixture(scope="session")
def admin_session():
    s, r = _login(*ADMIN)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s

@pytest.fixture(scope="session")
def consultant_session():
    s, r = _login(*CONS)
    assert r.status_code == 200, f"consultant login failed: {r.status_code} {r.text}"
    return s

@pytest.fixture(scope="session")
def evaluator_session():
    s, r = _login(*EVAL)
    assert r.status_code == 200, f"evaluator login failed: {r.status_code} {r.text}"
    return s


# ---------------- Auth ----------------
class TestAuth:
    def test_admin_login_sets_cookies(self):
        s, r = _login(*ADMIN)
        assert r.status_code == 200
        data = r.json()
        # role check
        user = data.get("user") or data
        assert user.get("role") == "admin"
        # cookie present
        cookie_names = {c.name for c in s.cookies}
        assert any("access" in n.lower() or "token" in n.lower() for n in cookie_names), f"cookies={cookie_names}"

    def test_me_with_cookie(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json().get("role") == "admin"

    def test_refresh(self, admin_session):
        r = admin_session.post(f"{API}/auth/refresh", timeout=15)
        assert r.status_code == 200

    def test_unauthenticated_returns_401(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_protected_endpoint_no_auth_401(self):
        r = requests.get(f"{API}/reconciliation/summary", timeout=15)
        assert r.status_code == 401

    def test_invalid_login(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN[0], "password": "wrongwrong"}, timeout=15)
        assert r.status_code in (400, 401)


# ---------------- Reconciliation counts ----------------
class TestReconciliation:
    def test_summary_counts(self, admin_session):
        r = admin_session.get(f"{API}/reconciliation/summary", timeout=30)
        assert r.status_code == 200
        data = r.json()
        # dump for debug
        print("SUMMARY:", data)
        # find integers anywhere
        flat = str(data)
        expected = [2565, 57, 17, 45, 118, 3760, 3403, 67, 120]
        missing = [e for e in expected if str(e) not in flat]
        assert not missing, f"missing counts in summary: {missing}. data={data}"
        # hours 1662.0
        assert "1662" in flat, f"missing 1662 hours in {data}"

    def test_pending_mappings_9(self, admin_session):
        r = admin_session.get(f"{API}/reconciliation/mappings", params={"status": "pending"}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("mappings", []))
        assert len(items) == 9, f"expected 9 pending, got {len(items)}"
        kinds = {}
        for it in items:
            k = it.get("kind") or it.get("type")
            kinds[k] = kinds.get(k, 0) + 1
        assert kinds.get("organization_probable_match", 0) == 1, kinds
        assert kinds.get("model_evolved_schema", 0) == 3, kinds
        assert kinds.get("evaluator_assignment_changed", 0) == 5, kinds

    def test_admin_lists(self, admin_session):
        # organizations
        r = admin_session.get(f"{API}/admin/organizations", timeout=30)
        assert r.status_code == 200
        orgs = r.json()
        orgs = orgs if isinstance(orgs, list) else orgs.get("items", [])
        assert len(orgs) == 57, f"expected 57 orgs, got {len(orgs)}"

        r = admin_session.get(f"{API}/admin/people", timeout=30)
        assert r.status_code == 200
        p = r.json(); p = p if isinstance(p, list) else p.get("items", [])
        assert len(p) == 17

        r = admin_session.get(f"{API}/admin/models", timeout=30)
        assert r.status_code == 200
        m = r.json(); m = m if isinstance(m, list) else m.get("items", [])
        assert len(m) == 45

        r = admin_session.get(f"{API}/admin/organizations/historical", timeout=30)
        assert r.status_code == 200
        h = r.json(); h = h if isinstance(h, list) else h.get("items", [])
        assert len(h) == 118


# ---------------- RBAC ----------------
class TestRBAC:
    def test_consultant_cannot_admin(self, consultant_session):
        r = consultant_session.get(f"{API}/reconciliation/summary", timeout=15)
        assert r.status_code == 403
        r = consultant_session.get(f"{API}/admin/organizations", timeout=15)
        assert r.status_code == 403

    def test_consultant_cannot_evaluator(self, consultant_session):
        r = consultant_session.get(f"{API}/evaluator/queue", timeout=15)
        assert r.status_code == 403

    def test_evaluator_cannot_admin(self, evaluator_session):
        r = evaluator_session.get(f"{API}/reconciliation/summary", timeout=15)
        assert r.status_code == 403

    def test_evaluator_cannot_consultant(self, evaluator_session):
        r = evaluator_session.get(f"{API}/consultant/submissions", timeout=15)
        assert r.status_code == 403

    def test_admin_cannot_consultant_endpoint(self, admin_session):
        # admin isn't consultant either — should be 403
        r = admin_session.get(f"{API}/consultant/submissions", timeout=15)
        assert r.status_code == 403


# ---------------- Consultant scope ----------------
class TestConsultant:
    def test_submissions_count(self, consultant_session):
        r = consultant_session.get(f"{API}/consultant/submissions", timeout=30)
        assert r.status_code == 200
        d = r.json(); items = d if isinstance(d, list) else d.get("items", [])
        assert len(items) == 270, f"expected 270 got {len(items)}"

    def test_activities(self, consultant_session):
        r = consultant_session.get(f"{API}/consultant/activities", timeout=30)
        assert r.status_code == 200


# ---------------- Evaluator scope ----------------
class TestEvaluator:
    def test_queue_count(self, evaluator_session):
        r = evaluator_session.get(f"{API}/evaluator/queue", timeout=30)
        assert r.status_code == 200
        d = r.json(); items = d if isinstance(d, list) else d.get("items", [])
        assert len(items) == 225, f"expected 225 got {len(items)}"

    def test_hours_summary(self, evaluator_session):
        r = evaluator_session.get(f"{API}/evaluator/hours-summary", timeout=30)
        assert r.status_code == 200
        flat = str(r.json())
        assert "136" in flat

    def test_evaluator_orgs(self, evaluator_session):
        r = evaluator_session.get(f"{API}/evaluator/organizations", timeout=30)
        assert r.status_code == 200
        d = r.json(); items = d if isinstance(d, list) else d.get("items", [])
        assert len(items) == 5, f"expected 5 orgs got {len(items)}"


# ---------------- Brute force ----------------
class TestBruteForce:
    def test_lockout_after_5_failures(self):
        email = f"bruteforce_{int(time.time())}@edama.local"
        codes = []
        for _ in range(6):
            r = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": "wrong"}, timeout=15)
            codes.append(r.status_code)
        print("brute codes:", codes)
        # last should be 429; first 5 should be 401/400
        assert 429 in codes, f"expected 429 in {codes}"
