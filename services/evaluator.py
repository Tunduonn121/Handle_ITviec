import json
from typing import List, Dict, Set, Any
from services.aliases import clean_and_normalize

class RecommendationEvaluator:
    def __init__(self):
        pass

    def _is_skill_matched(self, required_skill: str, course_skill: str) -> bool:
        """
        Hàm so khớp an toàn: Xử lý triệt để lỗi chuẩn hóa kép.
        """
        req_clean = clean_and_normalize(required_skill)
        crs_clean = clean_and_normalize(course_skill)
        
        if req_clean == crs_clean: return True
        
        # Bọc thép đặc trị cho các môn dễ dính lỗi chuỗi con
        if "c#" in req_clean and "c#" in crs_clean: return True
        if ".net" in req_clean and ".net" in crs_clean: return True
        
        # So khớp tập hợp từ để bắt các biến thể (VD: "rest api" và "restful api")
        words1, words2 = set(req_clean.split()), set(crs_clean.split())
        return words1.issubset(words2) or words2.issubset(words1)

    def is_course_relevant(self, course: Dict[str, Any], gap_dict: Dict[str, List[int]]) -> bool:
        if not isinstance(course, dict): return False
            
        c_skills = course.get("target_skills", [])
        c_lvl = int(course.get("level", 1)) if str(course.get("level", 1)).isdigit() else 1
            
        for req_skill, missing_levels in gap_dict.items():
            for c_skill in c_skills:
                if self._is_skill_matched(req_skill, c_skill):
                    # Nếu kỹ năng khớp, kiểm tra xem khóa học có bao phủ level đang hổng không
                    if c_lvl in missing_levels or c_lvl <= max(missing_levels):
                        return True
        return False

    def calculate_precision_at_k(self, recommended_courses: List[Dict], gap_dict: Dict[str, List[int]], k: int) -> float:
        top_k_rec = recommended_courses[:k]
        if not top_k_rec: return 0.0
        relevant_count = sum(1 for c in top_k_rec if self.is_course_relevant(c, gap_dict))
        return relevant_count / len(top_k_rec)

    def calculate_skill_coverage(self, recommended_courses: List[Dict], gap_dict: Dict[str, List[int]]) -> float:
        if not gap_dict: return 1.0
        
        # Khởi tạo tập hợp chứa các kỹ năng yêu cầu ĐÃ ĐƯỢC LẤP
        skills_covered: Set[str] = set()
        
        for course in recommended_courses:
            if isinstance(course, dict):
                c_skills = course.get("target_skills", [])
                
                # Đối chiếu từng kỹ năng của khóa học với đống Lỗ hổng
                for req_skill in gap_dict.keys():
                    if req_skill in skills_covered: continue # Môn này đã được lấp rồi thì bỏ qua
                    
                    for c_skill in c_skills:
                        if self._is_skill_matched(req_skill, c_skill):
                            skills_covered.add(req_skill)
                            break
                
        # Tỷ lệ lấp đầy = Số môn đã lấp / Tổng số môn bị thiếu
        return len(skills_covered) / len(gap_dict.keys())

def log_live_evaluation_metrics(task_id: str, recommended_list: List[Dict], combo_list: List[Dict], candidate_pool: List[Dict], gap_dict: Dict[str, List[int]]):
    evaluator = RecommendationEvaluator()
    print("\n" + "="*60)
    print(f"📊 [LIVE TELEMETRY] ĐÁNH GIÁ CHẤT LƯỢNG LỘ TRÌNH HỌC - TASK {task_id}")
    print("="*60)
    
    p_at_3 = evaluator.calculate_precision_at_k(recommended_list, gap_dict, k=3)
    p_at_5 = evaluator.calculate_precision_at_k(recommended_list, gap_dict, k=5)
    
    full_path = combo_list + recommended_list 
    coverage = evaluator.calculate_skill_coverage(full_path, gap_dict)
    
    print(f"   🔹 Precision@3 (Độ chính xác sư phạm Top 3) : {p_at_3 * 100:.1f}%")
    print(f"   🔹 Precision@5 (Độ chính xác sư phạm Top 5) : {p_at_5 * 100:.1f}%")
    print(f"   🔹 Skill Coverage (Tỷ lệ lấp đầy Lỗ hổng)   : {coverage * 100:.1f}%")
    print("="*60 + "\n")