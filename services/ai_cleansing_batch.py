import json
import re

# IMPORT TỪ FILE ALIASES ĐỂ DÙNG CHUNG MỘT NGUỒN CHÂN LÝ (SINGLE SOURCE OF TRUTH)
from services.aliases import GLOBAL_ALIAS_MAP

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN
# ==========================================
RAW_FILE = r"data\raw_courses_massive.json"
CLEAN_FILE = r"data\clean_courses.json"

# 1. Danh sách đen (Exact Match): Bắt đúng từ (Word Boundary) để không chém nhầm
# Bổ sung: Các phần mềm gõ code (IDE/Editor), Công cụ chat/văn phòng, và phương pháp quản lý chung
BLACKLIST_EXACT = {
    # Nhóm IDE / Text Editors (Chỉ là công cụ gõ code, không phải kỹ năng lõi)
    'vscode', 'visual studio', 'eclipse', 'intellij', 'pycharm', 'webstorm', 
    'phpstorm', 'netbeans', 'atom', 'sublime text', 'notepad++', 'vim', 'emacs', 'xcode',
    
    # Nhóm Build tools & Package managers (Quá nhỏ để tính là một skill lớn)
    'maven', 'gradle', 'npm', 'yarn', 'webpack', 'gulp', 'grunt', 'composer',
    
    # Nhóm Giao tiếp / Quản lý dự án / Chat văn phòng
    'jira', 'slack', 'trello', 'confluence', 'asana', 'notion', 'monday', 'monday.com',
    'microsoft teams', 'zoom', 'skype', 'discord', 'google meet',
    
    # Nhóm Thuật ngữ chung chung / Phương pháp luận
    'bash', 'powershell', 'agile', 'scrum', 'kanban', 'waterfall', 'lean', 
    'qa', 'qc', 'debugging', 'debug', 'testing', 'deploy'
}

# 2. Danh sách đen (Substring): Bắt cụm từ chứa các từ chung chung vô nghĩa
# Bổ sung: Các câu từ Marketing của Udemy/Coursera, Soft-skills, và từ khóa định hướng
BLACKLIST_SUBSTRING = [
    # 🗑️ Rác Marketing giáo dục (Coursera / Udemy fluff)
    'from scratch', 'zero to hero', 'for beginners', 'for dummies', 'masterclass', 
    'bootcamp', 'crash course', 'step by step', 'complete guide', 'deep dive', 
    'getting started', 'tutorial', 'hands on', 'hands-on', 'tips and tricks', 
    'interview prep', 'exam prep', 'certification', 'course', 'module', 'learn',
    
    # 🗑️ Rác Soft-skills (Kỹ năng mềm)
    'communication', 'leadership', 'teamwork', 'problem solving', 'critical thinking', 
    'time management', 'presentation', 'writing', 'speaking', 'collaboration',
    
    # 🗑️ Rác Thuật ngữ học thuật / Đại cương
    'introduction', 'basics', 'fundamentals', 'advanced', 'concepts', 'understanding', 
    'overview', 'principles', 'best practices', 'how to', 'what is',
    
    # 🗑️ Rác Ngành nghề chung chung
    'software engineering', 'software development', 'web development', 'app development', 
    'computer science', 'programming languages', 'coding', 'developer', 'engineer', 
    'architect', 'career', 'resume', 'portfolio',
    
    # 🗑️ Rác Kỹ thuật chung chung
    'linux command', 'command line', 'maintainability', 'testability', 'reliability', 
    'design strategies', 'project management', 'quality assurance', 'troubleshooting', 
    'optimization', 'architecture patterns', 'features', 'update', 'new in'
]

