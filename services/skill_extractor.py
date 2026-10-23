import json
import time
# IMPORT CHUẨN CLEAN ARCHITECTURE: Lấy API Key từ Bác quản gia (config.py)
_t = time.time()
from core.config import ollama_client as client, MODEL_NAME, OLLAMA_API_KEY

VALID_LEVELS = {1, 2, 3}
# VALID_MODES = {"EXACT", "ANY"}

# def validate_extraction(parsed_list):
#     """Lọc bỏ các bản ghi không hợp lệ trước khi đưa vào dict kết quả."""
#     valid, dropped = [], 0
#     for item in parsed_list:
#         if not isinstance(item, dict):
#             dropped += 1; continue
#         name = item.get("skill_name")
#         level = item.get("level")
#         mode = item.get("match_mode", "EXACT")
#         if not name or not isinstance(name, str) or not name.strip():
#             dropped += 1; continue
#         if level not in VALID_LEVELS:
#             dropped += 1; continue
#         if mode not in VALID_MODES:
#             dropped += 1; continue
#         valid.append(item)
#     if dropped:
#         print(f"⚠️ Validation: dropped {dropped}/{len(parsed_list)} invalid records")
#     return valid

def validate_extraction(parsed_list):
    """Lọc bỏ các bản ghi không hợp lệ trước khi đưa vào dict kết quả."""
    valid, dropped = [], 0
    for item in parsed_list:
        if not isinstance(item, dict):
            dropped += 1; continue
        name = item.get("skill_name")
        level = item.get("level")
        if not name or not isinstance(name, str) or not name.strip():
            dropped += 1; continue
        if level not in VALID_LEVELS:
            dropped += 1; continue
        valid.append(item)
    if dropped:
        print(f"⚠️ Validation: dropped {dropped}/{len(parsed_list)} invalid records")
    return valid

def extract_skills_from_jd(jd_text):
    # Rào chắn bảo vệ: Tránh lỗi sập hệ thống nếu thiếu API Key
    if not jd_text or jd_text == "N/A" or not OLLAMA_API_KEY:
        return {}

    # Tiền xử lý văn bản: Chuẩn hóa các dấu câu lộn xộn
    jd_text = jd_text.replace(" / ", "/").replace(" /", "/").replace("/ ", "/")
    jd_text = jd_text.replace(", or ", " or ").replace(", and/or ", " or ")
    jd_text_safe = jd_text.replace("{", "{{").replace("}", "}}")
    
    if len(jd_text) > 8000:
        print(f"⚠️ JD bị cắt: {len(jd_text)} → 8000 ký tự")

    # Xây dựng câu lệnh Prompt cho LLM
#     prompt = f"""[SYSTEM ROLE]
# Bạn là Hệ thống Phân tích Kỹ năng (Skill Extraction Engine) lõi. Nhiệm vụ: Trích xuất Hard Tech Skills từ JD.

# Output BẮT BUỘC là MẢNG JSON:
# [
#   {{"skill_name": "Tên kỹ năng", "level": 1-3, "match_mode": "EXACT" or "ANY"}}
# ]

# [STRICT RULES]

# 1. QUY TẮC LẤY KỸ NĂNG (MỞ RỘNG TỐI ĐA):
#    - ĐƯỢC PHÉP LẤY TOÀN BỘ: Ngôn ngữ (C#, Java), Framework (Angular, ExpressJS), Database (Oracle, MongoDB), DevOps/Cloud (Docker, Kubernetes, CI/CD), Version Control (Git).
#    - ĐƯỢC PHÉP LẤY CÁC KHÁI NIỆM KỸ THUẬT: SSR, CSR, ETL, Microservices, Security, JWT, Caching.
#    - 🚫 DANH SÁCH ĐEN (TUYỆT ĐỐI CẤM LẤY): 
#      + Kỹ năng mềm: Teamwork, Communication, Problem-solving, Time management, Logical thinking, Tư duy thiết kế.
#      + Ngoại ngữ: Tiếng Anh, English, Đọc hiểu tài liệu.
#      + Kiến thức ngành/Nghiệp vụ: Banking, Finance, E-commerce, Domain knowledge.
#      + Từ khóa quá chung chung: Backend, Frontend, Database, DevOps, IT.

# 2. LUẬT "HOẶC" / NHÓM OR (ANY MODE) - TỐI QUAN TRỌNG:
#    - Nếu giữa các kỹ năng có chữ "hoặc", "hay", "or", dấu "/", dấu phẩy mang tính liệt kê lựa chọn.
#    - LỆNH BẮT BUỘC: Gộp chúng lại thành 1 chuỗi ngăn cách bằng dấu "|", set "match_mode": "ANY".
#    - VÍ DỤ 1: "C#.NET Core hoặc Java" -> "C#.NET Core|Java"
#    - VÍ DỤ 2: "GitHub/GitLab" -> "GitHub|GitLab"

