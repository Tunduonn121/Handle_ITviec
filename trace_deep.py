"""
trace_deep.py — Vì sao khóa lệch (vd C3094 Technical Support) vào recommended?
==============================================================================
In blueprint từng mốc + khóa LLM chọn + khóa fallback, đánh dấu khóa lệch gap.
Kiểm: khóa lệch có NẰM trong blueprint không (nếu có -> group_courses_by_gap sai;
nếu không -> LLM/parse đưa id lạ mà lọt qua chốt chặn).
CHẠY: py trace_deep.py --task task_001
"""
import json, re, argparse
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.course_ranker import group_courses_by_gap
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
bp = group_courses_by_gap(cand, search_gap)

def m(c): return [f"{g}<-{s}" for g in gaps for s in c.get("target_skills",[]) if is_skill_match(g, clean_and_normalize(s))]

print("\n=== BLUEPRINT từng mốc (khóa nào nằm trong) ===")
all_bp_ids = set()
for step, courses in bp.items():
    ids = [c["course_id"] for c in courses]
    all_bp_ids |= set(ids)
    print(f"  {step}: {ids}")
    # kiểm từng khóa blueprint có THẬT khớp mốc không
    skill_of_step = step.split(" (")[0].lower()
    for c in courses:
        hit = m(c)
        if not any(skill_of_step in h.split("<-")[0] for h in hit):
            print(f"     ⚠️ {c['course_id']} trong mốc '{skill_of_step}' nhưng khớp: {hit if hit else 'KHÔNG KHỚP GÌ'}")

# Có khóa lệch nổi tiếng nào trong blueprint không?
for bad in ["C3094","C1394","C2436","C2626"]:
    if bad in all_bp_ids:
        print(f"\n🚨 {bad} (khóa lệch) CÓ trong blueprint -> group_courses_by_gap đưa nhầm!")
    # tìm khóa trong cand
    cc = next((c for c in cand if c.get("course_id")==bad), None)
    if cc:
        print(f"   {bad} skills={cc.get('target_skills',[])[:6]} | khớp gap: {m(cc)}")