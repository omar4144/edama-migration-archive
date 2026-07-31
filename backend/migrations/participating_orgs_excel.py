"""
Build a single Excel workbook for human review of the 175 Participating Orgs audit.
READ-ONLY with respect to the database. Only reads existing CSV/MD reports under /app/memory/
and writes /app/memory/PARTICIPATING_ORGANIZATIONS_REVIEW.xlsx.

Sheets (Arabic RTL headers):
  1. الملخص
  2. عناصر الـ175
  3. مجموعات التطابق
  4. المشاركات حسب الدفعة
  5. الجمعيات متعددة الدفعات
  6. جودة سجلات Lovable
  7. الحالات التي تحتاج قرارًا بشريًا
"""
import csv
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

MEMORY = Path("/app/memory")
OUT = MEMORY / "PARTICIPATING_ORGANIZATIONS_REVIEW.xlsx"

HEADER_FILL = PatternFill("solid", fgColor="0F3D3E")   # navy
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Tahoma", size=11)
BODY_FONT = Font(name="Tahoma", size=10)
WARN_FILL = PatternFill("solid", fgColor="FFF2CC")     # soft yellow
HUMAN_FILL = PatternFill("solid", fgColor="FCE4D6")    # soft orange
GOOD_FILL = PatternFill("solid", fgColor="E2EFDA")     # soft green


def _read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []
    return headers, rows


def _write_sheet(ws, headers, rows, *, row_fill=None, freeze=True):
    ws.sheet_view.rightToLeft = True
    ws.append(headers)
    for col_idx, _ in enumerate(headers, start=1):
        c = ws.cell(row=1, column=col_idx)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r_idx, row in enumerate(rows, start=2):
        for c_idx, h in enumerate(headers, start=1):
            v = row.get(h, "") if isinstance(row, dict) else row[c_idx - 1]
            cell = ws.cell(row=r_idx, column=c_idx, value=v)
            cell.font = BODY_FONT
            cell.alignment = Alignment(horizontal="right", vertical="top", wrap_text=True)
        if row_fill:
            fill = row_fill(row) if callable(row_fill) else row_fill
            if fill:
                for c_idx in range(1, len(headers) + 1):
                    ws.cell(row=r_idx, column=c_idx).fill = fill
    # column widths
    for c_idx, h in enumerate(headers, start=1):
        max_len = min(60, max(12, len(str(h)) + 2))
        # scan first 200 rows
        sample = rows[:200]
        for row in sample:
            v = row.get(h, "") if isinstance(row, dict) else row[c_idx - 1]
            L = len(str(v).splitlines()[0]) if v else 0
            if L > max_len:
                max_len = min(60, L + 2)
        ws.column_dimensions[get_column_letter(c_idx)].width = max_len
    ws.row_dimensions[1].height = 32
    if freeze:
        ws.freeze_panes = "A2"


