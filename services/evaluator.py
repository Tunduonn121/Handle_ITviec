import json
import re
from typing import List, Dict, Set, Any

class RecommendationEvaluator:
    def __init__(self):
        # Từ điển Alias đồng bộ để nhận diện kỹ năng chính xác
        self.alias_map = {
        "sql server": "microsoft sql servers", "postgres": "postgresql", "mongo": "mongodb",
        "rdbms": "relational database", "nosql": "nosql databases",
        "restful api": "rest api", "graphql api": "graphql", "grpc": "g-rpc",
        "microservice": "microservices", "oop concepts": "oop", "object oriented programming": "oop",
        "express": "expressjs", "react": "reactjs", "react.js": "reactjs", "vue": "vuejs",
        "vue.js": "vuejs", "node": "nodejs", "node.js": "nodejs", "next": "nextjs",
        "nuxt": "nuxtjs", "angular.js": "angular",
        ".net 8": ".net", ".net 7": ".net", ".net 6": ".net", ".net 5": ".net",
        ".net core": ".net", "asp.net core": "asp.net", "c sharp": "c#",
        "k8s": "kubernetes", "aws": "amazon web services", "gcp": "google cloud", 
        "google cloud platform": "google cloud", "azure": "microsoft azure", "ci/cd": "continuous integration",
        "genai": "generative ai", "ml": "machine learning", "dl": "deep learning",
        "nlp": "natural language processing", "cv": "computer vision",
        "golang": "go", "cpp": "c++", "js": "javascript", "ts": "typescript"
    }

    def _normalize_skill(self, skill: str) -> str:
        s = skill.lower().strip().replace("/", " ").replace("-", " ")
        return self.alias_map.get(s, s)

    def is_course_relevant(self, course: Dict[str, Any], gap_dict: Dict[str, List[int]]) -> bool:
        """ Kiểm tra một khóa học thực tế từ DB có thực sự xử lý được Gap không """
        if not isinstance(course, dict):
            return False
            
        c_skills = {self._normalize_skill(s) for s in course.get("target_skills", [])}
        gap_skills = {self._normalize_skill(s) for s in gap_dict.keys()}
        
        # 1. Kiểm tra giao thoa kỹ năng
        matching_skills = c_skills.intersection(gap_skills)
        if not matching_skills:
            return False
            
        # 2. Kiểm tra tính phù hợp về Level (Sư phạm)
        try:
            c_lvl = int(course.get("level", 1))
        except:
            c_lvl = 1
            
        for skill in matching_skills:
            orig_key = next((k for k in gap_dict.keys() if self._normalize_skill(k) == skill), None)
            if orig_key:
                missing_levels = gap_dict[orig_key]
                # Khóa học hợp lệ nếu thuộc mốc level thiếu hoặc bổ trợ nền tảng dưới mốc đó
                if c_lvl in missing_levels or c_lvl <= max(missing_levels):
                    return True
        return False

    def calculate_precision_at_k(self, recommended_courses: List[Dict], gap_dict: Dict[str, List[int]], k: int) -> float:
        top_k_rec = recommended_courses[:k]
        if not top_k_rec:
            return 0.0
        relevant_count = sum(1 for c in top_k_rec if self.is_course_relevant(c, gap_dict))
        return relevant_count / len(top_k_rec)

    def calculate_recall_at_k(self, recommended_courses: List[Dict], all_candidate_pool: List[Dict], gap_dict: Dict[str, List[int]], k: int) -> float:
        top_k_rec = recommended_courses[:k]
        total_relevant_in_db = sum(1 for c in all_candidate_pool if self.is_course_relevant(c, gap_dict))
        if total_relevant_in_db == 0:
            return 1.0
        relevant_in_top_k = sum(1 for c in top_k_rec if self.is_course_relevant(c, gap_dict))
        return relevant_in_top_k / total_relevant_in_db

    def calculate_skill_coverage(self, recommended_courses: List[Dict], gap_dict: Dict[str, List[int]]) -> float:
        if not gap_dict:
            return 1.0
        gap_skills = {self._normalize_skill(s) for s in gap_dict.keys()}
        covered_skills: Set[str] = set()
        
        for course in recommended_courses:
            if isinstance(course, dict):
                c_skills = {self._normalize_skill(s) for s in course.get("target_skills", [])}
                matches = c_skills.intersection(gap_skills)
                covered_skills.update(matches)
                
        return len(covered_skills) / len(gap_skills)

# =====================================================================
# HÀM NHÚNG TRỰC TIẾP VÀO LUỒNG CHẠY WEB (LIVE TELEMETRY LOGGER)
# =====================================================================
def log_live_evaluation_metrics(task_id: str, recommended_list: List[Dict], candidate_pool: List[Dict], gap_dict: Dict[str, List[int]]):
    """ Hàm này sẽ được gọi trong main.py để in số liệu thực tế ra Terminal """
    evaluator = RecommendationEvaluator()
    
    print("\n" + "="*60)
    print(f"📊 [LIVE TELEMETRY] ĐÁNH GIÁ CHẤT LƯỢNG AI - TASK {task_id}")
    print("="*60)
    
    # Tính toán các chỉ số dựa trên Lộ trình Regular (danh sách tuyến tính)
    p_at_3 = evaluator.calculate_precision_at_k(recommended_list, gap_dict, k=3)
    p_at_5 = evaluator.calculate_precision_at_k(recommended_list, gap_dict, k=5)
    r_at_3 = evaluator.calculate_recall_at_k(recommended_list, candidate_pool, gap_dict, k=3)
    r_at_5 = evaluator.calculate_recall_at_k(recommended_list, candidate_pool, gap_dict, k=5)
    coverage = evaluator.calculate_skill_coverage(recommended_list, gap_dict)
    
    print(f"   🔹 Precision@3 (Độ chính xác Top 3) : {p_at_3 * 100:.1f}%")
    print(f"   🔹 Precision@5 (Độ chính xác Top 5) : {p_at_5 * 100:.1f}%")
    print(f"   🔹 Recall@3    (Độ phủ Ứng viên Top 3): {r_at_3 * 100:.1f}%")
    print(f"   🔹 Recall@5    (Độ phủ Ứng viên Top 5): {r_at_5 * 100:.1f}%")
    print(f"   🔹 Skill Coverage (Độ lấp đầy Gap)   : {coverage * 100:.1f}%")
    print("="*60 + "\n")