# 3. LUẬT TRONG NGOẶC KÉP (PARENTHESES RULE):
#    - Nếu JD ghi Khái niệm chung đi kèm ngoặc liệt kê Tool. Ví dụ: "BI Tools (Power BI, Tableau, Google Data Studio)" hoặc "AI tools (Copilot, ChatGPT, AutoML)".
#    - LỆNH BẮT BUỘC: Lấy các công cụ bên TRONG ngoặc gộp thành nhóm ANY. BỎ QUA từ khóa chung chung bên ngoài.
#    - OUTPUT ĐÚNG: "Power BI|Tableau|Google Data Studio" (ANY).

# 4. ĐỊNH LƯỢNG LEVEL (BÁM SÁT TỪ NGỮ):
#    - [3] (Master): "Thành thạo", "Chuyên gia", "Nắm vững", "Proficient" hoặc >= 3 năm.
#    - [2] (Standard): "Có kinh nghiệm", "Hiểu biết", "Sử dụng tốt", "Làm việc với", hoặc 1-2 năm. (MẶC ĐỊNH)
#    - [1] (Basic): "Biết", "Biết cách", "Hiểu về", "Ưu tiên", "Lợi thế", "Familiarity".

# [INPUT JD CẦN XỬ LÝ]
# ---
# {jd_text_safe[:8000]}
# ---
# """

    prompt = f"""[SYSTEM ROLE]
Bạn là Hệ thống Phân tích Kỹ năng (Skill Extraction Engine) lõi. Nhiệm vụ: Trích xuất Hard Tech Skills từ JD.

Output BẮT BUỘC là MẢNG JSON:
[
  {{"skill_name": "Tên kỹ năng", "level": 1-3}}
]

[STRICT RULES]

1. QUY TẮC LẤY KỸ NĂNG (MỞ RỘNG TỐI ĐA):
   - ĐƯỢC PHÉP LẤY TOÀN BỘ: Ngôn ngữ (C#, Java), Framework (Angular, ExpressJS), Database (Oracle, MongoDB), DevOps/Cloud (Docker, Kubernetes, CI/CD), Version Control (Git).
   - ĐƯỢC PHÉP LẤY CÁC KHÁI NIỆM KỸ THUẬT: SSR, CSR, ETL, Microservices, Security, JWT, Caching.
   - 🚫 DANH SÁCH ĐEN (TUYỆT ĐỐI CẤM LẤY): 
     + Kỹ năng mềm: Teamwork, Communication, Problem-solving, Time management, Logical thinking, Tư duy thiết kế.
     + Ngoại ngữ: Tiếng Anh, English, Đọc hiểu tài liệu.
     + Kiến thức ngành/Nghiệp vụ: Banking, Finance, E-commerce, Domain knowledge.
     + Từ khóa quá chung chung: Backend, Frontend, Database, DevOps, IT.
    - ⚠️ QUY TẮC LỰA CHỌN THAY THẾ (QUAN TRỌNG): Nếu JD liệt kê nhiều lựa chọn thay thế nhau (ví dụ "thành thạo MỘT TRONG các nhóm sau: Java, Node.js, Python" hoặc "Java hoặc Node.js" hoặc "GitHub/GitLab"), hãy trích xuất MỖI công nghệ như một mục riêng biệt (không gộp chuỗi), NHƯNG gán level = 2 (Standard) cho TẤT CẢ các công nghệ trong nhóm lựa chọn đó, kể cả khi JD dùng từ "thành thạo"/"proficient" cho cả nhóm.
    - ⚠️ NGOẠI LỆ ƯU TIÊN CAO NHẤT: Nếu đoạn văn nằm trong mục "NICE TO HAVE", "ƯU TIÊN", "LỢI THẾ", hoặc "PREFERRED", LUÔN gán level = 1 (Basic) cho MỌI công nghệ trong đoạn đó, BẤT KỂ có chữ "or", dấu "/", hay liệt kê nhiều lựa chọn hay không. Quy tắc này được ưu tiên hơn quy tắc lựa chọn thay thế ở trên.

2. ĐỊNH LƯỢNG LEVEL (BÁM SÁT TỪ NGỮ):
   - [3] (Master): "Thành thạo", "Chuyên gia", "Nắm vững", "Proficient" hoặc >= 3 năm.
   - [2] (Standard): "Có kinh nghiệm", "Hiểu biết", "Sử dụng tốt", "Làm việc với", hoặc 1-2 năm. (MẶC ĐỊNH)
   - [1] (Basic): "Biết", "Biết cách", "Hiểu về", "Ưu tiên", "Lợi thế", "Familiarity".

[INPUT JD CẦN XỬ LÝ]
---
{jd_text_safe[:8000]}
---
"""

    try:
        # Gọi API Ollama sử dụng Tên Model từ config.py
        import time

        _t = time.time()
        response = client.chat(
            model=MODEL_NAME, 
            messages=[{'role': 'user', 'content': prompt}], 
            stream=False, format='json', options={'temperature': 0.0}
        )
        print(f"⏱️ LLM call took {time.time()-_t:.2f}s")
        # Làm sạch chuỗi JSON trả về
        result_text = response['message']['content'].replace('```json', '').replace('```', '').strip()
        start_idx = result_text.find('[')
        end_idx = result_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx != -1:
            parsed_list = json.loads(result_text[start_idx:end_idx])
            parsed_list = validate_extraction(parsed_list)
            result = {}
            for item in parsed_list:
                if not isinstance(item, dict):
                    continue
                name = item.get("skill_name")
                if not name:
                    continue
                result[name] = {
                    "level": item.get("level", 2),
                    # "match_mode": item.get("match_mode", "EXACT"),
                }
            return result
        return {}
    except Exception as e:
        print(f"\n❌ Lỗi bóc tách JD: {e}")
        return {}

