import json
from typing import List, Dict, Set, Any
from services.aliases import is_skill_match, is_level_fit

# =====================================================================
# LƯU Ý QUAN TRỌNG VỀ TÍNH ĐÚNG ĐẮN:
# Module này đo "Guardrail Consistency Rate" — tỷ lệ khóa gợi ý mà hàng rào
# toán học xác nhận KHỚP skill + đúng level yêu cầu. Đây là chỉ số NỘI BỘ
# (đo độ chặt của guardrail), KHÔNG phải Precision so với ground-truth.
# Precision/Recall THẬT được đo riêng ở evaluate_offline.py (nhãn người gán).
# =====================================================================
class RecommendationEvaluator:
    def is_course_relevant(self, course: Dict[str, Any], gap_dict: Dict[str, List[int]]) -> bool:
        if not isinstance(course, dict):
            return False
        c_skills = course.get("target_skills", [])
        try:
            c_lvl = int(course.get("level", 1))
        except (ValueError, TypeError):
            c_lvl = 1

        for req_skill, missing_levels in gap_dict.items():
            for c_skill in c_skills:
                if is_skill_match(req_skill, c_skill):
                    # CHỈ tính khớp khi khóa dạy ĐÚNG level đang thiếu (bỏ vế nới lỏng cũ)
                    if is_level_fit(c_lvl, missing_levels):
                        return True
        return False

    def guardrail_consistency_at_k(self, recommended_courses: List[Dict], gap_dict: Dict[str, List[int]], k: int) -> float:
        top_k = recommended_courses[:k]
        if not top_k:
            return 0.0
        consistent = sum(1 for c in top_k if self.is_course_relevant(c, gap_dict))
        return consistent / len(top_k)

    def calculate_skill_coverage(self, recommended_courses: List[Dict], gap_dict: Dict[str, List[int]]) -> float:
        if not gap_dict:
            return 1.0
        skills_covered: Set[str] = set()
        for course in recommended_courses:
            if not isinstance(course, dict):
                continue
            c_skills = course.get("target_skills", [])
            try:
                c_lvl = int(course.get("level", 1))
            except (ValueError, TypeError):
                c_lvl = 1
            for req_skill, missing_levels in gap_dict.items():
                if req_skill in skills_covered:
                    continue
                for c_skill in c_skills:
                    # Coverage giờ XÉT CẢ LEVEL (đồng bộ với gap), không bỏ qua như trước
                    if is_skill_match(req_skill, c_skill) and is_level_fit(c_lvl, missing_levels):
                        skills_covered.add(req_skill)
                        break
        return len(skills_covered) / len(gap_dict.keys())


def log_live_evaluation_metrics(task_id: str, recommended_list: List[Dict], combo_list: List[Dict], candidate_pool: List[Dict], gap_dict: Dict[str, List[int]]):
    ev = RecommendationEvaluator()
    print("\n" + "=" * 60)
    print(f"📊 [LIVE TELEMETRY] CHỈ SỐ NỘI BỘ (KHÔNG phải Precision) - TASK {task_id}")
    print("=" * 60)
    gcr_3 = ev.guardrail_consistency_at_k(recommended_list, gap_dict, k=3)
    gcr_5 = ev.guardrail_consistency_at_k(recommended_list, gap_dict, k=5)
    coverage = ev.calculate_skill_coverage(combo_list + recommended_list, gap_dict)
    print(f"   🔹 Guardrail Consistency@3 : {gcr_3 * 100:.1f}%  (khóa gợi ý khớp guardrail)")
    print(f"   🔹 Guardrail Consistency@5 : {gcr_5 * 100:.1f}%")
    print(f"   🔹 Skill Coverage (có xét level) : {coverage * 100:.1f}%")
    print("   ⚠️ Precision/Recall THẬT: chạy evaluate_offline.py với nhãn người gán.")
    print("=" * 60 + "\n")