def clean_skill_local(skill):
    """Hàm dọn rác bọc thép (Xử lý theo thứ tự tuyệt đối)"""
    s = skill.lower().strip()
    
    if not s or len(s) < 2: 
        return None

    # ==========================================
    # BƯỚC 1: MAPPING BÌNH THƯỜNG (Sử dụng từ điển chung của toàn hệ thống)
    # ==========================================
    for key, val in GLOBAL_ALIAS_MAP.items():
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, s):
            return val

    # ==========================================
    # BƯỚC 2: BLACKLIST BẮT CHÍNH XÁC TỪ
    # ==========================================
    for bad in BLACKLIST_EXACT:
        pattern = r'\b' + re.escape(bad) + r'\b'
        if re.search(pattern, s):
            return None

    # ==========================================
    # BƯỚC 3: BLACKLIST CHUỖI VÔ NGHĨA
    # ==========================================
    for trash in BLACKLIST_SUBSTRING:
        if trash in s:
            return None
            
    # Đã XÓA đoạn chém oan các chữ chứa "programming" hay "development" ở đây.

    # ==========================================
    # BƯỚC 4: LÀM SẠCH KÝ TỰ 
    # ==========================================
    s = re.sub(r'[^a-zA-Z0-9\+\#\-\.\/]', ' ', s) 
    s = ' '.join(s.split()) 
    
    if len(s) < 2: 
        return None
        
    return s.title()

def run_test_cases():
    """Hàm test thử nghiệm các ca khó để Sếp kiểm chứng logic"""
    print("=" * 80)
    print("🧪 BÀN THỬ NGHIỆM: KIỂM TRA LOGIC LỌC RÁC KỸ NĂNG")
    print("=" * 80)
    
    # Tập hợp các ca từ sạch đến siêu bẩn
    test_cases = [
        "react.js",                        # Chuẩn hóa -> ReactJS
        "core java programming",           # Chuẩn hóa -> Java
        "c# programming",                  # Chuẩn hóa -> C#
        "front-end web development",       # Chuẩn hóa -> Frontend
        "learn python 3 from scratch",     # Có chữ 'learn' -> BỊ CHÉM
        "best practices in c++",           # Có chữ 'best practices' -> BỊ CHÉM
        "introduction to agile",           # Có 'introduction' & 'agile' -> BỊ CHÉM
        "vscode extensions",               # Có 'vscode' (Blacklist exact) -> BỊ CHÉM
        "docker & kubernetes!!!",          # Xóa ký tự lạ, giữ lại chữ
        "  node.js  "                      # Cắt khoảng trắng thừa -> NodeJS
    ]
    
    for raw in test_cases:
        cleaned = clean_skill_local(raw)
        if cleaned:
            print(f" 🟢 Bẩn: '{raw:<30}' ➡️  Sạch: {cleaned}")
        else:
            print(f" 🔴 Bẩn: '{raw:<30}' ➡️  [BỊ TIÊU DIỆT TỪ VÒNG GỬI XE]")
            
    print("=" * 80)


def process_real_files():
    """Hàm chạy ETL thực tế trên file json"""
    print("\n🚀 BẮT ĐẦU DỌN RÁC BẰNG PYTHON TRÊN FILE THẬT (OFFLINE - SIÊU TỐC)")
    try:
        with open(RAW_FILE, 'r', encoding='utf-8') as f:
            courses = json.load(f)
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file {RAW_FILE}")
        return

    clean_courses = []
    
    for course in courses:
        raw_skills = course.get("target_skills", [])
        mapped_skills = set()
        
        for raw_skill in raw_skills:
            cleaned = clean_skill_local(raw_skill)
            if cleaned: 
                mapped_skills.add(cleaned)
        
        if mapped_skills:
            course["target_skills"] = list(mapped_skills)
            clean_courses.append(course)

    with open(CLEAN_FILE, 'w', encoding='utf-8') as f:
        json.dump(clean_courses, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 HOÀN TẤT TRONG NHÁY MẮT! Đã giữ lại {len(clean_courses)}/{len(courses)} khóa học cực sạch.")
    print(f"📁 Dữ liệu đã sẵn sàng tại: {CLEAN_FILE}")
    print("👉 SẾP CÓ THỂ CHẠY FILE 'import_courses_to_sql.py' ĐƯỢC RỒI!")


if __name__ == "__main__":
    # 1. Chạy Demo để Sếp xem mắt trước
    run_test_cases()
    
    # 2. Hỏi ý kiến Sếp xem có muốn quất luôn file thật không
    user_choice = input("\n[?] Sếp đã ưng ý với kết quả Test chưa? Gõ 'y' để dọn rác file thật, 'n' để thoát: ")
    if user_choice.lower() == 'y':
        process_real_files()
    else:
        print("🛑 Đã hủy quá trình chạy file thật.")