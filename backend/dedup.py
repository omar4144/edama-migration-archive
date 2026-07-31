"""Canonical deduplication layer — pure derivation from raw data.

Never mutates source_records. Produces:
- canonical_submissions: one operational submission per (org, model) unit
- record_crosswalks: raw-row → canonical mapping with match evidence
- duplicate_groups: groups of raw rows treated as the same submission
- canonical_reviews: unified arbitration decision (one per submission where possible)

Match levels:
  EXACT_CROSS_SOURCE_MATCH    — auto-merge (URL file-id + org + model all match)
  PROBABLE_CROSS_SOURCE_MATCH — auto-merge only if confidence ≥ threshold
                                (org + model + evaluator + consultant + date-bucket)
  VERSION_NOT_DUPLICATE       — same (org, model) but different URL/date → separate version
  REVIEW_REQUIRED             — name-only or conflicting evidence, no auto-merge
"""
import re
from urllib.parse import urlsplit, parse_qsl


GDRIVE_RE = re.compile(
    r"docs\.google\.com/(?:document|spreadsheets|presentation|forms|drive/folders)/d/([a-zA-Z0-9_-]{10,})",
)
ONEDRIVE_RE = re.compile(r"[?&](?:resid|id)=([^&]+)", re.IGNORECASE)


def normalize_url(u):
    """Return (canonical_key, file_id or None).
    canonical_key is stable across cosmetic URL variations (query strings, /edit).
    """
    if not u or not isinstance(u, str):
        return None, None
    u = u.strip()
    if not u:
        return None, None

    # Google Drive family — extract file ID
    m = GDRIVE_RE.search(u)
    if m:
        fid = m.group(1)
        return f"gdrive:{fid}", fid

    # OneDrive — best-effort id extraction
    m = ONEDRIVE_RE.search(u)
    if m:
        rid = m.group(1)
        return f"onedrive:{rid}", rid

    # Generic fallback: strip query + fragment + trailing slash & common view suffixes
    try:
        p = urlsplit(u)
        path = p.path.rstrip("/")
        for suffix in ("/edit", "/view", "/preview", "/comment"):
            if path.endswith(suffix):
                path = path[: -len(suffix)]
                break
        key = f"{p.scheme}://{p.netloc}{path}".lower()
        return key, None
    except Exception:
        return u.lower(), None


def date_bucket(iso_date, days=90):
    """Group dates into a coarse bucket for probable-match date proximity."""
    if not iso_date:
        return None
    try:
        # Accept YYYY-MM-DD or ISO datetime
        y, m, d = iso_date[:10].split("-")
        y, m, d = int(y), int(m), int(d)
        total_days = y * 365 + m * 30 + d
        return total_days // days
    except Exception:
        return None


# Confidence weights (0-100)
CONF_URL_MATCH = 50
CONF_ORG_MATCH = 15
CONF_MODEL_MATCH = 15
CONF_EVAL_MATCH = 8
CONF_CONS_MATCH = 6
CONF_DATE_CLOSE = 6

THRESHOLD_AUTO_MERGE = 65   # anything at/above this is auto-canonicalized
THRESHOLD_REVIEW = 30       # below this is REVIEW_REQUIRED


def score_pair(current, legacy_matched, url_key_c, url_key_l, model_id_c, model_id_l):
    """Score a potential cross-source pair. Both records already resolved
    to the same organization_id. Returns (score, evidence_list)."""
    score, evidence = 0, []
    if url_key_c and url_key_l and url_key_c == url_key_l:
        score += CONF_URL_MATCH
        evidence.append(f"url_file_id={url_key_c}")
    score += CONF_ORG_MATCH  # caller already ensured
    evidence.append("org_matched")
    if model_id_c and model_id_l and model_id_c == model_id_l:
        score += CONF_MODEL_MATCH
        evidence.append("model_matched")
    if current.get("evaluator_name") and legacy_matched.get("evaluator_name") \
            and current["evaluator_name"] == legacy_matched["evaluator_name"]:
        score += CONF_EVAL_MATCH
        evidence.append("evaluator_matched")
    if current.get("consultant_name") and legacy_matched.get("consultant_name") \
            and current["consultant_name"] == legacy_matched["consultant_name"]:
        score += CONF_CONS_MATCH
        evidence.append("consultant_matched")
    bc = date_bucket(current.get("submitted_at_iso"))
    bl = date_bucket(legacy_matched.get("arbitration_date_iso") or legacy_matched.get("arbitration_date_source_iso"))
    if bc is not None and bl is not None and abs(bc - bl) <= 1:
        score += CONF_DATE_CLOSE
        evidence.append("date_close")
    return score, evidence
