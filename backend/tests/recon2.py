import sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import asyncio, json
from db import coll

async def main():
    # Current internal dup groups
    cur_dup_by_mig = {}
    async for g in coll('duplicate_links_current').find({}):
        gid = g.get('duplicate_link_group_id')
        migs = g.get('migration_ids')
        if isinstance(migs, str):
            try: migs = json.loads(migs)
            except Exception: migs = []
        for m in (migs or []):
            cur_dup_by_mig[m] = gid
    from collections import Counter
    cur_group_sizes = Counter(cur_dup_by_mig.values())
    print(f"Lovable duplicate group members total: {len(cur_dup_by_mig)} across {len(cur_group_sizes)} groups")
    print(f"  size distribution: {sorted(Counter(cur_group_sizes.values()).items())}")
    reduction_cur = sum((sz - 1) for sz in cur_group_sizes.values())
    print(f"  reduction (members - groups): {reduction_cur}")

    # Legacy internal dup groups
    leg_dup_by_rev = {}
    async for g in coll('historical_duplicate_links').find({}):
        rid = g.get('resource_id')
        gid = g.get('legacy_duplicate_group_id')
        if not rid or not gid: continue
        async for r in coll('historical_arbitrations').find({'model_url_resource_id': rid}, {'legacy_review_id':1,'_id':0}):
            leg_dup_by_rev[r['legacy_review_id']] = gid
    leg_group_sizes = Counter(leg_dup_by_rev.values())
    print(f"\nLegacy duplicate group members total: {len(leg_dup_by_rev)} across {len(leg_group_sizes)} groups")
    print(f"  size distribution: {sorted(Counter(leg_group_sizes.values()).items())}")
    reduction_leg = sum((sz - 1) for sz in leg_group_sizes.values())
    print(f"  reduction (members - groups): {reduction_leg}")

    # Raw hour totals
    tot_cur_h = 0.0
    n_cur_h = 0
    async for r in coll('records_current').find({}, {'work_hours':1,'_id':0}):
        try:
            v = float(r.get('work_hours') or 0)
            tot_cur_h += v
            if v > 0: n_cur_h += 1
        except Exception:
            pass
    tot_leg_h = 0.0
    n_leg_h = 0
    async for r in coll('historical_arbitrations').find({}, {'total_arbitration_hours_raw':1,'total_arbitration_hours':1,'_id':0}):
        try:
            v = float(r.get('total_arbitration_hours_raw') or r.get('total_arbitration_hours') or 0)
            tot_leg_h += v
            if v > 0: n_leg_h += 1
        except Exception:
            pass
    print(f"\nRaw current hours = {tot_cur_h:.1f} over {n_cur_h} rows")
    print(f"Raw legacy hours  = {tot_leg_h:.1f} over {n_leg_h} rows")
    print(f"Raw combined naïve sum = {tot_cur_h + tot_leg_h:.1f}")

    # Also confirm the current 45,077.5 origin
asyncio.run(main())
