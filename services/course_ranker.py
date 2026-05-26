import json
import os
import re
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OLLAMA_API_KEY")
HOST_URL = 'https://ollama.com' 
MODEL_NAME = 'qwen3-coder:480b-cloud'

if not API_KEY:
    print("❌ LỖI: Sếp chưa điền OLLAMA_API_KEY vào file .env kìa!")
    exit()

client = Client(host=HOST_URL, headers={'Authorization': f'Bearer {API_KEY}'})

GLOBAL_ALIAS_MAP = {
    "sql server": "microsoft sql servers", "postgres": "postgresql", "mongo": "mongodb",
    "rdbms": "relational database", "nosql": "nosql databases",
    "restful api": "rest api", "web api": "rest api", "api design": "rest api", "graphql api": "graphql", "grpc": "g-rpc",
    "microservice": "microservices", "oop concepts": "oop", "object oriented programming": "oop",
    "express": "expressjs", "react": "reactjs", "react.js": "reactjs", "vue": "vuejs",
    "vue.js": "vuejs", "node": "nodejs", "node.js": "nodejs", "next": "nextjs",
    "nuxt": "nuxtjs", "angular.js": "angular",
    ".net 8": ".net", ".net 7": ".net", ".net 6": ".net", ".net 5": ".net",
    ".net core": ".net", "asp.net core": ".net", "c sharp": "c#",
    "k8s": "kubernetes", "aws": "amazon web services", "gcp": "google cloud", 
    "google cloud platform": "google cloud", "azure": "microsoft azure", "ci/cd": "continuous integration",
    "genai": "generative ai", "ml": "machine learning", "dl": "deep learning",
    "nlp": "natural language processing", "cv": "computer vision",
    "golang": "go", "cpp": "c++", "js": "javascript", "ts": "typescript",
    "object-relational mapping": "entity framework", "orm": "entity framework",
    "mean": "expressjs" # Thêm alias cứu khóa MEAN Stack
}

# 🚀 HÀM SO KHỚP CHUỖI SIÊU AN TOÀN (CHỐNG LỖI CHỮ "R")
# 🚀 HÀM SO KHỚP CHUỖI SIÊU AN TOÀN (CHỐNG LỖI CHỮ "R" VÀ LỖI BAO HÀM RỘNG)
# 🚀 HÀM SO KHỚP CHUỖI CÂN BẰNG (CHỐNG LỖI CHỮ "R" VÀ GIẢI OAN CHO CÁC TỪ MỞ RỘNG)
def is_safe_match(term1: str, term2: str) -> bool:
    if term1 == term2: 
        return True
        
    # Cắt thành các từ đơn (Ví dụ: "docker software" -> {"docker", "software"})
    words1 = set(term1.split())
    words2 = set(term2.split())
    
    # 🎯 LƯỠI DAO THÔNG MINH:
    # 1. Nếu "docker" nằm trong {"docker", "software"} -> Hợp lệ (True)
    # 2. Nếu chữ "r" mang đi đọ với tập {"express"} -> Không nằm trong -> Bị chặn (False)
    if words1.issubset(words2) or words2.issubset(words1):
        return True
        
    return False

def find_combo_courses(candidate_courses, gap_dict):
    combo_courses = []
    gap_skills = set([skill.lower() for skill in gap_dict.keys()])
    
    for course in candidate_courses:
        c_skills_raw = [s.lower().replace("/", " ").replace("-", " ") for s in course.get("target_skills", [])]
        c_skills_normalized = set()
        
        for c_s in c_skills_raw:
            for k, v in GLOBAL_ALIAS_MAP.items():
                if is_safe_match(k, c_s) or is_safe_match(v, c_s):
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
            lite_combo["reasoning"] = f"🎯 [KHÓA HỌC COMBO] -> Khóa học này cực kỳ tối ưu thời gian vì nó bao phủ cùng lúc {coverage_score} kỹ năng bạn đang thiếu: {skill_list_str}."
            combo_courses.append(lite_combo)
            
    combo_courses.sort(key=lambda x: x["coverage_score"], reverse=True)
    return combo_courses[:3]

def group_courses_by_gap(candidate_courses, gap_dict):
    path_blueprint = {}
    for gap_skill, missing_levels in gap_dict.items():
        gap_skill_lower = gap_skill.lower()
        for req_level in sorted(missing_levels):
            step_name = f"{gap_skill.upper()} (Cần học Level {req_level})"
            valid_for_this_step = []
            
            for course in candidate_courses:
                c_skills = [s.lower() for s in course.get("target_skills", [])]
                try:
                    c_lvl = int(course.get("level", 1))
                except:
                    c_lvl = 1
                    
                search_term = GLOBAL_ALIAS_MAP.get(gap_skill_lower, gap_skill_lower)
                search_term_clean = search_term.replace("/", " ").replace("-", " ") 
                
                is_skill_match = any(is_safe_match(search_term_clean, s.lower().replace("/", " ").replace("-", " ")) for s in c_skills)
                
                if is_skill_match:
                    if c_lvl == req_level:
                        priority_score = 2
                        lite_course = {
                            "course_id": course.get("course_id") or course.get("id"),
                            "title": course.get("title", ""),
                            "level": c_lvl,
                            "target_skills": course.get("target_skills", []),
                            "priority": priority_score,
                            "description": course.get("description", "")[:150] + "..."
                        }
                        valid_for_this_step.append(lite_course)
            
            valid_for_this_step.sort(key=lambda x: x["priority"], reverse=True)
            if valid_for_this_step:
                path_blueprint[step_name] = valid_for_this_step[:3]
                
    return path_blueprint

