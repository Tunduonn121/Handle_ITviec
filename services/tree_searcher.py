import json
import re
import os
from dotenv import load_dotenv
from ollama import Client
from .tree_builder import load_courses_from_sql, build_course_tree

# ==========================================
# CẤU HÌNH AI CHO NHIỆM VỤ CẮT TỈA (PRUNING)
# ==========================================
# Dùng con 1.5b hoặc 3b để máy Sếp chạy mượt, không bị ngộp RAM
load_dotenv()

# Load biến môi trường từ file .env
load_dotenv()
api_key = os.getenv("OLLAMA_API_KEY")

if not api_key:
    print("❌ LỖI: Sếp chưa điền OLLAMA_API_KEY vào file .env kìa!")

# Khởi tạo Client trỏ thẳng lên Máy chủ Đám mây của Ollama
client = Client(
    host='https://ollama.com',
    headers={'Authorization': f'Bearer {api_key}'}
)
# Chốt chặn an toàn: Báo lỗi ngay nếu chưa lấy được Key


MODEL_NAME = 'qwen3-coder:480b-cloud'
def real_llm_evaluate(node_path, gap_dict):
    """
    Sử dụng LLM THẬT để suy luận ngữ nghĩa xem nhánh này có chứa kỹ năng đang thiếu không.
    """
    # Lấy danh sách tên kỹ năng User đang thiếu (VD: ['Java', 'Spring Boot'])
    missing_skills = list(gap_dict.keys())
    
    prompt = f"""Bạn là một chuyên gia Hệ thống gợi ý khóa học IT.
Nhiệm vụ: Quyết định xem có nên tìm kiếm khóa học trong một danh mục cụ thể hay không.

- Kỹ năng người dùng đang cần học (CHỈ CẦN KHỚP 1 KỸ NĂNG LÀ ĐẠT): {missing_skills}
- Nhánh danh mục bạn đang xét: "{node_path}"

Câu hỏi: Nhánh danh mục "{node_path}" này có mối liên hệ ngữ nghĩa NÀO với BẤT KỲ kỹ năng nào trong danh sách trên không? (Ví dụ: Nhánh 'DevOps' sẽ chứa 'Docker' hoặc 'CI/CD').
Trả lời NGẮN GỌN BẮT BUỘC bằng 1 chữ duy nhất: YES hoặc NO. Tuyệt đối không giải thích.
"""

    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            stream=False,
            options={'temperature': 0.0} # Ép AI trả lời máy móc, dứt khoát 100%
        )
        answer = response['message']['content'].strip().upper()
        
        # Dùng Regex bắt chữ YES để lọc rác nếu AI lỡ lảm nhảm
        if re.search(r'\bYES\b', answer):
            return True
        return False
        
    except Exception as e:
        print(f"⚠️ Lỗi AI khi hỏi nhánh '{node_path}': {e}. [Mặc định: GIỮ LẠI ĐỂ AN TOÀN]")
        return True # Fallback: Thà duyệt nhầm còn hơn bỏ sót khóa học của User

def dfs_tree_search(course_tree, gap_dict):
    """
    Duyệt Cây bằng Stack + LLM Pruning (Chuẩn bài báo LLMTreeRec)
    """
    stack = []
    candidate_courses = []

    # 1. Khởi tạo: Đẩy Tầng 1 vào Stack (kèm đường dẫn để AI hiểu Context)
    for cat_name, cat_content in course_tree.items():
        stack.append((cat_name, cat_content))

    print(f"\n🚀 BẮT ĐẦU DUYỆT CÂY DFS VỚI LLM PRUNING")
    print(f"🎯 Kỹ năng cần tìm (Gap): {list(gap_dict.keys())}")
    print("-" * 60)

    # 2. Vòng lặp DFS
    while stack:
        current_node_path, current_node_content = stack.pop()
        
        # 3. Gọi LLM "Gác cổng" đánh giá Nhánh
        print(f"🔍 AI đang 'soi' nhánh: [{current_node_path}]...")
        is_relevant = real_llm_evaluate(current_node_path, gap_dict)
        
        if is_relevant:
            print(f"   🟢 [MỞ KHÓA] Nhánh '{current_node_path}' có tiềm năng!")
            
            if isinstance(current_node_content, list):
                # 🔓 ĐÃ CHẠM TỚI ĐÁY CÂY (Tầng 3 - Node Lá): Hốt hết khóa học
                candidate_courses.extend(current_node_content)
                print(f"      => 📥 Đã thu hoạch {len(current_node_content)} khóa học từ nhánh này.")
            else:
                # 🌿 ĐANG Ở TẦNG NHÁNH: Đẩy các Node con vào Stack để đi sâu xuống
                for sub_name, sub_content in current_node_content.items():
                    # Nối chuỗi để AI hiểu ngữ cảnh (VD: "Backend -> Java Ecosystem")
                    detailed_path = f"{current_node_path} -> {sub_name}"
                    stack.append((detailed_path, sub_content))
        else:
            print(f"   🔴 [CẮT TỈA] Đã chém bỏ nhánh '{current_node_path}' - Không liên quan!")

    print("-" * 60)
    return candidate_courses

# --- TEST HỆ THỐNG TOÀN DIỆN ---
if __name__ == "__main__":
    # Bước A: Kéo 4050 khóa học từ DB lên và Xây Cây thực tế
    print("⏳ Đang tải Database và xây Cây 3 Tầng...")
    flat_data = load_courses_from_sql()
    
    if not flat_data:
        print("❌ Cây rỗng! Hãy kiểm tra lại Database.")
        exit()
        
    tree = build_course_tree(flat_data)
    print("✅ Cây đã sẵn sàng trên RAM!")
    
    # Bước B: Giả lập Skill Gap của User (Lấy từ bài toán Matching JD - CV)
    # Ví dụ: User ứng tuyển DevOps nhưng CV chưa biết Docker và CI/CD
    user_gap = {
        'Docker': [1, 2], 
        'CI/CD': [2]
    }
    
    # Bước C: Thả chó... à nhầm, thả AI đi lùng sục khóa học
    found_courses = dfs_tree_search(tree, user_gap)
    
    # Bước D: Tổng kết chiến lợi phẩm
    print(f"\n🎉 TỔNG KẾT: THU HOẠCH ĐƯỢC {len(found_courses)} KHÓA HỌC ỨNG VIÊN!")
    
    if found_courses:
        print("\n📚 3 KHÓA HỌC TIÊU BIỂU TÌM THẤY:")
        # In đẹp 3 khóa học đầu tiên để nghiệm thu
        for i, c in enumerate(found_courses[:3], 1):
            skills_str = ", ".join(c['target_skills'])[:80] + "..." # Rút gọn string cho đỡ rối
            print(f" {i}. [{c['course_id']}] {c['title']} \n    (Level: {c['level']} | Skills: {skills_str})\n")
    else:
        print("⚠️ Không tìm thấy khóa học nào lấp được Gap này.")