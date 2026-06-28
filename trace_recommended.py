"""
trace_recommended.py — Truy vết: khóa 'recommended' lệch gap lọt qua đâu?
========================================================================
Với 1 task, in: blueprint (group_courses_by_gap) + combo (find_combo_courses)
+ regular_courses cuối, đánh dấu khóa nào KHÔNG khớp gap để thấy nguồn.
CHẠY: py trace_recommended.py --task task_001
"""
import json, re, argparse
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.course_ranker import group_courses_by_gap, find_combo_courses, rank_courses_with_llm
from services.aliases import is_skill_match, clean_and_normalize
import make_labeling_template as M

ap = argparse.ArgumentParser(); ap.add_argument("--task", default="task_001"); a = ap.parse_args()
flat = load_courses_from_sql(); state.GLOBAL_COURSE_TREE = build_course_tree(flat)
cases = {c["task_id"]: c for c in M.TEST_CASES}
case = cases[a.task]
jd = extract_skills_from_jd(case["jd_text"]); cv = extract_skills_from_cv(case["cv_text"])
gap_raw, _ = compute_skill_gap(cv, jd)
search_gap = M.build_search_gap(gap_raw)
gaps = list(search_gap.keys())
print("GAP:", gaps)

cand = [c for c in dfs_tree_search(state.GLOBAL_COURSE_TREE, search_gap) if isinstance(c, dict)]

def matches(c):
    return [f"{g}<-{s}" for g in gaps for s in c.get("target_skills",[])
            if is_skill_match(g, clean_and_normalize(s))]

combo = find_combo_courses(cand, search_gap)
print(f"\n--- COMBO ({len(combo)} khóa) — find_combo_courses ---")
for c in combo:
    m = matches(c)
    print(f"  {'OK' if m else '❌LỆCH'} [{c.get('course_id')}] {c.get('title','')[:38]} | {m if m else 'KHÔNG KHỚP'}")

ranked = rank_courses_with_llm(cand, search_gap, top_k=3)
print(f"\n--- REGULAR ({len(ranked.get('regular_courses',[]))} khóa) — sau LLM+guardrail ---")
for c in ranked.get("regular_courses", []):
    m = matches(c)
    print(f"  {'OK' if m else '❌LỆCH'} [{c.get('course_id')}] {c.get('title','')[:38]} | {m if m else 'KHÔNG KHỚP'}")

print(f"\n--- COMBO_COURSES trong kết quả ({len(ranked.get('combo_courses',[]))}) ---")
for c in ranked.get("combo_courses", []):
    m = matches(c)
    print(f"  {'OK' if m else '❌LỆCH'} [{c.get('course_id')}] {c.get('title','')[:38]} | {m if m else 'KHÔNG KHỚP'}")
print("\n>> Khóa ❌LỆCH ở COMBO -> find_combo_courses match lỏng.")
print(">> Khóa ❌LỆCH ở REGULAR -> lọt qua group_courses_by_gap/LLM.")