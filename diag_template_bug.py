"""
diag_template_bug.py — Tìm GỐC RỄ vì sao template còn khóa không khớp gap
=========================================================================
Kiểm 3 thứ trên CHÍNH file + DB của bạn:
 1) make_labeling_template.py trên đĩa CÓ gọi course_matches_gap không?
 2) search_gap thực tế của 1 task có chứa key "rác" không (build_search_gap)?
 3) Pool sau lọc mỗi task lớn cỡ nào? (nếu ~trăm/task -> lọc KHÔNG chạy)
CHẠY: py diag_template_bug.py
"""
import inspect, json, re
import make_labeling_template as M   # import chính file trên đĩa bạn
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.aliases import is_skill_match, clean_and_normalize

# 1) File trên đĩa có hàm lọc + có DÙNG nó không?
src = inspect.getsource(M)
has_func = "def course_matches_gap" in src
uses_func = "course_matches_gap(c, search_gap)" in src or "if course_matches_gap" in src
print("="*70)
print(f"1) make_labeling_template trên ĐĨA có hàm course_matches_gap : {has_func}")
print(f"   ...và có DÙNG nó để lọc pool                            : {uses_func}")
if not (has_func and uses_func):
    print("   🚨 FILE TRÊN ĐĨA LÀ BẢN CŨ / chưa dán đúng -> đó là nguyên nhân.")
    print("   -> Dán đè bản mới rồi chạy lại. Khỏi cần đọc tiếp.")

# 2) search_gap thật của task_001 (xem có key rác không)
flat = load_courses_from_sql(); state.GLOBAL_COURSE_TREE = build_course_tree(flat)
cases = {c["task_id"]: c for c in M.TEST_CASES}
case = cases.get("task_001") or list(cases.values())[0]
jd = extract_skills_from_jd(case["jd_text"]); cv = extract_skills_from_cv(case["cv_text"])
gap_raw, _ = compute_skill_gap(cv, jd)
search_gap = M.build_search_gap(gap_raw)
print("\n2) search_gap THẬT của", case["task_id"], ":")
for k, v in search_gap.items():
    print(f"     '{k}'  (level {v})")
print("   >> Nếu có key lạ (vd 'automation','scripting','devops') -> build_search_gap bung gap quá rộng.")

# 3) Pool trước/sau lọc
cand = [c for c in dfs_tree_search(state.GLOBAL_COURSE_TREE, search_gap) if isinstance(c, dict)]
if has_func:
    pool = [c for c in cand if M.course_matches_gap(c, search_gap)]
else:
    pool = cand
print(f"\n3) Pool task_001: candidates={len(cand)} -> sau lọc={len(pool)}")
# trong pool, bao nhiêu khóa KHÔNG có skill khớp tên gap hiển thị
disp_gaps = list(search_gap.keys())
nomatch = 0
for c in pool:
    if not any(is_skill_match(g, clean_and_normalize(s)) for g in disp_gaps for s in c.get("target_skills",[])):
        nomatch += 1
print(f"   Trong pool, khóa KHÔNG khớp gap nào: {nomatch}/{len(pool)}")
if nomatch > 0 and has_func:
    print("   🚨 Lọc CÓ chạy nhưng vẫn lọt -> build_search_gap chứa key match qua alias rộng.")
    print("   -> In ví dụ 3 khóa lọt:")
    cnt=0
    for c in pool:
        hit=[(g,s) for g in disp_gaps for s in c.get("target_skills",[]) if is_skill_match(g,clean_and_normalize(s))]
        if not hit:
            print(f"      [{c.get('course_id')}] {c.get('title','')[:40]} skills={c.get('target_skills',[])[:5]}")
            cnt+=1
            if cnt>=3: break