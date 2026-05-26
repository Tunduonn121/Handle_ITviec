import json
import os
import re
from ollama import Client
from dotenv import load_dotenv
from services.aliases import GLOBAL_ALIAS_MAP

load_dotenv()

API_KEY = os.getenv("OLLAMA_API_KEY")
HOST_URL = 'https://ollama.com' 
MODEL_NAME = 'qwen3-coder:480b-cloud'

client = Client(host=HOST_URL, headers={'Authorization': f'Bearer {API_KEY}'})

def is_safe_match(term1: str, term2: str) -> bool:
    t1, t2 = term1.lower().strip(), term2.lower().strip()
    if t1 == t2: return True
    
    # Bọc thép đặc trị cho C# và .NET
    if "c#" in t1 and "c#" in t2: return True
    if ".net" in t1 and ".net" in t2: return True
    
    words1, words2 = set(t1.split()), set(t2.split())
    return words1.issubset(words2) or words2.issubset(words1)

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
            lite_combo["reasoning"] = f"🎯 [KHÓA HỌC COMBO] -> Khóa học này tối ưu thời gian vì bao phủ {coverage_score} kỹ năng: {skill_list_str}."
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
                c_lvl = int(course.get("level", 1)) if str(course.get("level", 1)).isdigit() else 1
                    
                search_term = GLOBAL_ALIAS_MAP.get(gap_skill_lower, gap_skill_lower)
                search_term_clean = search_term.replace("/", " ").replace("-", " ") 
                
                is_skill_match = any(is_safe_match(search_term_clean, s.lower().replace("/", " ").replace("-", " ")) for s in c_skills)
                
                if is_skill_match and c_lvl == req_level:
                    lite_course = {
                        "course_id": course.get("course_id") or course.get("id"),
                        "title": course.get("title", ""),
                        "level": c_lvl,
                        "target_skills": course.get("target_skills", []),
                        "description": course.get("description", "")[:100] + "..."
                    }
                    valid_for_this_step.append(lite_course)
            
            if valid_for_this_step:
                path_blueprint[step_name] = valid_for_this_step[:3]
                
    return path_blueprint

def evaluate_ai_result(course, expected_step_name, gap_dict):
    match = re.search(r'(.*?)\s*\(Cần học Level (\d+)\)', expected_step_name)
    if not match: return True, 1.0 
    
    req_skill = match.group(1).strip().lower()
    req_clean = GLOBAL_ALIAS_MAP.get(req_skill, req_skill).replace("/", " ").replace("-", " ")
    req_level = int(match.group(2))
    
    c_skills = [s.lower() for s in course.get("target_skills", [])]
    c_lvl = int(course.get("level", 1)) if str(course.get("level", 1)).isdigit() else 1

    # Tiêu chí 1: Độ khớp kỹ năng (Trọng số 0.5)
    skill_match_score = 0
    for s in c_skills:
        s_clean = GLOBAL_ALIAS_MAP.get(s.replace("/", " ").replace("-", " "), s.replace("/", " ").replace("-", " "))
        if is_safe_match(req_clean, s_clean):
            skill_match_score = 1
            break
            
    # Tiêu chí 2: Độ chuẩn xác Level (Trọng số 0.4)
    level_align_score = 1 if c_lvl == req_level else (0.5 if c_lvl < req_level else 0)
    
    # Tiêu chí 3: Phạt trừ điểm nếu khóa học chứa quá nhiều môn không liên quan đến Gap (Trọng số 0.1)
    gap_keys = [k.lower() for k in gap_dict.keys()]
    redundant_skills = [s for s in c_skills if not any(is_safe_match(g, GLOBAL_ALIAS_MAP.get(s.replace("/", " ").replace("-", " "), s.replace("/", " ").replace("-", " "))) for g in gap_keys)]
    redundancy_penalty = len(redundant_skills) / len(c_skills) if c_skills else 0

    # Công thức tính điểm tổng hợp:
    E_c = (0.5 * skill_match_score) + (0.4 * level_align_score) - (0.1 * redundancy_penalty)
    
    # Ép điểm không vượt quá 0.99 để nhìn chân thực
    final_score = min(0.99, max(0.1, E_c))
    
    print(f"  📊 Evaluator chấm điểm [{course.get('title')[:25]}...]: E(c) = {final_score:.2f}")
    return final_score >= 0.7, final_score

