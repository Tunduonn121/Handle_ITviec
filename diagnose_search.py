"""
diagnose_search.py — CHẨN ĐOÁN từng tầng: DB -> cây -> search -> ranker
=======================================================================
Trả lời: khóa CI/CD, Terraform có trong DB không? Có vào cây không?
Search có trả về không? Ranker có giữ không? Tầng nào làm mất khóa.
CHẠY: py diagnose_search.py
"""
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.tree_searcher import dfs_tree_search
from services.course_ranker import group_courses_by_gap
from services.aliases import clean_and_normalize, is_skill_match, is_level_fit

flat = load_courses_from_sql()
print(f"📦 Tổng khóa trong DB: {len(flat)}")

# ===== TẦNG 1: DB có khóa dạy ci/cd, terraform, linux không? =====
print("\n" + "="*70)
print("TẦNG 1: ĐẾM KHÓA DB chứa skill (cấp khóa, is_skill_match)")
print("="*70)
for gap in ["ci/cd", "terraform", "linux"]:
    hits = []
    for c in flat:
        for s in c["target_skills"]:
            if is_skill_match(gap, clean_and_normalize(s)):
                hits.append((c["course_id"], c["title"][:40], c["level"], s))
                break
    print(f"\n🔍 '{gap}': {len(hits)} khóa trong DB")
    for cid, title, lvl, s in hits[:6]:
        print(f"   [{cid}] L{lvl} {title} (khớp qua '{s}')")

# ===== TẦNG 2: các khóa đó có vào CÂY không (cùng category/sub)? =====
print("\n" + "="*70)
print("TẦNG 2: build cây + kiểm khóa ci/cd có nằm trong cây không")
print("="*70)
tree = build_course_tree(flat)
state.GLOBAL_COURSE_TREE = tree
total_in_tree = sum(len(sub["_courses"]) for cat in tree.values() for sub in cat["_subs"].values())
print(f"Tổng khóa trong cây: {total_in_tree}")

# ===== TẦNG 3: search trả về gì cho gap chỉ có terraform =====
print("\n" + "="*70)
print("TẦNG 3: search riêng từng skill")
print("="*70)
for gap_skill in ["ci/cd", "terraform", "linux"]:
    search_gap = {gap_skill: [1,2,3]}  # mọi level
    cand = [c for c in dfs_tree_search(tree, search_gap) if isinstance(c, dict)]
    # lọc cấp khóa
    real = [c for c in cand if any(is_skill_match(gap_skill, clean_and_normalize(s))
                                    for s in c["target_skills"])]
    print(f"\n'{gap_skill}': search trả {len(cand)} khóa, trong đó {len(real)} khóa THẬT khớp cấp khóa")
    # ranker giữ bao nhiêu
    bp = group_courses_by_gap(cand, search_gap)
    n_bp = sum(len(v) for v in bp.values())
    print(f"   -> group_courses_by_gap giữ: {n_bp} khóa trong {len(bp)} mốc")
    for step, courses in list(bp.items())[:3]:
        print(f"      [{step}]: {[c.get('course_id') for c in courses]}")


   