def build_summary(wb, headers175, rows175, groups_rows, part_rows):
    ws = wb.create_sheet("الملخص", 0)
    ws.sheet_view.rightToLeft = True

    lines = [
        ("تدقيق سجل الجمعيات المشاركة — لماذا 175؟", True),
        ("تدقيق قراءة فقط. لا تعديل ولا دمج ولا حذف.", False),
        ("", False),
        ("1) معادلة الرقم 175", True),
        ("عدد صفوف جهات Legacy الخام: 118", False),
        ("عدد صفوف جهات Lovable الخام: 57", False),
        ("175 = 57 + 118 (جمع مباشر لكلا المصدرين، بدون تطبيق crosswalk)", False),
        ("", False),
        ("2) الأرقام الثلاثة المنفصلة", True),
        ("صفوف المصادر الخام للجهات: 175", False),
        ("مشاركات (organization × cohort): 175", False),
        ("الجمعيات الفريدة عبر البرنامج: 118 (بعد EXACT+PROBABLE) — 119 (بـEXACT فقط)", False),
        ("", False),
        ("3) توزيع Crosswalk", True),
        ("EXACT_NORMALIZED: 56", False),
        ("PROBABLE_NAME_VARIANT: 1", False),
        ("LEGACY_ONLY: 61", False),
        ("LOVABLE_ONLY: 0", False),
        ("", False),
        ("4) تعدد الدفعات", True),
        ("جمعيات ظهرت في أكثر من دفعة: 0", False),
        ("جمعيات بدون دفعة معروفة: 0", False),
        ("", False),
        ("5) جودة Lovable", True),
        ("كل الـ2,565 صف Lovable يحمل evaluation='مقبول' بلا استثناء.", False),
        ("يجب معاملتها كـ LINK_EXISTS_CONTENT_NOT_VERIFIED حتى يتم فحص محتوى الملف.", False),
        ("", False),
        ("6) Family Key", True),
        ("عدد الرحلات بالمفتاح الحالي org × model_definition: 3,521", False),
        ("عدد الرحلات بالمفتاح المقترح org × cohort × model_definition: 3,521 (لا تغيّر)", False),
        ("لا حاجة لتغيير المفتاح حاليًا. أبقِ حقل cohort_participation_id احتياطيًا.", False),
        ("", False),
        ("7) عدّادات هذا الملف", True),
        (f"عناصر الـ175: {len(rows175)}", False),
        (f"مجموعات التطابق: {len(groups_rows)}", False),
        (f"صفوف المشاركات حسب الدفعة: {len(part_rows)}", False),
        ("", False),
        ("8) تأكيد عدم لمس البيانات", True),
        ("لا تعديل على source_records أو canonical_submissions أو organizations_current.", False),
        ("لا تنفيذ لأي Bulk confirm.", False),
        ("فقط قراءة + كتابة إلى /app/memory/.", False),
    ]

    for i, (txt, is_h) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=txt)
        if is_h:
            c.font = Font(bold=True, name="Tahoma", size=13, color="0F3D3E")
            c.fill = PatternFill("solid", fgColor="E7F3F2")
        else:
            c.font = Font(name="Tahoma", size=11)
        c.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
    ws.column_dimensions["A"].width = 110


def build_multi_cohort(wb, part_rows):
    ws = wb.create_sheet("الجمعيات متعددة الدفعات")
    # group by proposed_canonical_org_id
    by_org = defaultdict(list)
    for r in part_rows:
        by_org[r.get("proposed_canonical_org_id", "")].append(r)

    headers = [
        "proposed_canonical_org_id",
        "canonical_org_name",
        "cohorts_present",
        "cohort_count",
        "participation_ids",
        "sources",
        "requires_review",
        "possible_previous_participation",
        "possible_next_participation",
    ]
    rows = []
    for oid, group in by_org.items():
        cohorts = sorted({str(g.get("cohort", "")).strip() for g in group if g.get("cohort")})
        if len(cohorts) < 2:
            continue
        rows.append({
            "proposed_canonical_org_id": oid,
            "canonical_org_name": group[0].get("canonical_org_name", ""),
            "cohorts_present": " | ".join(cohorts),
            "cohort_count": len(cohorts),
            "participation_ids": " | ".join(g.get("participation_id", "") for g in group),
            "sources": " | ".join(sorted({g.get("source", "") for g in group})),
            "requires_review": " | ".join(g.get("requires_review", "") for g in group),
            "possible_previous_participation": " | ".join(g.get("possible_previous_participation", "") for g in group if g.get("possible_previous_participation")),
            "possible_next_participation": " | ".join(g.get("possible_next_participation", "") for g in group if g.get("possible_next_participation")),
        })
    if not rows:
        # Add a note row so the sheet isn't empty
        _write_sheet(ws, headers, [{"proposed_canonical_org_id": "—", "canonical_org_name": "لا توجد جمعيات متعددة الدفعات في البيانات الحالية", "cohorts_present": "", "cohort_count": 0, "participation_ids": "", "sources": "", "requires_review": "", "possible_previous_participation": "", "possible_next_participation": ""}], row_fill=GOOD_FILL)
    else:
        _write_sheet(ws, headers, rows, row_fill=WARN_FILL)