def rank_courses_with_llm(candidate_courses, gap_dict, top_k=10):
    print("🔍 Đang tìm kiếm các Khóa học Combo (Đa kỹ năng)...")
    combo_results = find_combo_courses(candidate_courses, gap_dict)
    
    path_blueprint = group_courses_by_gap(candidate_courses, gap_dict)
    if not path_blueprint:
        return {"combo_courses": combo_results, "regular_courses": []}

    print(f"🧠 [GIAI ĐOẠN 2] Qwen 480B đang thiết kế Lộ trình học từ {len(path_blueprint)} mốc kỹ năng...")
    
    # 🚀🚀🚀 THUẬT TOÁN CHIA ĐỂ TRỊ (CHUNKING MAGIC) 🚀🚀🚀
    required_steps = list(path_blueprint.keys())
    chunk_size = 4 # Mỗi lần chỉ đưa AI xử lý 4 kỹ năng (Chống đứt JSON)
    path_results = {}
    
    for i in range(0, len(required_steps), chunk_size):
        chunk_steps = required_steps[i:i+chunk_size]
        chunk_blueprint = {k: path_blueprint[k] for k in chunk_steps}
        blueprint_str = json.dumps(chunk_blueprint, ensure_ascii=False, indent=2)
        
        prompt = f"""Bạn là Thầy giáo IT Cấp cao.
BẢN THẢO LỘ TRÌNH (Phần {i//chunk_size + 1}):
{blueprint_str}

NHIỆM VỤ: Với mỗi Mốc Kỹ năng (Step) ở trên, chọn ra 1 KHÓA HỌC xuất sắc nhất.
BẮT BUỘC TRẢ VỀ CHUẨN JSON (Không giải thích thêm):
{{
"""
        for step in chunk_steps:
            prompt += f'  "{step}": {{"course_id": "Mã khóa", "relevance_score": 95, "reasoning": "Lý do..."}},\n'
        prompt += "}"
        
        try:
            response = client.chat(
                model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}],
                stream=False, options={'temperature': 0.0}, format='json' 
            )
            raw_text = response['message']['content'].strip()
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                chunk_results = json.loads(raw_text[start_idx:end_idx])
                path_results.update(chunk_results)
        except Exception as e:
            print(f"⚠️ CẢNH BÁO: Lỗi AI ở Chunk {i//chunk_size + 1}: {e}")

    # ===== HOÀN THIỆN ĐÓNG GÓI =====
    final_learning_path = []
    for step_name, item in path_results.items():
        if not isinstance(item, dict): continue
        cid = item.get("course_id")
        if not cid: continue 
        
        original_course = next((c for c in candidate_courses if c.get("course_id") == cid or c.get("id") == cid), None)
        if original_course:
            is_valid, e_c_score = evaluate_ai_result(original_course, step_name, gap_dict)
            new_course = original_course.copy()
            new_course["relevance_score"] = int(e_c_score * 100)
            if is_valid:
                new_course["reasoning"] = f"🎯 [MỤC TIÊU: {step_name}] -> {item.get('reasoning', '')}"
            else:
                new_course["reasoning"] = f"🚨 [BỊ CHẶN LỖI SƯ PHẠM - Điểm {e_c_score:.2f}] -> Khóa này sai Level hoặc không chứa kỹ năng yêu cầu!"
            final_learning_path.append(new_course)
            
    return {"combo_courses": combo_results, "regular_courses": final_learning_path}


if __name__ == "__main__":
    pass