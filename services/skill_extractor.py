import os
import json
from dotenv import load_dotenv
from ollama import Client

load_dotenv()
api_key = os.getenv("OLLAMA_API_KEY")

if not api_key:
    print("❌ LỖI: Sếp chưa điền OLLAMA_API_KEY vào file .env kìa!")

client = Client(
    host='https://ollama.com',
    headers={'Authorization': f'Bearer {api_key}'}
)

def extract_skills_from_jd(jd_text):
    if not jd_text or jd_text == "N/A" or not api_key:
        return {}

    jd_text = jd_text.replace(" / ", "/").replace(" /", "/").replace("/ ", "/")
    jd_text = jd_text.replace(", or ", " or ").replace(", and/or ", " or ")
    jd_text_safe = jd_text.replace("{", "{{").replace("}", "}}")
    
    if len(jd_text) > 8000:
        print(f"⚠️ JD bị cắt: {len(jd_text)} → 8000 ký tự")

    prompt = f"""[SYSTEM ROLE]
Bạn là Hệ thống Phân tích Kỹ năng (Skill Extraction Engine) lõi. Nhiệm vụ: Trích xuất Hard Tech Skills từ JD.

Output BẮT BUỘC là MẢNG JSON:
[
  {{"skill_name": "Tên kỹ năng", "level": 1-3, "match_mode": "EXACT" or "ANY"}}
]

[STRICT RULES]

1. QUY TẮC LẤY KỸ NĂNG (MỞ RỘNG TỐI ĐA):
   - ĐƯỢC PHÉP LẤY TOÀN BỘ: Ngôn ngữ (C#, Java), Framework (Angular, ExpressJS), Database (Oracle, MongoDB), DevOps/Cloud (Docker, Kubernetes, CI/CD, OpenShift), Version Control (Git, GitHub, GitLab).
   - ĐƯỢC PHÉP LẤY CÁC KHÁI NIỆM KỸ THUẬT: SSR, CSR, ETL, Data Lake, Microservices, Security, JWT, OAuth 2, Caching, Load balancing.
   - CHỈ CẤM LẤY: Kỹ năng mềm (Teamwork, Communication) và từ chung chung (Backend, Frontend, Database, DevOps).

2. LUẬT "HOẶC" / NHÓM OR (ANY MODE) - TỐI QUAN TRỌNG:
   - Nếu giữa các kỹ năng có chữ "hoặc", "hay", "or", dấu "/", dấu phẩy mang tính liệt kê lựa chọn.
   - LỆNH BẮT BUỘC: Gộp chúng lại thành 1 chuỗi ngăn cách bằng dấu "|", set "match_mode": "ANY".
   - VÍ DỤ 1: "C#.NET Core hoặc Java" -> "C#.NET Core|Java"
   - VÍ DỤ 2: "GitHub/GitLab" -> "GitHub|GitLab"

3. LUẬT TRONG NGOẶC KÉP (PARENTHESES RULE):
   - Nếu JD ghi Khái niệm chung đi kèm ngoặc liệt kê Tool. Ví dụ: "BI Tools (Power BI, Tableau, Google Data Studio)" hoặc "AI tools (Copilot, ChatGPT, AutoML)".
   - LỆNH BẮT BUỘC: Lấy các công cụ bên TRONG ngoặc gộp thành nhóm ANY. BỎ QUA từ khóa chung chung bên ngoài.
   - OUTPUT ĐÚNG: "Power BI|Tableau|Google Data Studio" (ANY).

4. ĐỊNH LƯỢNG LEVEL (BÁM SÁT TỪ NGỮ):
   - [3] (Master): "Thành thạo", "Chuyên gia", "Nắm vững", hoặc >= 3 năm.
   - [2] (Standard): "Có kinh nghiệm", "Hiểu biết", "Sử dụng tốt", "Làm việc với", hoặc 1-2 năm. (MẶC ĐỊNH)
   - [1] (Basic): "Biết", "Biết cách", "Hiểu về", "Ưu tiên", "Lợi thế", "Familiarity".

[INPUT JD CẦN XỬ LÝ]
---
{jd_text_safe[:8000]}
---
"""
    try:
        response = client.chat(
            model='qwen3-coder:480b-cloud',
            messages=[{'role': 'user', 'content': prompt}], 
            stream=False, format='json', options={'temperature': 0.0}
        )
        
        result_text = response['message']['content'].replace('```json', '').replace('```', '').strip()
        start_idx = result_text.find('[')
        end_idx = result_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx != -1:
            parsed_list = json.loads(result_text[start_idx:end_idx])
            return {item["skill_name"]: {"level": item["level"], "match_mode": item["match_mode"]} for item in parsed_list}
        return {}
    except Exception as e:
        print(f"\n❌ Lỗi bóc tách JD: {e}")
        return {}

def extract_skills_from_cv(cv_text):
    if not cv_text or cv_text == "N/A" or not api_key:
        return {}

    cv_text = cv_text.replace(" / ", "/").replace(" /", "/").replace("/ ", "/")
    cv_text_safe = cv_text.replace("{", "{{").replace("}", "}}")

    prompt = f"""[SYSTEM ROLE]
Bạn là Hệ thống trích xuất kỹ năng từ CV. Nhiệm vụ: Tách ra TOÀN BỘ Hard Tech Skills từ CV kèm Level.

Output BẮT BUỘC là MẢNG JSON:
[
  {{"skill_name": "Tên kỹ năng", "level": 1-3, "match_mode": "EXACT"}}
]

[RULES]
1. LẤY SẠCH, KHÔNG BỎ SÓT: Lấy toàn bộ ngôn ngữ, Framework, Database, Khái niệm (RESTful API, SSR...), Tool (Docker, Gitlab, MySQL...). KHÔNG LẤY soft skills.
2. TUYỆT ĐỐI KHÔNG GỘP: Trích xuất chính xác từng công nghệ riêng biệt (EXACT).
3. ĐỊNH LƯỢNG LEVEL:
   - [3]: "Thành thạo", "Chuyên gia", "> 3 năm".
   - [2]: "Có kinh nghiệm", "Từng thiết kế", "Sử dụng chính", "1-2 năm".
   - [1]: "Biết", "Chứng chỉ cơ bản", "Thường xuyên dùng" (nhưng không nói rõ mức độ).

[INPUT CV CẦN XỬ LÝ]
---
{cv_text_safe[:8000]}
---
"""
    try:
        response = client.chat(
            model='qwen3-coder:480b-cloud',
            messages=[{'role': 'user', 'content': prompt}], 
            stream=False, format='json', options={'temperature': 0.0}
        )
        
        result_text = response['message']['content'].replace('```json', '').replace('```', '').strip()
        start_idx = result_text.find('[')
        end_idx = result_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx != -1:
            parsed_list = json.loads(result_text[start_idx:end_idx])
            final_dict = {}
            for item in parsed_list:
                skill_name = item.get("skill_name") or item.get("skill")
                if skill_name:
                    final_dict[skill_name] = {"level": item.get("level", 1), "match_mode": "EXACT"}
            return final_dict
        return {}
    except Exception as e:
        print(f"\n❌ Lỗi bóc tách CV: {e}")
        return {}   

if __name__ == "__main__":
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
    
    print("⏳ Đang bóc tách JD...")
    jd_skills = extract_skills_from_jd(test_jd)
    print("\n🚀 KẾT QUẢ BÓC TÁCH JD (JSON):")
    print(json.dumps(jd_skills, indent=4, ensure_ascii=False))