def build_lovable_quality(wb, rows175):
    ws = wb.create_sheet("جودة سجلات Lovable")
    headers = [
        "lovable_org_id",
        "display_name",
        "cohort",
        "lovable_model_rows",
        "current_links_count",
        "canonical_version_count",
        "model_family_count",
        "roster_status",
        "consultant_names",
        "evaluator_names",
        "notes",
    ]
    rows = []
    for r in rows175:
        lov_id = r.get("lovable_org_id", "").strip()
        if not lov_id:
            continue
        note = "LINK_EXISTS_CONTENT_NOT_VERIFIED — كل «مقبول» يحتاج فحص محتوى الملف."
        rows.append({
            "lovable_org_id": lov_id,
            "display_name": r.get("display_name", ""),
            "cohort": r.get("cohorts", ""),
            "lovable_model_rows": r.get("lovable_model_rows", ""),
            "current_links_count": r.get("current_links_count", ""),
            "canonical_version_count": r.get("canonical_version_count", ""),
            "model_family_count": r.get("model_family_count", ""),
            "roster_status": r.get("roster_status", ""),
            "consultant_names": r.get("consultant_names", ""),
            "evaluator_names": r.get("evaluator_names", ""),
            "notes": note,
        })
    _write_sheet(ws, headers, rows, row_fill=WARN_FILL)


def build_human_decisions(wb, rows175, groups_rows, part_rows):
    ws = wb.create_sheet("قرارات بشرية مطلوبة")
    headers = [
        "case_type",
        "candidate_or_group_id",
        "display_name",
        "match_status",
        "match_reason",
        "confidence",
        "why_needs_human",
        "recommended_action",
        "linked_records",
    ]
    rows = []

    # 1) PROBABLE_NAME_VARIANT groups
    for g in groups_rows:
        if g.get("match_status") == "PROBABLE_NAME_VARIANT" or (str(g.get("requires_human_review", "")).lower() == "true"):
            rows.append({
                "case_type": "زوج مطابقة مقترح — يحتاج تأكيد",
                "candidate_or_group_id": g.get("proposed_canonical_org_id", ""),
                "display_name": g.get("member_names", ""),
                "match_status": g.get("match_status", ""),
                "match_reason": g.get("match_reason", ""),
                "confidence": g.get("confidence", ""),
                "why_needs_human": g.get("blocking_issue", "") or "PROBABLE_NAME_VARIANT — تطابق محتمل غير مؤكد",
                "recommended_action": "تأكيد الدمج أو الفصل بقرار بشري",
                "linked_records": g.get("member_candidate_ids", ""),
            })

    # 2) LEGACY_ONLY (no Lovable match)
    for r in rows175:
        if r.get("organization_crosswalk_status") in ("LEGACY_ONLY", "NO_MATCH_LEGACY_ONLY"):
            rows.append({
                "case_type": "Legacy بدون مطابق Lovable",
                "candidate_or_group_id": r.get("registry_candidate_id", ""),
                "display_name": r.get("display_name", ""),
                "match_status": r.get("organization_crosswalk_status", ""),
                "match_reason": "لا يوجد صف Lovable مطابق",
                "confidence": r.get("match_confidence", ""),
                "why_needs_human": "تأكيد ما إذا كانت الجمعية لم تعد نشطة أم تحتاج إنشاء ORG في Lovable",
                "recommended_action": "إبقاء كـ Legacy فقط، أو ربطها يدويًا بـ ORG لوفابل جديد",
                "linked_records": r.get("legacy_org_id", ""),
            })

    # 3) participations that flag review
    for p in part_rows:
        if str(p.get("requires_review", "")).lower() == "true":
            rows.append({
                "case_type": "مشاركة دفعة — تحتاج مراجعة",
                "candidate_or_group_id": p.get("participation_id", ""),
                "display_name": p.get("canonical_org_name", ""),
                "match_status": p.get("cohort_confidence", ""),
                "match_reason": p.get("participation_evidence", ""),
                "confidence": p.get("cohort_confidence", ""),
                "why_needs_human": "مشاركة دفعة غير مؤكدة أو تحتاج تأكيد",
                "recommended_action": "تحديد الدفعة الصحيحة يدويًا",
                "linked_records": p.get("source_record_ids", ""),
            })

    # 4) seed_did_not_apply_crosswalk_merge (EXACT that stayed as two candidates)
    for r in rows175:
        why = r.get("why_separate_candidate", "") or ""
        if "seed_did_not_apply_crosswalk_merge" in why:
            rows.append({
                "case_type": "زوج EXACT لم يُدمج في seed",
                "candidate_or_group_id": r.get("registry_candidate_id", ""),
                "display_name": r.get("display_name", ""),
                "match_status": r.get("organization_crosswalk_status", ""),
                "match_reason": r.get("match_method", ""),
                "confidence": r.get("match_confidence", ""),
                "why_needs_human": "الـcrosswalk يوصي بالدمج لكن الـseed لم يطبّقه — يحتاج قرار: دمج أم إبقاء كصفّين",
                "recommended_action": "الموافقة على تطبيق EXACT_NORMALIZED بالكامل أو تحديد استثناءات",
                "linked_records": f"{r.get('legacy_org_id','')} ↔ {r.get('lovable_org_id','')}",
            })

    _write_sheet(ws, headers, rows, row_fill=HUMAN_FILL)


