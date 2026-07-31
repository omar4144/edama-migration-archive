"""Executive Scene — the new landing surface for admin users.

Every headline number here is designed to be clickable from the frontend,
opening a filtered view of the underlying data (models hub, cohort, org, etc.).
"""
from fastapi import APIRouter, Depends

from auth import require_role
from db import coll

router = APIRouter(prefix="/exec", tags=["exec"])


@router.get("/scene")
async def executive_scene(user: dict = Depends(require_role("admin"))):
    # ---- Totals across the unified layer ----
    async def _cnt(name, q=None):
        return await coll(name).count_documents(q or {})

    orgs_total = await _cnt("organizations_current")
    people_evaluators = await _cnt("people", {"role": "evaluator"})
    people_consultants = await _cnt("people", {"role": "consultant"})

    # Union with historical names
    hist_evals = set(await coll("historical_arbitrations").distinct("evaluator_name") or [])
    hist_evals.discard(None); hist_evals.discard("")
    hist_cons = set(await coll("historical_activities").distinct("consultant_name") or [])
    hist_cons.discard(None); hist_cons.discard("")

    current_eval_names = set(p["person_name"] for p in await coll("people").find(
        {"role": "evaluator"}, {"_id": 0, "person_name": 1}).to_list(50) if p.get("person_name"))
    current_cons_names = set(p["person_name"] for p in await coll("people").find(
        {"role": "consultant"}, {"_id": 0, "person_name": 1}).to_list(50) if p.get("person_name"))

    evaluators_unified = len(current_eval_names | hist_evals)
    consultants_unified = len(current_cons_names | hist_cons)

    models_total = await _cnt("model_definitions")
    records_total = await _cnt("records_current")
    hist_arb_total = await _cnt("historical_arbitrations")

    accepted = await _cnt("records_current", {"evaluation": "مقبول"})
    needs_dev = await _cnt("records_current", {"evaluation": "يحتاج لتطوير"})
    incomplete = await _cnt("records_current", {"evaluation": "غير مكتمل"})

    # Open legacy arbitration = arbitration_result_raw not in decided set
    open_legacy = await coll("historical_arbitrations").count_documents(
        {"arbitration_result_raw": {"$in": [None, "", "غير مكتمل"]}})

    hours_current = 0.0
    agg = await coll("records_current").aggregate(
        [{"$group": {"_id": None, "s": {"$sum": "$work_hours"}}}]).to_list(1)
    if agg: hours_current = float(agg[0]["s"] or 0)

    # Legacy hours (raw string in total_arbitration_hours_raw)
    hours_legacy = 0.0
    async for r in coll("historical_arbitrations").find(
        {"total_arbitration_hours_raw": {"$ne": None}},
        {"total_arbitration_hours_raw": 1, "_id": 0}):
        try:
            hours_legacy += float(r["total_arbitration_hours_raw"])
        except (ValueError, TypeError):
            pass

    # ---- Cohorts strip ----
    cohorts = []
    for c in ["1", "2", "3", "4"]:
        c_orgs_leg = await coll("historical_organizations").count_documents({"cohort": c})
        c_arbs = await coll("historical_arbitrations").count_documents({"cohort": c})
        c_acts = await coll("historical_activities").count_documents({"cohort": c})
        # legacy evaluator/consultant unique per cohort
        c_evals = len({e for e in (await coll("historical_arbitrations").distinct(
            "evaluator_name", {"cohort": c}) or []) if e})
        c_cons = len({e for e in (await coll("historical_activities").distinct(
            "consultant_name", {"cohort": c}) or []) if e})
        cohorts.append({
            "cohort": c,
            "organizations": c_orgs_leg,
            "evaluators": c_evals,
            "consultants": c_cons,
            "activities": c_acts,
            "arbitrations": c_arbs,
        })

    # ---- Attention items (real, data-driven) ----
    attention = []
    if incomplete:
        attention.append({
            "severity": "HIGH",
            "message": f"{incomplete} نموذج بحالة «غير مكتمل» في السجلات الحالية",
            "target": "/admin/models-hub?evaluation=غير مكتمل",
        })
    if needs_dev:
        attention.append({
            "severity": "MEDIUM",
            "message": f"{needs_dev} نموذج يحتاج لتطوير — بانتظار مستشار/محكم",
            "target": "/admin/models-hub?evaluation=يحتاج لتطوير",
        })
    if open_legacy:
        attention.append({
            "severity": "LOW",
            "message": f"{open_legacy} سجل تحكيم تاريخي بدون قرار موثّق",
            "target": "/admin/models-hub?source=legacy&evaluation=غير مكتمل",
        })
    pending_maps = await coll("mappings").count_documents({"status": "pending"})
    if pending_maps:
        attention.append({
            "severity": "MEDIUM",
            "message": f"{pending_maps} مطابقة بحاجة قرار في قائمة المراجعة",
            "target": "/admin/data/mappings",
        })
    # Records without a working URL (url_check != PASS)
    no_url = await coll("records_current").count_documents(
        {"$or": [{"model_url": None}, {"model_url": ""}]})
    if no_url:
        attention.append({
            "severity": "LOW",
            "message": f"{no_url} سجل حالي بدون رابط نموذج",
            "target": "/admin/models-hub?no_url=true",
        })

    return {
        "totals": {
            "cohorts": 4,
            "organizations": orgs_total,
            "evaluators": evaluators_unified,
            "evaluators_current": people_evaluators,
            "consultants": consultants_unified,
            "consultants_current": people_consultants,
            "models_defined": models_total,
            "records_current": records_total,
            "arbitrations_legacy": hist_arb_total,
            "accepted": accepted,
            "needs_dev": needs_dev,
            "incomplete": incomplete,
            "open_legacy": open_legacy,
            "hours_current": round(hours_current, 1),
            "hours_legacy": round(hours_legacy, 1),
            "hours_total": round(hours_current + hours_legacy, 1),
        },
        "cohorts": cohorts,
        "attention": attention,
    }
