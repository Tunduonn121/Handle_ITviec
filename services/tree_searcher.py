import json
import re
import os
from dotenv import load_dotenv
from ollama import Client
from .tree_builder import load_courses_from_sql, build_course_tree

load_dotenv()
api_key = os.getenv("OLLAMA_API_KEY")
client = Client(host='https://ollama.com', headers={'Authorization': f'Bearer {api_key}'})
MODEL_NAME = 'qwen3-coder:480b-cloud'

# Bộ nhớ đệm lưu vết toàn cục nằm trên RAM
MICRO_PRUNING_CACHE = {}

def evaluate_single_skill_on_node(node_path: str, single_skill: str) -> bool:
    """Hỏi AI một kỹ năng duy nhất và lưu cache cứng cho kỹ năng đó tại Node này"""
    global MICRO_PRUNING_CACHE # KHAI BÁO Ở ĐẦU HÀM DUY NHẤT LÀ ĐỦ!
    
    if node_path not in MICRO_PRUNING_CACHE:
        MICRO_PRUNING_CACHE[node_path] = {}
        
    skill_clean = single_skill.lower().strip()
    
    # ⚡ NẾU ĐÃ CÓ TRONG CACHE: Trả về kết quả ngay lập tức
    if skill_clean in MICRO_PRUNING_CACHE[node_path]:
        return MICRO_PRUNING_CACHE[node_path][skill_clean]
        
    # 🌐 NẾU CHƯA CÓ: Gọi AI phân tích ngữ nghĩa
    prompt = f"""Quyết định xem danh mục "{node_path}" có chứa khóa học dạy về kỹ năng "{single_skill}" hay không.
Trả lời một chữ duy nhất: YES hoặc NO.
"""
    try:
        response = client.chat(
            model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}],
            stream=False, options={'temperature': 0.0}
        )
        answer = response['message']['content'].strip().upper()
        result = bool(re.search(r'\bYES\b', answer))
        
        # ĐÃ XÓA DÒNG GLOBAL BỊ LỖI Ở ĐÂY
        MICRO_PRUNING_CACHE[node_path][skill_clean] = result
        return result
    except Exception:
        return True # Thà duyệt nhầm còn hơn bỏ sót khi lỗi mạng

def real_llm_evaluate(node_path, gap_dict):
    """
    Hàm gác cổng cải tiến: Duyệt qua từng môn trong đống Gap của User.
    Chỉ cần 1 môn báo YES (được lưu từ trước hoặc vừa hỏi xong) là MỞ KHÓA NHÁNH.
    """
    missing_skills = list(gap_dict.keys())
    
    for skill in missing_skills:
        if evaluate_single_skill_on_node(node_path, skill):
            print(f"   🎯 [CACHE HIT] Phát hiện môn '{skill}' nằm trong nhánh [{node_path}]!")
            return True
            
    return False

def dfs_tree_search(course_tree, gap_dict):
    global MICRO_PRUNING_CACHE
    print(f"\n🧠 [HỆ THỐNG] Kích thước Cache hiện tại: {len(MICRO_PRUNING_CACHE)} nhánh đã quét.")
    
    stack = [(cat_name, cat_content) for cat_name, cat_content in course_tree.items()]
    candidate_courses = []

    print(f"\n🚀 BẮT ĐẦU DUYỆT CÂY DFS VỚI LLM PRUNING")
    print(f"🎯 Kỹ năng cần tìm ({len(gap_dict)} skills)")
    
    while stack:
        current_node_path, current_node_content = stack.pop()
        is_relevant = real_llm_evaluate(current_node_path, gap_dict)
        
        if is_relevant:
            if isinstance(current_node_content, list):
                candidate_courses.extend(current_node_content)
            else:
                for sub_name, sub_content in current_node_content.items():
                    stack.append((f"{current_node_path} -> {sub_name}", sub_content))
    return candidate_courses

# --- TEST HỆ THỐNG TOÀN DIỆN ---
if __name__ == "__main__":
    print("⏳ Đang tải Database và xây Cây 3 Tầng...")
    flat_data = load_courses_from_sql()
    
    if not flat_data:
        print("❌ Cây rỗng! Hãy kiểm tra lại Database.")
        exit()
        
    tree = build_course_tree(flat_data)
    print("✅ Cây đã sẵn sàng trên RAM!")
    
    user_gap = {
        'Docker': [1, 2], 
        'CI/CD': [2]
    }
    
    print("\n" + "="*50)
    print("🕒 LẦN 1: BẮT ĐẦU COLD START (GỌI API)")
    print("="*50)
    found_courses_1 = dfs_tree_search(tree, user_gap)
    
    print("\n" + "="*50)
    print("⚡ LẦN 2: CHẠY LẠI VỚI BỘ NHỚ ĐỆM CACHE")
    print("="*50)
    found_courses_2 = dfs_tree_search(tree, user_gap)