def main():
    headers175, rows175 = _read_csv(MEMORY / "PARTICIPATING_ORGANIZATIONS_175_AUDIT.csv")
    groups_headers, groups_rows = _read_csv(MEMORY / "ORGANIZATION_MATCH_GROUPS.csv")
    part_headers, part_rows = _read_csv(MEMORY / "ORGANIZATION_COHORT_PARTICIPATIONS.csv")

    wb = Workbook()
    # remove default sheet
    default = wb.active
    wb.remove(default)

    # 1) Summary (added at index 0 inside build_summary)
    build_summary(wb, headers175, rows175, groups_rows, part_rows)

    # 2) 175 items
    ws2 = wb.create_sheet("عناصر الـ175")
    def _color175(row):
        st = (row.get("organization_crosswalk_status") or "").upper()
        if st in ("LEGACY_ONLY", "NO_MATCH_LEGACY_ONLY"):
            return HUMAN_FILL
        if st == "PROBABLE_NAME_VARIANT":
            return WARN_FILL
        if st == "EXACT_NORMALIZED":
            return GOOD_FILL
        return None
    _write_sheet(ws2, headers175, rows175, row_fill=_color175)

    # 3) match groups
    ws3 = wb.create_sheet("مجموعات التطابق")
    def _colorg(row):
        st = (row.get("match_status") or "").upper()
        if st == "EXACT_SAME_ORGANIZATION":
            return GOOD_FILL
        if st == "PROBABLE_NAME_VARIANT":
            return WARN_FILL
        if str(row.get("requires_human_review", "")).lower() == "true":
            return HUMAN_FILL
        return None
    _write_sheet(ws3, groups_headers, groups_rows, row_fill=_colorg)

    # 4) cohort participations
    ws4 = wb.create_sheet("المشاركات حسب الدفعة")
    def _colorp(row):
        if str(row.get("requires_review", "")).lower() == "true":
            return HUMAN_FILL
        conf = (row.get("cohort_confidence") or "").upper()
        if conf == "HIGH":
            return GOOD_FILL
        if conf in ("LOW", "UNKNOWN"):
            return WARN_FILL
        return None
    _write_sheet(ws4, part_headers, part_rows, row_fill=_colorp)

    # 5) multi-cohort
    build_multi_cohort(wb, part_rows)

    # 6) lovable quality
    build_lovable_quality(wb, rows175)

    # 7) human decisions
    build_human_decisions(wb, rows175, groups_rows, part_rows)

    wb.save(OUT)
    print(f"Wrote {OUT}")
    print(f"Sheets: {wb.sheetnames}")


if __name__ == "__main__":
    main()