def extract_skills_from_cv(cv_text):
    if not cv_text or cv_text == "N/A" or not OLLAMA_API_KEY:
        return {}

    cv_text = cv_text.replace(" / ", "/").replace(" /", "/").replace("/ ", "/")
    cv_text_safe = cv_text.replace("{", "{{").replace("}", "}}")

#     prompt = f"""[SYSTEM ROLE]
# Bạn là Hệ thống trích xuất kỹ năng từ CV. Nhiệm vụ: Tách ra TOÀN BỘ Hard Tech Skills từ CV kèm Level.

# Output BẮT BUỘC là MẢNG JSON:
# [
#   {{"skill_name": "Tên kỹ năng", "level": 1-3, "match_mode": "EXACT"}}
# ]

# [RULES]

# 1. QUY TẮC LẤY KỸ NĂNG (MỞ RỘNG TỐI ĐA):
#    - ĐƯỢC PHÉP LẤY TOÀN BỘ: Ngôn ngữ (C#, Java), Framework (Angular, ExpressJS), Database (Oracle, MongoDB), DevOps/Cloud (Docker, Kubernetes, CI/CD), Version Control (Git).
#    - ĐƯỢC PHÉP LẤY CÁC KHÁI NIỆM KỸ THUẬT: SSR, CSR, ETL, Microservices, Security, JWT, Caching.
#    - 🚫 DANH SÁCH ĐEN (TUYỆT ĐỐI CẤM LẤY): 
#      + Kỹ năng mềm: Teamwork, Communication, Problem-solving, Time management, Logical thinking, Tư duy thiết kế.
#      + Ngoại ngữ: Tiếng Anh, English, Đọc hiểu tài liệu.
#      + Kiến thức ngành/Nghiệp vụ: Banking, Finance, E-commerce, Domain knowledge.
#      + Từ khóa quá chung chung: Backend, Frontend, Database, DevOps, IT.

# 2. TUYỆT ĐỐI KHÔNG GỘP: Trích xuất chính xác từng công nghệ riêng biệt (EXACT).
# 3. ĐỊNH LƯỢNG LEVEL:
#    - [3]: "Thành thạo", "Chuyên gia", "Proficient", "> 3 năm".
#    - [2]: "Có kinh nghiệm", "Từng thiết kế", "Sử dụng chính", "1-2 năm".
#    - [1]: "Biết", "Chứng chỉ cơ bản", "Thường xuyên dùng" (nhưng không nói rõ mức độ).

