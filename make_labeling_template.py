"""
make_labeling_template.py — SINH KHUNG GÁN NHÃN + GHI LẠI KẾT QUẢ HỆ THỐNG
==========================================================================
Chạy hệ thống trên một tập test (CV, JD) và xuất ra 3 file:
  - ground_truth_TEMPLATE.json : khung để NGƯỜI gán nhãn (mặc định để trống "")
  - system_runs.json           : khóa hệ thống gợi ý CÓ guardrail E(c)
  - system_runs_noguard.json   : khóa LLM chọn KHÔNG qua guardrail (cho ablation)

Người chấm chỉ việc mở ground_truth_TEMPLATE.json, sửa "" thành 1 (relevant)
hoặc 0 (not relevant) cho từng khóa, rồi lưu thành ground_truth.json.

LƯU Ý: file này gọi pipeline thật (LLM + DB) nên cần chạy trong môi trường
đã cấu hình .env và SQL Server giống lúc chạy server.
"""
import json
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.course_ranker import rank_courses_with_llm, group_courses_by_gap
from services.aliases import clean_and_normalize
import re


def build_search_gap(gap_raw):
    """Tái dùng đúng logic chuẩn hóa gap như background_tasks."""
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


# ⭐ ĐIỀN TẬP TEST CỦA BẠN VÀO ĐÂY (30-50 cặp để số liệu có ý nghĩa)
TEST_CASES = [
    {
        "task_id": "task_001",
        "cv_text": "Tôi có 2 năm kinh nghiệm Java, Spring Boot và MySQL.",
        "jd_text": "Yêu cầu thành thạo Docker, Kubernetes và CI/CD. Biết Java là lợi thế."
    },
    # {"task_id": "task_002", "cv_text": "...", "jd_text": "..."},
    # ... thêm các cặp khác
]


def main():
    print("⏳ Nạp cây khóa học...")
    flat = load_courses_from_sql()
    state.GLOBAL_COURSE_TREE = build_course_tree(flat)

    gt_template = {}
    system_runs = {}
    system_runs_noguard = {}

    for case in TEST_CASES:
        tid = case["task_id"]
        print(f"\n🔎 Xử lý {tid} ...")
        jd = extract_skills_from_jd(case["jd_text"])
        cv = extract_skills_from_cv(case["cv_text"])
        gap_raw, _ = compute_skill_gap(cv, jd)
        if not gap_raw:
            print("   (Không có gap, bỏ qua)")
            continue
        search_gap = build_search_gap(gap_raw)

        # Candidate pool (toàn bộ khóa qua DFS) -> đây là tập NGƯỜI gán nhãn
        candidates = [c for c in dfs_tree_search(state.GLOBAL_COURSE_TREE, search_gap) if isinstance(c, dict)]

        # Khung gán nhãn: mọi khóa trong pool, để trống cho người điền
        gt_template[tid] = {}
        for c in candidates:
            cid = c.get("course_id") or c.get("id")
            if cid:
                gt_template[tid][cid] = ""   # NGƯỜI điền 1 hoặc 0

        # Hệ thống gợi ý CÓ guardrail
        ranked = rank_courses_with_llm(candidates, search_gap, top_k=3)
        regular = ranked.get("regular_courses", [])
        system_runs[tid] = [c.get("course_id") or c.get("id") for c in regular]

        # KHÔNG guardrail: lấy thẳng khóa LLM gợi ý từ blueprint (không lọc E(c)).
        # Ở đây xấp xỉ bằng: mọi khóa trong blueprint (LLM được chọn trong đó).
        blueprint = group_courses_by_gap(candidates, search_gap)
        ng = []
        for step, courses in blueprint.items():
            if courses:
                ng.append(courses[0].get("course_id") or courses[0].get("id"))
        system_runs_noguard[tid] = ng

    with open("ground_truth_TEMPLATE.json", "w", encoding="utf-8") as f:
        json.dump(gt_template, f, ensure_ascii=False, indent=2)
    with open("system_runs.json", "w", encoding="utf-8") as f:
        json.dump(system_runs, f, ensure_ascii=False, indent=2)
    with open("system_runs_noguard.json", "w", encoding="utf-8") as f:
        json.dump(system_runs_noguard, f, ensure_ascii=False, indent=2)

    print("\n✅ Đã xuất: ground_truth_TEMPLATE.json, system_runs.json, system_runs_noguard.json")
    print("👉 Mở ground_truth_TEMPLATE.json, điền 1/0 cho từng khóa, lưu thành ground_truth.json")


if __name__ == "__main__":
    main()