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
from services.aliases import clean_and_normalize, is_skill_match, is_level_fit
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


# ⭐ ĐỌC TẬP TEST TỪ FILE test_cases.json (đặt cùng thư mục)
def load_test_cases(path="test_cases_labeled.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

TEST_CASES = load_test_cases()




def course_matches_gap(course, search_gap):
    """Khóa khớp gap ở CẤP KHÓA: có skill khớp + đúng level đang thiếu."""
    c_lvl = course.get("level", 1)
    for skill in course.get("target_skills", []):
        cs = clean_and_normalize(skill)
        for g, missing in search_gap.items():
            if is_skill_match(g, cs) and is_level_fit(c_lvl, missing):
                return True
    return False

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

        # Candidate pool (toàn bộ khóa qua DFS)
        candidates = [c for c in dfs_tree_search(state.GLOBAL_COURSE_TREE, search_gap) if isinstance(c, dict)]

        # Pool khớp gap ở CẤP KHÓA (skill+level)
        pool = [c for c in candidates if course_matches_gap(c, search_gap)]

        # Hệ thống gợi ý CÓ guardrail (tính TRƯỚC để biết khóa nào recommended)
        ranked = rank_courses_with_llm(candidates, search_gap, top_k=3)
        regular = ranked.get("regular_courses", [])
        rec_ids = [c.get("course_id") or c.get("id") for c in regular]
        system_runs[tid] = rec_ids
        rec_id_set = set(rec_ids)

        # KHÔNG guardrail: khóa đầu mỗi mốc blueprint
        blueprint = group_courses_by_gap(candidates, search_gap)
        ng = [courses[0].get("course_id") or courses[0].get("id")
              for step, courses in blueprint.items() if courses]
        system_runs_noguard[tid] = ng

        # ===== TẬP GÁN NHÃN = (A) khóa GỢI Ý + (B) mẫu ngẫu nhiên từ pool =====
        SAMPLE_N = 12
        pool_by_id = {(c.get("course_id") or c.get("id")): c for c in pool}
        label_set = {}
        for c in regular:
            cid = c.get("course_id") or c.get("id")
            if cid:
                label_set[cid] = (c, "recommended")
        import random
        rng = random.Random(42)
        rest = [cid for cid in pool_by_id if cid not in rec_id_set]
        rng.shuffle(rest)
        for cid in rest[:SAMPLE_N]:
            label_set[cid] = (pool_by_id[cid], "sample")

        gt_template[tid] = {
            "_gap_can_hoc": [f"{k} (cần L{','.join(map(str, sorted(v)))})" for k, v in search_gap.items()],
            "_cv": case["cv_text"][:150],
            "_jd": case["jd_text"][:150],
            "_pool_size": len(pool),
            "courses": {}
        }
        for cid, (c, source) in label_set.items():
            gt_template[tid]["courses"][cid] = {
                "title": c.get("title", ""),
                "level": c.get("level", ""),
                "skills": c.get("target_skills", [])[:8],
                "_source": source,
                "label": ""
            }

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