# [INPUT CV CẦN XỬ LÝ]
# ---
# {cv_text_safe[:8000]}
# ---
# """


    prompt = f"""[SYSTEM ROLE]
Bạn là Hệ thống trích xuất kỹ năng từ CV. Nhiệm vụ: Tách ra TOÀN BỘ Hard Tech Skills từ CV kèm Level.

Output BẮT BUỘC là MẢNG JSON:
[
  {{"skill_name": "Tên kỹ năng", "level": 1-3}}
]

[RULES]

1. QUY TẮC LẤY KỸ NĂNG (MỞ RỘNG TỐI ĐA):
   - ĐƯỢC PHÉP LẤY TOÀN BỘ: Ngôn ngữ (C#, Java), Framework (Angular, ExpressJS), Database (Oracle, MongoDB), DevOps/Cloud (Docker, Kubernetes, CI/CD), Version Control (Git).
   - ĐƯỢC PHÉP LẤY CÁC KHÁI NIỆM KỸ THUẬT: SSR, CSR, ETL, Microservices, Security, JWT, Caching.
   - 🚫 DANH SÁCH ĐEN (TUYỆT ĐỐI CẤM LẤY): 
     + Kỹ năng mềm: Teamwork, Communication, Problem-solving, Time management, Logical thinking, Tư duy thiết kế.
     + Ngoại ngữ: Tiếng Anh, English, Đọc hiểu tài liệu.
     + Kiến thức ngành/Nghiệp vụ: Banking, Finance, E-commerce, Domain knowledge.
     + Từ khóa quá chung chung: Backend, Frontend, Database, DevOps, IT.
    - ⚠️ QUY TẮC LỰA CHỌN THAY THẾ (QUAN TRỌNG): Nếu JD liệt kê nhiều lựa chọn thay thế nhau (ví dụ "thành thạo MỘT TRONG các nhóm sau: Java, Node.js, Python" hoặc "Java hoặc Node.js" hoặc "GitHub/GitLab"), hãy trích xuất MỖI công nghệ như một mục riêng biệt (không gộp chuỗi), NHƯNG gán level = 2 (Standard) cho TẤT CẢ các công nghệ trong nhóm lựa chọn đó, kể cả khi JD dùng từ "thành thạo"/"proficient" cho cả nhóm.
    - ⚠️ NGOẠI LỆ ƯU TIÊN CAO NHẤT: Nếu đoạn văn nằm trong mục "NICE TO HAVE", "ƯU TIÊN", "LỢI THẾ", hoặc "PREFERRED", LUÔN gán level = 1 (Basic) cho MỌI công nghệ trong đoạn đó, BẤT KỂ có chữ "or", dấu "/", hay liệt kê nhiều lựa chọn hay không. Quy tắc này được ưu tiên hơn quy tắc lựa chọn thay thế ở trên.
2. TUYỆT ĐỐI KHÔNG GỘP: Trích xuất chính xác từng công nghệ riêng biệt.
3. ĐỊNH LƯỢNG LEVEL:
   - [3]: "Thành thạo", "Chuyên gia", "Proficient", "> 3 năm".
   - [2]: "Có kinh nghiệm", "Từng thiết kế", "Sử dụng chính", "1-2 năm".
   - [1]: "Biết", "Chứng chỉ cơ bản", "Thường xuyên dùng" (nhưng không nói rõ mức độ).

[INPUT CV CẦN XỬ LÝ]
---
{cv_text_safe[:8000]}
---
"""



    try:
        import time
        _t = time.time()
        response = client.chat(
            model=MODEL_NAME, 
            messages=[{'role': 'user', 'content': prompt}], 
            stream=False, format='json', options={'temperature': 0.0}
        )
        print(f"⏱️ LLM call took {time.time()-_t:.2f}s")
        result_text = response['message']['content'].replace('```json', '').replace('```', '').strip()
        start_idx = result_text.find('[')
        end_idx = result_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx != -1:
            parsed_list = json.loads(result_text[start_idx:end_idx])
            final_dict = {}
            for item in parsed_list:
                skill_name = item.get("skill_name") or item.get("skill")
                if skill_name:
                    # final_dict[skill_name] = {"level": item.get("level", 1), "match_mode": "EXACT"}
                    final_dict[skill_name] = {"level": item.get("level", 1)}
            return final_dict
        return {}
    except Exception as e:
        print(f"\n❌ Lỗi bóc tách CV: {e}")
        return {}   

if __name__ == "__main__":
    # ĐOẠN TEST CHẠY ĐỘC LẬP (MOCK TEST)
    test_jd = """
    VỊ TRÍ: SENIOR BACKEND ENGINEER (FINTECH)
    
    [YÊU CẦU BẮT BUỘC]
    - Tối thiểu 4 năm kinh nghiệm làm việc với: C#, .NET 8, SQL Server.
    - Thành thạo ít nhất một trong các nhóm sau:
      * Java (Spring Boot, Hibernate, Microservices)
      * Node.js / ExpressJS / NestJS
      * Python (Django, FastAPI)
    - Kỹ năng về các loại CSDL MySQL, PostgreSQL/Oracle, MongoDB, Redis.
    - Nắm vững OOP, Design Patterns và thiết kế RESTful API.
    
    [NICE TO HAVE (ƯU TIÊN)]
    - Từng làm việc với hệ thống Cloud AWS, Azure or GCP.
    - Kinh nghiệm triển khai Kubernetes và Docker là một lợi thế rất lớn.
    - CI/CD (Gitlab CI, Jenkins).
    """
    
    print("⏳ Đang bóc tách JD bằng AI...")
    jd_skills = extract_skills_from_jd(test_jd)
    print("\n🚀 KẾT QUẢ BÓC TÁCH JD (JSON):")
    print(json.dumps(jd_skills, indent=4, ensure_ascii=False))