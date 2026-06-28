import json
import os
import re
from services.aliases import GLOBAL_ALIAS_MAP, is_skill_match, is_level_fit, clean_and_normalize

from core.config import ollama_client as client, MODEL_NAME

# =====================================================================
# KHỐI 3: TÌM KHÓA COMBO (ĐA KỸ NĂNG) — giữ nguyên
# =====================================================================
def find_combo_courses(candidate_courses, gap_dict):
    combo_courses = []
    gap_skills = set([skill.lower() for skill in gap_dict.keys()])

    for course in candidate_courses:
        c_skills_raw = [s.lower().replace("/", " ").replace("-", " ") for s in course.get("target_skills", [])]
        c_skills_normalized = set()
        for c_s in c_skills_raw:
            for k, v in GLOBAL_ALIAS_MAP.items():
                if is_skill_match(k, c_s) or is_skill_match(v, c_s):
                    c_skills_normalized.add(k)
            c_skills_normalized.add(c_s)

        overlap = gap_skills.intersection(c_skills_normalized)
        coverage_score = len(overlap)
        if coverage_score >= 2:
            lite_combo = course.copy()
            lite_combo["coverage_score"] = coverage_score
            lite_combo["covered_skills"] = list(overlap)
            lite_combo["relevance_score"] = min(98, 85 + (coverage_score * 5))
            skill_list_str = ", ".join([s.title() for s in overlap])
            lite_combo["reasoning"] = f"🎯 [KHÓA HỌC COMBO] -> Bao phủ {coverage_score} kỹ năng: {skill_list_str}."
            combo_courses.append(lite_combo)

    combo_courses.sort(key=lambda x: x["coverage_score"], reverse=True)
    return combo_courses[:3]

# =====================================================================
# KHỐI 4: NHÓM KHÓA THEO LỖ HỔNG (BLUEPRINT)
# SỬA Lỗi 3: dùng is_level_fit thay cho c_lvl == req_level (chặt quá),
# để khóa level thấp hơn vẫn được coi là bước đệm hợp lệ cho mốc đang xét.
# =====================================================================
def _relevance_score(course, gap_skill, gap_dict):
    """
    Điểm liên quan XÁC ĐỊNH (không LLM) để xếp hạng khóa trong 1 mốc.
    Ưu tiên: (1) tên skill trong TIÊU ĐỀ, (2) số skill gap khớp,
    (3) tỷ lệ skill gap / tổng skill (khóa chuyên). Cao hơn = liên quan hơn.
    """
    title = (course.get("title", "") or "").lower()
    c_skills = course.get("target_skills", [])
    gap_clean = clean_and_normalize(gap_skill)

    # (1) skill gap (hoặc alias của nó) xuất hiện trong TIÊU ĐỀ -> mạnh nhất
    term = GLOBAL_ALIAS_MAP.get(gap_skill.lower(), gap_skill.lower())
    in_title = 1 if (gap_clean in title or term.replace("/", " ").replace("-", " ") in title
                     or gap_skill.lower() in title) else 0

    # (2) số skill gap (toàn bộ gap_dict) mà khóa này khớp
    gap_hit = 0
    for g in gap_dict.keys():
        gn = clean_and_normalize(g)
        if any(is_skill_match(gn, clean_and_normalize(s)) for s in c_skills):
            gap_hit += 1

    # (3) tỷ lệ skill gap / tổng skill (khóa càng chuyên về gap càng cao)
    ratio = (gap_hit / len(c_skills)) if c_skills else 0

    return (in_title, gap_hit, ratio)

def group_courses_by_gap(candidate_courses, gap_dict):
    path_blueprint = {}
    for gap_skill, missing_levels in gap_dict.items():
        gap_skill_lower = gap_skill.lower()
        for req_level in sorted(missing_levels):
            step_name = f"{gap_skill.upper()} (Cần học Level {req_level})"
            valid_for_this_step = []

            for course in candidate_courses:
                c_skills = [s.lower() for s in course.get("target_skills", [])]
                c_lvl = int(course.get("level", 1)) if str(course.get("level", 1)).isdigit() else 1

                search_term = GLOBAL_ALIAS_MAP.get(gap_skill_lower, gap_skill_lower)
                search_term_clean = search_term.replace("/", " ").replace("-", " ")

                skill_ok = any(is_skill_match(search_term_clean, s.lower().replace("/", " ").replace("-", " ")) for s in c_skills)

                # Chỉ nhận khóa ĐÚNG level của mốc (chặt) -> giữ khóa chuyên, không loãng pool.
                if skill_ok and c_lvl == req_level:
                    lite_course = {
                        "course_id": course.get("course_id") or course.get("id"),
                        "title": course.get("title", ""),
                        "level": c_lvl,
                        "target_skills": course.get("target_skills", []),
                        "description": (course.get("description", "") or "")[:100] + "..."
                    }
                    valid_for_this_step.append(lite_course)

            # SẮP XẾP XÁC ĐỊNH theo ĐỘ LIÊN QUAN (cao->thấp), course_id là tie-break cuối:
            #  (1) tên gap trong tiêu đề, (2) số skill gap khớp, (3) tỷ lệ skill gap, (4) id
            for c in valid_for_this_step:
                c["_rel"] = _relevance_score(c, gap_skill, gap_dict)
            valid_for_this_step.sort(
                key=lambda c: (-c["_rel"][0], -c["_rel"][1], -c["_rel"][2], str(c.get("course_id", "")))
            )
            for c in valid_for_this_step:
                c.pop("_rel", None)
            if valid_for_this_step:
                path_blueprint[step_name] = valid_for_this_step[:3]

    return path_blueprint

