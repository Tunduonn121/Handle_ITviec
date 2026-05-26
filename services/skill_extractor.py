import os
import json
from dotenv import load_dotenv
from ollama import Client

# Load biến môi trường từ file .env
load_dotenv()
api_key = os.getenv("OLLAMA_API_KEY")

if not api_key:
    print("❌ LỖI: Sếp chưa điền OLLAMA_API_KEY vào file .env kìa!")

# Khởi tạo Client
client = Client(
    host='https://ollama.com',
    headers={'Authorization': f'Bearer {api_key}'}
)

def extract_skills_from_jd(jd_text):
    if not jd_text or jd_text == "N/A" or not api_key:
        return {}

    # Pre-processing
    jd_text = jd_text.replace(" / ", "/").replace(" /", "/").replace("/ ", "/")
    jd_text = jd_text.replace(", or ", " or ").replace(", and/or ", " or ")
    jd_text_safe = jd_text.replace("{", "{{").replace("}", "}}")
    
    # Mở rộng giới hạn cho CV/JD dài
    if len(jd_text) > 8000:
        print(f"⚠️ JD bị cắt: {len(jd_text)} → 8000 ký tự")

    prompt = f"""[SYSTEM ROLE]
Bạn là Hệ thống Phân tích Kỹ năng (Skill Extraction Engine) lõi.
Nhiệm vụ: Trích xuất Hard Tech Skills cốt lõi nhất từ JD.

Output BẮT BUỘC là MẢNG JSON:
[
  {{"skill_name": "Tên kỹ năng", "level": 1-3, "match_mode": "EXACT" or "ANY"}}
]

[STRICT RULES]

1. QUY TẮC CHUẨN HÓA TÊN (ALIAS NORMALIZATION):
   Nếu gặp các từ sau, BẮT BUỘC chuyển về dạng Chuẩn (Bên phải dấu mũi tên):
   - React.js, React -> ReactJS
   - Vue.js, Vue -> VueJS
   - Node.js, Node -> NodeJS
   - C sharp -> C#
   - C plus plus -> C++
   - Python 3 -> Python
   - Golang, Go programming -> Go
   - AWS, Amazon Web Services -> AWS
   - GCP, Google Cloud -> GCP
   - ML, Machine Learning -> Machine Learning
   - AI, Artificial Intelligence -> Artificial Intelligence

2. ĐƯỢC PHÉP LẤY (CORE SKILLS TƯƠNG THÍCH VỚI 11 DOMAIN IT):
   - Ngôn ngữ & Framework (Java, Python, C#, ReactJS, NodeJS...)
   - Database & Cache (SQL, MySQL, MongoDB, Redis, PostgreSQL...)
   - Cloud & DevOps (AWS, Azure, Docker, Kubernetes, CI/CD...)
   - Mobile (iOS, Android, Flutter, React Native)
   - Core CS (Data Structures, Algorithms, OOP, System Design, Microservices, REST API)
   - Cybersecurity (Ethical Hacking, Penetration Testing, Cryptography, Network Security)

3. BLACKLIST (CẤM LẤY - VI PHẠM SẼ BỊ HỦY BỎ):
   - Kỹ năng mềm (Communication, Teamwork, English)
   - Văn hóa quản lý dự án (Agile, Scrum, Jira, Kanban)
   - Chức danh/Môi trường (DevOps, Fintech, Proptech, Backend, Frontend) -> Chỉ lấy ngôn ngữ, không lấy chữ Backend/Frontend.
   - Tool Thô (GitHub Actions, Jenkins, Terraform, Ansible, Postman, npm) -> Bỏ hẳn.

4. LUẬT NHÓM OR (ANY MODE) - TỐI QUAN TRỌNG:
   - CASE 1 (OR Cùng dòng): Nếu có "/", "or", "hoặc" (VD: "Java/Python/Go"). BẮT BUỘC gộp thành "Java|Python|Go", "match_mode": "ANY".
   - CASE 2 (BULLET LỒNG - CHỌN 1 TRONG NHIỀU): Nếu JD ghi câu dẫn "Ít nhất một trong...", "Một trong các ngôn ngữ sau..." kèm theo các bullet bên dưới.
     -> LỆNH TUYỆT ĐỐI: Phải gộp TOÀN BỘ các gạch đầu dòng đó thành MỘT CHUỖI DUY NHẤT, nối với nhau bằng dấu "|", KHÔNG ĐƯỢC tách thành các JSON object riêng.
     -> VÍ DỤ: 
        Ít nhất 1 trong các nhóm:
        * Java (Spring, Hibernate)
        * Node.js / Express
     -> OUTPUT ĐÚNG 100%: 
        {{"Java (Spring, Hibernate)|NodeJS|Express": {{"level": 3, "match_mode": "ANY"}}}}
        
5. QUYỀN PHỦ QUYẾT LEVEL 1 (ABSOLUTE OVERRIDE):
   - Nếu kỹ năng nằm dưới tiêu đề "Ưu tiên", "Nice to have", "Preferred" HOẶC có từ "là lợi thế", "is a plus". BẮT BUỘC Ép về Level 1.

6. ĐỊNH LƯỢNG LEVEL MẶC ĐỊNH:
   - [3]: "Thành thạo", "Strong proficiency", "Master", hoặc >= 3 năm.
   - [2]: "Có kinh nghiệm", "Experience with", hoặc 1-2 năm. (Đây là mức mặc định).
   - [1]: "Biết", "Familiarity", "Cơ bản".

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
    
    if len(cv_text) > 8000:
        print(f"⚠️ CV bị cắt: {len(cv_text)} → 8000 ký tự")

    prompt = f"""[SYSTEM ROLE]
Bạn là Hệ thống trích xuất kỹ năng từ CV.
Nhiệm vụ: Tách ra các Hard Tech Skills từ CV kèm Level dự đoán.

Output BẮT BUỘC là MẢNG JSON:
[
  {{"skill_name": "Tên kỹ năng", "level": 1-3, "match_mode": "EXACT"}}
]

[RULES]
1. CV CHỈ LẤY EXACT (Không gộp OR).
2. Áp dụng quy tắc CHUẨN HÓA TÊN (Ví dụ: React.js -> ReactJS, Node.js -> NodeJS, Golang -> Go).
3. KHÔNG lấy Tool thô (Jenkins, Docker Hub, npm). KHÔNG lấy Soft Skills. ĐƯỢC PHÉP lấy Core CS (OOP, System Design) và CyberSec.
4. ĐỊNH LƯỢNG LEVEL:
   - [3]: "Thành thạo", "Master", hoặc ghi chú >= 3 năm.
   - [2]: "Có kinh nghiệm", "Familiar", hoặc 1-2 năm.
   - [1]: Dự án môn học, học qua chứng chỉ, nhắc lướt qua.

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