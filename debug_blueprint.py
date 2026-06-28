"""
debug_blueprint.py — In BLUEPRINT (trước LLM) + path_results (sau LLM) cho 1 task
=================================================================================
Phân biệt: mốc Terraform mất ở group_courses_by_gap (blueprint) hay ở LLM?
CHẠY: py debug_blueprint.py --task task_001
"""
import json, re, argparse
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.course_ranker import group_courses_by_gap, find_combo_courses
from services.aliases import clean_and_normalize

def build_search_gap(gap_raw):
    sg={}
    for sk,gi in gap_raw.items():
        lv=gi["missing_levels"]
        if gi["match_mode"]=="EXACT":
            sg[clean_and_normalize(gi.get("user_skill_name") or sk)]=lv
        else:
            bm=gi.get("user_best_match")
            if bm:
                m=re.match(r'([^\(]+)(?:\((.*)\))?',bm)
                if m:
                    sg[clean_and_normalize(m.group(1).strip())]=lv
                    if m.group(2):
                        for s in m.group(2).split(','): sg[clean_and_normalize(s.strip())]=lv
    return sg

ap=argparse.ArgumentParser(); ap.add_argument("--task",default="task_001"); a=ap.parse_args()
flat=load_courses_from_sql(); tree=build_course_tree(flat); state.GLOBAL_COURSE_TREE=tree
cases={c["task_id"]:c for c in json.load(open("test_cases_labeled.json",encoding="utf-8"))}
case=cases[a.task]
jd=extract_skills_from_jd(case["jd_text"]); cv=extract_skills_from_cv(case["cv_text"])
gap_raw,_=compute_skill_gap(cv,jd)
sg=build_search_gap(gap_raw)
print("GAP đem search:", sg)
cand=[c for c in dfs_tree_search(tree,sg) if isinstance(c,dict)]
print(f"Candidates: {len(cand)}")
bp=group_courses_by_gap(cand,sg)
print(f"\n=== BLUEPRINT ({len(bp)} mốc) — đây là thứ ĐƯA CHO LLM ===")
for step,courses in bp.items():
    print(f"  {step}: {[c['course_id'] for c in courses]}")
print("\n>> Nếu có mốc TERRAFORM ở đây mà kết quả cuối KHÔNG có -> LLM làm mất.")
print(">> Nếu KHÔNG có mốc TERRAFORM ở đây -> group_courses_by_gap/gap làm mất.")