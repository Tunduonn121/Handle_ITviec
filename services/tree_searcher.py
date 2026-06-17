import json
import re
import os
from dotenv import load_dotenv
from ollama import Client
from .tree_builder import load_courses_from_sql, build_course_tree

# =====================================================================
# KHỐI 1: KHỞI TẠO MÔI TRƯỜNG VÀ KẾT NỐI LLM
# =====================================================================
load_dotenv()
api_key = os.getenv("OLLAMA_API_KEY")
client = Client(host='https://ollama.com', headers={'Authorization': f'Bearer {api_key}'})
MODEL_NAME = 'qwen3-coder:480b-cloud'

# =====================================================================
# KHỐI 2: KHỞI TẠO BỘ NHỚ ĐỆM TỐI ƯU HÓA (MICRO-PRUNING CACHE)
# Mục đích: Lưu trữ kết quả đánh giá của LLM trên RAM để đạt độ trễ O(1).
# Khắc phục triệt để bài toán tốn tiền API và giảm thời gian chờ.
# =====================================================================
# Bộ nhớ đệm lưu vết toàn cục nằm trên RAM
MICRO_PRUNING_CACHE = {}

# =====================================================================
# KHỐI 3: HÀM ĐÁNH GIÁ VÀ LƯU CACHE (SINGLE SKILL EVALUATOR)
# Mục đích: Hỏi AI xem nhánh hiện tại (VD: "Backend") có dạy môn 
# đang xét (VD: "Docker") không. Nếu đã hỏi rồi thì móc từ Cache ra dùng.
# =====================================================================
def evaluate_single_skill_on_node(node_path: str, single_skill: str) -> bool:
    """Hỏi AI một kỹ năng duy nhất và lưu cache cứng cho kỹ năng đó tại Node này"""
    global MICRO_PRUNING_CACHE # KHAI BÁO Ở ĐẦU HÀM DUY NHẤT LÀ ĐỦ!
    
    if node_path not in MICRO_PRUNING_CACHE:
        MICRO_PRUNING_CACHE[node_path] = {}
        
    skill_clean = single_skill.lower().strip()
    
    # ⚡ NẾU ĐÃ CÓ TRONG CACHE (CACHE HIT): Trả về kết quả ngay lập tức (Tốc độ O(1))
    if skill_clean in MICRO_PRUNING_CACHE[node_path]:
        return MICRO_PRUNING_CACHE[node_path][skill_clean]
        
    # 🌐 NẾU CHƯA CÓ (CACHE MISS): Gọi LLM Qwen-480B phân tích ngữ nghĩa
    prompt = f"""Quyết định xem danh mục "{node_path}" có chứa khóa học dạy về kỹ năng "{single_skill}" hay không.
Trả lời một chữ duy nhất: YES hoặc NO.
"""
    try:
        response = client.chat(
            model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}],
            stream=False, options={'temperature': 0.0} # Nhiệt độ 0.0 để đảm bảo tính Tất định (Deterministic)
        )
        answer = response['message']['content'].strip().upper()
        result = bool(re.search(r'\bYES\b', answer))
        
        # ĐÃ XÓA DÒNG GLOBAL BỊ LỖI Ở ĐÂY
        # Lưu kết quả vừa gọi API vào Cache để lần sau không phải gọi nữa
        MICRO_PRUNING_CACHE[node_path][skill_clean] = result
        return result
    except Exception:
        # Fallback an toàn: Thà duyệt nhầm còn hơn bỏ sót khi lỗi mạng API
        return True 

# =====================================================================
# KHỐI 4: BỘ LỌC NGẮN MẠCH (SHORT-CIRCUIT EVALUATOR)
# Mục đích: Duyệt qua danh sách Lỗ hổng (Gap). Chỉ cần 1 môn khớp với 
# nhánh này là lập tức trả về True (Mở khóa nhánh) để đi sâu vào trong.
# =====================================================================
def real_llm_evaluate(node_path, gap_dict):
    """
    Hàm gác cổng cải tiến: Duyệt qua từng môn trong đống Gap của User.
    Chỉ cần 1 môn báo YES (được lưu từ trước hoặc vừa hỏi xong) là MỞ KHÓA NHÁNH.
    """
    missing_skills = list(gap_dict.keys())
    
    for skill in missing_skills:
        # Cơ chế Short-circuit: Vừa gặp 1 cái True là return cắt luồng ngay lập tức
        if evaluate_single_skill_on_node(node_path, skill):
            print(f"   🎯 [CACHE HIT] Phát hiện môn '{skill}' nằm trong nhánh [{node_path}]!")
            return True
            
    # Nếu duyệt hết các môn hổng mà AI bảo KHÔNG -> Cắt tỉa (Prune) toàn bộ nhánh này
    return False

# =====================================================================
# KHỐI 5: THUẬT TOÁN DUYỆT CÂY (DEPTH-FIRST SEARCH - DFS)
# Mục đích: Duyệt Cây Khóa học từ trên xuống dưới bằng thuật toán DFS.
# Kết hợp với LLM để quyết định đi tiếp hay "cắt tỉa" nhánh đó đi.
# =====================================================================
def dfs_tree_search(course_tree, gap_dict):
    global MICRO_PRUNING_CACHE
    print(f"\n🧠 [HỆ THỐNG] Kích thước Cache hiện tại: {len(MICRO_PRUNING_CACHE)} nhánh đã quét.")
    
    # Khởi tạo Stack cho DFS thay vì dùng Đệ quy (Giúp chống tràn bộ nhớ)
    stack = [(cat_name, cat_content) for cat_name, cat_content in course_tree.items()]
    candidate_courses = []

    print(f"\n🚀 BẮT ĐẦU DUYỆT CÂY DFS VỚI LLM PRUNING")
    print(f"🎯 Kỹ năng cần tìm ({len(gap_dict)} skills)")
    
    while stack:
        current_node_path, current_node_content = stack.pop()
        
        # Hỏi LLM xem nhánh này có đáng để đi sâu vào không
        is_relevant = real_llm_evaluate(current_node_path, gap_dict)
        
        # Nếu nhánh này tiềm năng (is_relevant == True)
        if is_relevant:
            if isinstance(current_node_content, list):
                # Đã đến Tầng cuối (Lá) -> Hốt trọn mảng Khóa học
                candidate_courses.extend(current_node_content)
            else:
                # Vẫn ở Tầng trung gian -> Đẩy các node con vào Stack để đi tiếp
                for sub_name, sub_content in current_node_content.items():
                    stack.append((f"{current_node_path} -> {sub_name}", sub_content))
                    
    # Trả về không gian tìm kiếm đã được thu hẹp tối đa
    return candidate_courses

# =====================================================================
# KHỐI 6: KIỂM THỬ ĐO LƯỜNG HIỆU NĂNG (BENCHMARKING)
# =====================================================================
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
    # Lần 1: Cache trống rỗng, bắt buộc phải gọi API tốn thời gian
    found_courses_1 = dfs_tree_search(tree, user_gap)
    
    print("\n" + "="*50)
    print("⚡ LẦN 2: CHẠY LẠI VỚI BỘ NHỚ ĐỆM CACHE")
    print("="*50)
    # Lần 2: Cache đã đầy, tốc độ trả về sẽ là tức thời O(1)
    found_courses_2 = dfs_tree_search(tree, user_gap)