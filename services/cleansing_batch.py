import re
import sys
import argparse
from services.aliases import GLOBAL_ALIAS_MAP

# Sắp key theo độ dài giảm dần: key cụ thể (dài) được ưu tiên khớp trước
ALIAS_KEYS_SORTED = sorted(GLOBAL_ALIAS_MAP.keys(), key=len, reverse=True)

# Tên hiển thị chuẩn cho các giá trị canonical hay bị xấu khi .title()
DISPLAY_OVERRIDES = {
    "c#": "C#", ".net": ".NET", "nodejs": "Node.js", "reactjs": "ReactJS",
    "vuejs": "Vue.js", "javascript": "JavaScript", "typescript": "TypeScript",
    "jpa": "JPA", "sql": "SQL", "sql server": "SQL Server", "ci/cd": "CI/CD",
    "aws": "AWS", "gcp": "GCP", "rest api": "REST API", "oop": "OOP",
    "jwt": "JWT", "etl": "ETL", "nlp": "NLP", "go": "Go",
}

def to_display(canonical: str) -> str:
    """Chuẩn hóa tên hiển thị, áp ĐỒNG NHẤT cho cả skill alias lẫn không-alias."""
    c = canonical.lower().strip()
    if c in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[c]
    return canonical.title()

def _word_boundary_hit(token: str, text: str) -> bool:
    """Khớp token như một từ/cụm ĐỘC LẬP (không cắt giữa từ). An toàn cho c#, .net..."""
    pat = r'(?<![a-z0-9])' + re.escape(token) + r'(?![a-z0-9])'
    return re.search(pat, text) is not None

def map_alias(s: str):
    """Trả canonical nếu map được, ngược lại None. Bằng-nhau trước, key dài trước."""
    if s in GLOBAL_ALIAS_MAP:
        return GLOBAL_ALIAS_MAP[s]
    for key in ALIAS_KEYS_SORTED:
        if _word_boundary_hit(key, s):
            return GLOBAL_ALIAS_MAP[key]
    return None
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
    """Dọn rác theo thứ tự an toàn: chuẩn hóa -> alias chính xác -> blacklist (word-boundary) -> alias fuzzy -> dọn ký tự."""
    s = skill.lower().strip()
    s = re.sub(r'\([^)]*\)', '', s).strip()   # bỏ đuôi mô tả: "Docker (Software)" -> "docker"
    if not s or len(s) < 2:
        return None
    if not s or len(s) < 2:
        return None

    # BƯỚC 1: ALIAS KHỚP BẰNG-NHAU TOÀN CHUỖI (chắc chắn là core -> giữ ngay)
    if s in GLOBAL_ALIAS_MAP:
        return to_display(GLOBAL_ALIAS_MAP[s])

    # BƯỚC 2: BLACKLIST EXACT (word-boundary - giữ nguyên ý định cũ)
    for bad in BLACKLIST_EXACT:
        if _word_boundary_hit(bad, s):
            return None

    # BƯỚC 3: BLACKLIST CỤM RÁC -> ĐỔI SANG WORD-BOUNDARY (hết giết "Engineering","Architecture")
    for trash in BLACKLIST_SUBSTRING:
        if _word_boundary_hit(trash, s):
            return None

    # BƯỚC 4: ALIAS FUZZY (key dài trước) cho các cụm ghép như "core java programming"
    mapped = map_alias(s)
    if mapped is not None:
        return to_display(mapped)

    # BƯỚC 5: LÀM SẠCH KÝ TỰ rồi trả về với casing chuẩn
    s = re.sub(r'[^a-zA-Z0-9\+\#\-\.\/]', ' ', s)
    s = ' '.join(s.split())
    if len(s) < 2:
        return None
    return to_display(s)

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
        "  node.js  ",                     # Cắt khoảng trắng thừa -> NodeJS"microsoft sql server",   # PHẢI ra: SQL Server (cũ ra "sql")
        "spring data jpa",                 # PHẢI ra: JPA       (cũ ra "Spring Boot")
        "data engineering",                # PHẢI GIỮ           (cũ bị 'engineer' chém)
        "software architecture",           # PHẢI GIỮ           (cũ bị 'architect' chém)
        "core java programming",           # PHẢI ra: Java
        "react.js",                        # PHẢI ra: ReactJS
        "teamwork",                        # PHẢI bị chém (soft skill)   
        "vscode extensions",               # PHẢI bị chém (IDE rác)
        "  node.js  ", 
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
    parser = argparse.ArgumentParser(description="Cleansing pipeline (offline).")
    parser.add_argument("--yes", action="store_true", help="Chạy thẳng file thật, không hỏi.")
    parser.add_argument("--test", action="store_true", help="Chỉ chạy test logic lọc.")
    args = parser.parse_args()

    run_test_cases()
    if args.test:
        sys.exit(0)

    if args.yes:
        process_real_files()
    else:
        choice = input("\n[?] Gõ 'y' để dọn file thật, Enter để thoát: ")
        if choice.lower() == 'y':
            process_real_files()
        else:
            print("🛑 Đã hủy.")