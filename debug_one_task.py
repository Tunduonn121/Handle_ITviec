"""
debug_one_task.py — SOI 1 task để biết vì sao khóa bị kéo vào (gap rộng? matching lỏng?)
=========================================================================================
CHẠY: py debug_one_task.py --task task_001
Cần DB sạch + test_cases_labeled.json.
"""
import json, re, argparse
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.aliases import clean_and_normalize, is_skill_match

def build_search_gap(gap_raw):
    sg = {}
    for sk, gi in gap_raw.items():
        lv = gi["missing_levels"]
        if gi["match_mode"] == "EXACT":
            sg[clean_and_normalize(gi.get("user_skill_name") or sk)] = lv
        else:
            bm = gi.get("user_best_match")
            if bm:
                m = re.match(r'([^\(]+)(?:\((.*)\))?', bm)
                if m:
                    sg[clean_and_normalize(m.group(1).strip())] = lv
                    if m.group(2):
                        for s in m.group(2).split(','):
                            sg[clean_and_normalize(s.strip())] = lv
    return sg

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--task", default="task_001")
    args = ap.parse_args()

    flat = load_courses_from_sql()
    state.GLOBAL_COURSE_TREE = build_course_tree(flat)
    cases = {c["task_id"]: c for c in json.load(open("test_cases_labeled.json", encoding="utf-8"))}
    case = cases[args.task]

    print("="*80); print(f"TASK {args.task}  (domain={case.get('domain')}, gap_type={case.get('gap_type')})")
    print("="*80)
    print("JD:", case["jd_text"]); print("CV:", case["cv_text"])

    jd = extract_skills_from_jd(case["jd_text"]); cv = extract_skills_from_cv(case["cv_text"])
    print("\n--- JD skills LLM trích ---"); print(json.dumps(jd, ensure_ascii=False, indent=1))
    print("\n--- CV skills LLM trích ---"); print(json.dumps(cv, ensure_ascii=False, indent=1))

    gap_raw, matched = compute_skill_gap(cv, jd)
    search_gap = build_search_gap(gap_raw)
    print("\n--- GAP (đã chuẩn hóa, đem đi search) ---"); print(list(search_gap.keys()))

    cand = [c for c in dfs_tree_search(state.GLOBAL_COURSE_TREE, search_gap) if isinstance(c, dict)]
    print(f"\n--- {len(cand)} khóa ứng viên, kèm SKILL NÀO khớp gap ---")
    for c in cand[:30]:
        hits = []
        for g in search_gap:
            for s in c.get("target_skills", []):
                if is_skill_match(g, clean_and_normalize(s)):
                    hits.append(f"{g}<-{s}"); break
        print(f"  [{c.get('course_id')}] {c.get('title','')[:45]:45} | khớp: {hits}")

if __name__ == "__main__":
    main()