# =====================================================================
# KHỐI 5: GUARDRAIL E(c) — giữ nguyên công thức
# =====================================================================
def evaluate_ai_result(course, expected_step_name, gap_dict):
    match = re.search(r'(.*?)\s*\(Cần học Level (\d+)\)', expected_step_name)
    if not match: return True, 1.0

    req_skill = match.group(1).strip().lower()
    req_clean = GLOBAL_ALIAS_MAP.get(req_skill, req_skill).replace("/", " ").replace("-", " ")
    req_level = int(match.group(2))

    c_skills = [s.lower() for s in course.get("target_skills", [])]
    c_lvl = int(course.get("level", 1)) if str(course.get("level", 1)).isdigit() else 1

    skill_match_score = 0
    for s in c_skills:
        s_clean = GLOBAL_ALIAS_MAP.get(s.replace("/", " ").replace("-", " "), s.replace("/", " ").replace("-", " "))
        if is_skill_match(req_clean, s_clean):
            skill_match_score = 1
            break

    level_align_score = 1 if c_lvl == req_level else (0.5 if c_lvl < req_level else 0)

    gap_keys = [k.lower() for k in gap_dict.keys()]
    redundant_skills = [s for s in c_skills if not any(is_skill_match(g, GLOBAL_ALIAS_MAP.get(s.replace("/", " ").replace("-", " "), s.replace("/", " ").replace("-", " "))) for g in gap_keys)]
    redundancy_penalty = len(redundant_skills) / len(c_skills) if c_skills else 0

    E_c = (0.5 * skill_match_score) + (0.4 * level_align_score) - (0.1 * redundancy_penalty)
    final_score = min(0.99, max(0.1, E_c))
    print(f"  📊 Evaluator chấm điểm [{course.get('title')[:25]}...]: E(c) = {final_score:.2f}")
    return final_score >= 0.7, final_score

# =====================================================================
# KHỐI 6+7: ĐIỀU PHỐI + ĐÓNG GÓI (ĐÃ SỬA Lỗi 1 & 2)
# - LLM CHỈ được chọn id trong chính mốc (valid_ids_per_step).
# - Duyệt MỌI mốc blueprint khi đóng gói -> mốc nào LLM bỏ/chọn-sai
#   thì FALLBACK lấy khóa đầu blueprint của mốc đó. KHÔNG mốc nào bị mất.
# =====================================================================
def rank_courses_with_llm(candidate_courses, gap_dict, top_k=10):
    print("🔍 Đang tìm kiếm các Khóa học Combo (Đa kỹ năng)...")
    combo_results = find_combo_courses(candidate_courses, gap_dict)

    path_blueprint = group_courses_by_gap(candidate_courses, gap_dict)
    if not path_blueprint:
        return {"combo_courses": combo_results, "regular_courses": []}

    print(f"🧠 [GIAI ĐOẠN 2] Thiết kế Lộ trình học từ {len(path_blueprint)} mốc kỹ năng (chọn khóa XÁC ĐỊNH)...")

    # ============================================================
    # CHỌN KHÓA XÁC ĐỊNH (TẤT ĐỊNH - REPRODUCIBLE)
    # Mỗi mốc -> lấy khóa ĐẦU trong blueprint (blueprint đã sort tất định).
    # KHÔNG để LLM chọn khóa nữa -> kết quả lặp lại 100% giữa các lần chạy.
    # LLM (nếu bật use_llm_reasoning) chỉ viết LỜI GIẢI THÍCH, KHÔNG đổi khóa nào được chọn.
    # ============================================================
    final_learning_path = []
    for step_name, courses_in_step in path_blueprint.items():
        if not courses_in_step:
            continue
        cid = courses_in_step[0]["course_id"]   # XÁC ĐỊNH: luôn lấy khóa đầu mốc
        original_course = next((c for c in candidate_courses
                                if c.get("course_id") == cid or c.get("id") == cid), None)
        if not original_course:
            continue

        is_valid, e_c = evaluate_ai_result(original_course, step_name, gap_dict)
        new_course = original_course.copy()
        new_course["relevance_score"] = int(e_c * 100)
        new_course["picked_by"] = "DETERMINISTIC"
        if is_valid:
            new_course["reasoning"] = f"🎯 [MỤC TIÊU: {step_name}]"
        else:
            new_course["reasoning"] = f"🚨 [BỊ CHẶN - E(c)={e_c:.2f}] Sai level/kỹ năng cho {step_name}."
        final_learning_path.append(new_course)

    return {"combo_courses": combo_results, "regular_courses": final_learning_path}


if __name__ == "__main__":
    pass