"""
benchmark_tokens.py — P2: PHÂN TÍCH TOKEN (kiểu RQ2 của LLMTreeRec)
====================================================================
Đo token gửi cho LLM dưới 3 mức, để TRUNG THỰC về nguồn giảm:
  (1) NAIVE        : nhồi TẤT CẢ khóa cho LLM tự chọn (baseline LLMTreeRec phê phán)
  (2) FILTER-ONLY  : quét phẳng + bộ lọc xác định (group_courses_by_gap, cap <=3/step)
  (3) TREE+FILTER  : cây thu hẹp trước + bộ lọc -> pipeline đầy đủ của bạn

Mục tiêu: cho thấy (2) là nguồn giảm token CHÍNH; (3) cây đóng góp thêm rất ít.
=> Ghi đúng vào luận văn: "giảm token chủ yếu do bộ lọc xác định, cây đóng vai trò tổ chức."

CHẠY: py benchmark_tokens.py   (cần DB sạch + test_cases.json ở thư mục gốc)
"""
import json
import re

import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.course_ranker import group_courses_by_gap
from services.aliases import clean_and_normalize

# --- Ước lượng token: ưu tiên tiktoken, không có thì ký tự/4 ---
try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text): return len(_enc.encode(text))
except Exception:
    def count_tokens(text): return max(1, len(text) // 4)

def course_to_text(c):
    """Mô phỏng text 1 khóa khi đưa vào prompt LLM (title + skills + desc rút gọn)."""
    skills = ", ".join(c.get("target_skills", []))
    desc = (c.get("description", "") or "")[:100]
    return f'ID:{c.get("course_id")} | {c.get("title","")} | Skills: {skills} | {desc}'

def build_search_gap(gap_raw):
    search_gap = {}
    for skill_key, gi in gap_raw.items():
        lvls = gi["missing_levels"]
        if gi["match_mode"] == "EXACT":
            name = gi.get("user_skill_name") or skill_key
            search_gap[clean_and_normalize(name)] = lvls
        else:
            bm = gi.get("user_best_match")
            if bm:
                m = re.match(r'([^\(]+)(?:\((.*)\))?', bm)
                if m:
                    search_gap[clean_and_normalize(m.group(1).strip())] = lvls
                    if m.group(2):
                        for sub in m.group(2).split(','):
                            search_gap[clean_and_normalize(sub.strip())] = lvls
    return search_gap

def tokens_of_blueprint(blueprint):
    """Token mà LLM ranker phải đọc = tổng text các khóa trong blueprint."""
    total = 0
    for step, courses in blueprint.items():
        total += count_tokens(step)
        for c in courses:
            total += count_tokens(course_to_text(c))
    return total

def main():
    print("⏳ Nạp cây từ DB...")
    flat = load_courses_from_sql()
    if not flat:
        print("❌ DB rỗng. Hãy chạy import + auto_categorize trước.")
        return
    state.GLOBAL_COURSE_TREE = build_course_tree(flat)
    all_courses = [c for cat in state.GLOBAL_COURSE_TREE.values()
                   for sub in cat["_subs"].values() for c in sub["_courses"]]
    N = len(all_courses)
    print(f"✅ Cây sẵn sàng. Tổng {N} khóa.\n")

    with open("test_cases.json", encoding="utf-8") as f:
        cases = json.load(f)

    sum_naive = sum_filter = sum_tree = 0
    n_ok = 0
    print(f"{'task':>10} | {'NAIVE':>10} | {'FILTER-ONLY':>12} | {'TREE+FILTER':>12}")
    print("-"*54)
    for case in cases:
        jd = extract_skills_from_jd(case["jd_text"])
        cv = extract_skills_from_cv(case["cv_text"])
        gap_raw, _ = compute_skill_gap(cv, jd)
        if not gap_raw:
            continue
        search_gap = build_search_gap(gap_raw)

        # (1) NAIVE: LLM đọc TẤT CẢ khóa
        naive = sum(count_tokens(course_to_text(c)) for c in all_courses)

        # (2) FILTER-ONLY: quét phẳng (toàn bộ khóa) -> bộ lọc cap<=3/step
        bp_flat = group_courses_by_gap(all_courses, search_gap)
        filter_only = tokens_of_blueprint(bp_flat)

        # (3) TREE+FILTER: cây thu hẹp -> bộ lọc
        cand = [c for c in dfs_tree_search(state.GLOBAL_COURSE_TREE, search_gap) if isinstance(c, dict)]
        bp_tree = group_courses_by_gap(cand, search_gap)
        tree_filter = tokens_of_blueprint(bp_tree)

        sum_naive += naive; sum_filter += filter_only; sum_tree += tree_filter; n_ok += 1
        print(f"{case['task_id']:>10} | {naive:>10,} | {filter_only:>12,} | {tree_filter:>12,}")

    if n_ok == 0:
        print("Không task nào có gap. Kiểm tra DB/test_cases.")
        return
    print("-"*54)
    print(f"{'TRUNG BÌNH':>10} | {sum_naive//n_ok:>10,} | {sum_filter//n_ok:>12,} | {sum_tree//n_ok:>12,}")
    print("\n📊 KẾT LUẬN (ghi vào luận văn):")
    print(f"  • Bộ lọc xác định giảm token: {(1-sum_filter/sum_naive)*100:.1f}% so với Naive (NGUỒN GIẢM CHÍNH).")
    print(f"  • Cây đóng góp thêm: {(1-sum_tree/sum_filter)*100:.1f}% so với chỉ-bộ-lọc "
          f"({'không đáng kể' if abs(1-sum_tree/sum_filter)<0.05 else 'có giảm thêm'}).")
    print("  => Trung thực: giảm token chủ yếu do BỘ LỌC, cây vai trò tổ chức.")

if __name__ == "__main__":
    main()