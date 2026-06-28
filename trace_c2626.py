"""
trace_c2626.py — Khóa lệch THẬT (khớp gap rỗng) vào recommended qua đường nào?
=============================================================================
Tìm 1 task có khóa recommended khớp gap RỖNG, in xem nó ở regular hay combo,
và nếu regular thì nó được gán cho mốc nào (LLM trả hay fallback).
CHẠY: py trace_c2626.py --task task_005   (task có C2626)
"""
import json, argparse
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.course_ranker import group_courses_by_gap, find_combo_courses, rank_courses_with_llm
from services.aliases import is_skill_match, clean_and_normalize
import make_labeling_template as M

ap = argparse.ArgumentParser(); ap.add_argument("--task", default="task_005"); a=ap.parse_args()
flat = load_courses_from_sql(); state.GLOBAL_COURSE_TREE = build_course_tree(flat)
cases = {c["task_id"]: c for c in M.TEST_CASES}
case = cases[a.task]
jd = extract_skills_from_jd(case["jd_text"]); cv = extract_skills_from_cv(case["cv_text"])
gap_raw,_ = compute_skill_gap(cv, jd)
sg = M.build_search_gap(gap_raw); gaps=list(sg.keys())
print("TASK", a.task, "GAP:", gaps)
cand=[c for c in dfs_tree_search(state.GLOBAL_COURSE_TREE, sg) if isinstance(c,dict)]
def m(c): return [f"{g}<-{s}" for g in gaps for s in c.get("target_skills",[]) if is_skill_match(g,clean_and_normalize(s))]

bp = group_courses_by_gap(cand, sg)
bp_ids = {c["course_id"] for v in bp.values() for c in v}
combo = find_combo_courses(cand, sg)
combo_ids = {c.get("course_id") for c in combo}
ranked = rank_courses_with_llm(cand, sg, top_k=3)
reg = ranked.get("regular_courses", [])

print(f"\nRegular ({len(reg)} khóa):")
for c in reg:
    cid=c.get("course_id"); hit=m(c)
    where = "blueprint" if cid in bp_ids else ("combo" if cid in combo_ids else "❓NGOÀI CẢ HAI")
    flag = "OK" if hit else "❌LỆCH"
    print(f"  {flag} [{cid}] {c.get('title','')[:35]:35} | {where} | khớp:{hit if hit else 'RỖNG'} | reason:{c.get('reasoning','')[:40]}")