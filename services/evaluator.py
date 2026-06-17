import json
from typing import List, Dict, Set, Any
from services.aliases import clean_and_normalize

# =====================================================================
# KHỐI 1: LỚP KIỂM TOÁN SƯ PHẠM (RECOMMENDATION EVALUATOR)
# Mục đích: Đóng vai trò là "Giám khảo độc lập" dùng Toán học để 
# chấm điểm lại kết quả của LLM, đảm bảo không có Ảo giác (Hallucination).
# =====================================================================
class RecommendationEvaluator:
    def __init__(self):
        pass

    def _is_skill_matched(self, required_skill: str, course_skill: str) -> bool:
        """
        Hàm so khớp an toàn: Xử lý triệt để lỗi chuẩn hóa kép.
        Mục đích: Chống lại việc LLM sinh ra từ khóa gần giống nhưng sai bản chất.
        """
        req_clean = clean_and_normalize(required_skill)
        crs_clean = clean_and_normalize(course_skill)
        
        if req_clean == crs_clean: return True
        
        # Bọc thép đặc trị cho các môn dễ dính lỗi chuỗi con (Substring matching errors)
        if "c#" in req_clean and "c#" in crs_clean: return True
        if ".net" in req_clean and ".net" in crs_clean: return True
        
        # So khớp tập hợp từ để bắt các biến thể (VD: "rest api" và "restful api")
        words1, words2 = set(req_clean.split()), set(crs_clean.split())
        return words1.issubset(words2) or words2.issubset(words1)

    def is_course_relevant(self, course: Dict[str, Any], gap_dict: Dict[str, List[int]]) -> bool:
        # Kiểm tra xem 1 khóa học có THỰC SỰ giải quyết được lỗ hổng nào không
        if not isinstance(course, dict): return False
            
        c_skills = course.get("target_skills", [])
        c_lvl = int(course.get("level", 1)) if str(course.get("level", 1)).isdigit() else 1
            
        # Quét qua từng kỹ năng bị hổng (Skill Gap) của ứng viên
        for req_skill, missing_levels in gap_dict.items():
            for c_skill in c_skills:
                if self._is_skill_matched(req_skill, c_skill):
                    # Nếu kỹ năng khớp, kiểm tra xem khóa học có bao phủ level đang hổng không
                    if c_lvl in missing_levels or c_lvl <= max(missing_levels):
                        return True
        # Nếu duyệt hết mà khóa học không lấp được lỗ hổng nào -> Đánh dấu là Ảo giác
        return False

    # =====================================================================
    # KHỐI 2: ĐO LƯỜNG ĐỘ CHÍNH XÁC (PRECISION@K)
    # Mục đích: Tính toán công thức Precision@K trong luận văn.
    # Đo xem trong Top-K khóa học gợi ý, có bao nhiêu khóa là chuẩn xác.
    # =====================================================================
    def calculate_precision_at_k(self, recommended_courses: List[Dict], gap_dict: Dict[str, List[int]], k: int) -> float:
        top_k_rec = recommended_courses[:k]
        if not top_k_rec: return 0.0
        # Đếm số lượng khóa học vượt qua được bài test "is_course_relevant"
        relevant_count = sum(1 for c in top_k_rec if self.is_course_relevant(c, gap_dict))
        # Trả về tỷ lệ %
        return relevant_count / len(top_k_rec)

    # =====================================================================
    # KHỐI 3: ĐO LƯỜNG ĐỘ PHỦ KỸ NĂNG (SKILL COVERAGE)
    # Mục đích: Tính toán công thức Coverage trong luận văn.
    # Đo xem lộ trình học đã lấp được bao nhiêu phần trăm (%) Lỗ hổng (Gap).
    # =====================================================================
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

# =====================================================================
# KHỐI 4: MODULE GIÁM SÁT THỜI GIAN THỰC (LIVE TELEMETRY)
# Mục đích: Hàm này được gọi ở cuối pipeline để in báo cáo ra Terminal.
# Nó cung cấp số liệu thực tế (100%) để Sếp đưa vào Bảng 4.3 trong Khóa luận.
# =====================================================================
def log_live_evaluation_metrics(task_id: str, recommended_list: List[Dict], combo_list: List[Dict], candidate_pool: List[Dict], gap_dict: Dict[str, List[int]]):
    evaluator = RecommendationEvaluator()
    print("\n" + "="*60)
    print(f"📊 [LIVE TELEMETRY] ĐÁNH GIÁ CHẤT LƯỢNG LỘ TRÌNH HỌC - TASK {task_id}")
    print("="*60)
    
    # Đo lường Top 3 và Top 5
    p_at_3 = evaluator.calculate_precision_at_k(recommended_list, gap_dict, k=3)
    p_at_5 = evaluator.calculate_precision_at_k(recommended_list, gap_dict, k=5)
    
    # Gộp chung cả khóa Combo và khóa Thường để đo độ phủ tổng thể
    full_path = combo_list + recommended_list 
    coverage = evaluator.calculate_skill_coverage(full_path, gap_dict)
    
    # In kết quả ra màn hình Terminal
    print(f"   🔹 Precision@3 (Độ chính xác sư phạm Top 3) : {p_at_3 * 100:.1f}%")
    print(f"   🔹 Precision@5 (Độ chính xác sư phạm Top 5) : {p_at_5 * 100:.1f}%")
    print(f"   🔹 Skill Coverage (Tỷ lệ lấp đầy Lỗ hổng)   : {coverage * 100:.1f}%")
    print("="*60 + "\n")