def evaluate_ai_result(course, expected_step_name, gap_dict):
    W1 = 0.5  
    W2 = 0.5  
    W3 = 0.2  
    THRESHOLD = 0.7 

    match = re.search(r'(.*?)\s*\(Cần học Level (\d+)\)', expected_step_name)
    if not match:
        return True, 1.0 
        
    req_skill = match.group(1).strip().lower()
    req_clean = GLOBAL_ALIAS_MAP.get(req_skill, req_skill).replace("/", " ").replace("-", " ")
    req_level = int(match.group(2))
    
    c_skills = [s.lower() for s in course.get("target_skills", [])]
    c_lvl = int(course.get("level", 1))

    # Tiêu chí 1: SkillMatch (Chỉ dùng hàm is_safe_match, loại bỏ việc so chuỗi thông thường)
    skill_match_score = 0
    for s in c_skills:
        s_clean = s.replace("/", " ").replace("-", " ")
        # Tra cứu alias cho kỹ năng của khóa học trước khi so sánh
        s_clean_aliased = GLOBAL_ALIAS_MAP.get(s_clean, s_clean)
        
        if is_safe_match(req_clean, s_clean_aliased):
            skill_match_score = 1
            break
            
    # Tiêu chí 2: LevelAlign
    level_align_score = 0
    if c_lvl == req_level:
        level_align_score = 1      
    elif c_lvl < req_level:
        level_align_score = 0.5    
    else:
        level_align_score = 0      

    # Tiêu chí 3: Redundancy 
    gap_keys = [k.lower() for k in gap_dict.keys()]
    redundant_skills = [s for s in c_skills if not any(is_safe_match(g, GLOBAL_ALIAS_MAP.get(s.replace("/", " ").replace("-", " "), s.replace("/", " ").replace("-", " "))) for g in gap_keys)]
    redundancy_score = len(redundant_skills) / len(c_skills) if c_skills else 0

    E_c = (W1 * skill_match_score) + (W2 * level_align_score) - (W3 * redundancy_score)
    print(f"  📊 Evaluator chấm điểm [{course.get('title')[:25]}...]: E(c) = {E_c:.2f}")

    if E_c >= THRESHOLD:
        return True, E_c
    else:
        print(f"  🚫 CẢNH BÁO: Đã chặn khóa học AI chọn do E(c) = {E_c:.2f} < {THRESHOLD}!")
        return False, E_c

def rank_courses_with_llm(candidate_courses, gap_dict, top_k=10):
    print("🔍 Đang tìm kiếm các Khóa học Combo (Đa kỹ năng)...")
    combo_results = find_combo_courses(candidate_courses, gap_dict)
    
    path_blueprint = group_courses_by_gap(candidate_courses, gap_dict)
    if not path_blueprint:
        return {"combo_courses": combo_results, "regular_courses": []}

    print(f"🧠 [GIAI ĐOẠN 2] Qwen 480B đang thiết kế Lộ trình học (Learning Path) từ {len(path_blueprint)} mốc kỹ năng...")
    try:
        blueprint_str = json.dumps(path_blueprint, ensure_ascii=False, indent=2)
        required_steps = list(path_blueprint.keys()) 
        
        prompt = f"""Bạn là Thầy giáo IT Cấp cao.
Hệ thống đã phân loại sẵn các khóa học vào từng Mốc Kỹ năng (Step) mà học viên đang thiếu.

BẢN THẢO LỘ TRÌNH:
{blueprint_str}

NHIỆM VỤ: Với mỗi Mốc Kỹ năng (Step), hãy chọn ra ĐÚNG 1 KHÓA HỌC xuất sắc nhất.
ĐỊNH DẠNG ĐẦU RA BẮT BUỘC LÀ JSON DICTIONARY:
{{
"""
        for step in required_steps:
            prompt += f'  "{step}": {{"course_id": "Mã khóa", "relevance_score": 95, "reasoning": "Lý do..."}},\n'
        prompt += """}
"""
        
        response = client.chat(
            model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}],
            stream=False, options={'temperature': 0.1}, format='json' 
        )
        
        raw_text = response['message']['content'].strip()
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            clean_json = raw_text[start_idx:end_idx]
            path_results = json.loads(clean_json)
        else:
            path_results = {} 

        final_learning_path = []
        for step_name, item in path_results.items():
            if not isinstance(item, dict):
                continue
            
            cid = item.get("course_id")
            if not cid: continue 
            
            original_course = None
            for c in candidate_courses:
                if isinstance(c, dict) and (c.get("course_id") == cid or c.get("id") == cid):
                    original_course = c
                    break
            
            if original_course:
                is_valid, e_c_score = evaluate_ai_result(original_course, step_name, gap_dict)
                ai_reasoning = item.get("reasoning", "")
                
                new_course = original_course.copy()
                if is_valid:
                    new_course["relevance_score"] = int(e_c_score * 100)
                    new_course["reasoning"] = f"🎯 [DÀNH CHO MỤC TIÊU: {step_name}] -> {ai_reasoning}"
                else:
                    new_course["relevance_score"] = int(e_c_score * 100) 
                    new_course["reasoning"] = f"🚨 [BỊ CHẶN VÌ LỖI SƯ PHẠM/KỸ NĂNG - Điểm {e_c_score:.2f}] [MỤC TIÊU: {step_name}] -> Khóa này sai Level hoặc không chứa kỹ năng yêu cầu!"
                
                final_learning_path.append(new_course)
                
        return {
            "combo_courses": combo_results,
            "regular_courses": final_learning_path
        }
    
    except Exception as e:
        print(f"❌ LỖI QWEN API TRONG RANKER: {e}")
        return {"combo_courses": combo_results, "regular_courses": []}

if __name__ == "__main__":
    pass