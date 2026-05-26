import json
import re

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN
# ==========================================
RAW_FILE = r"data\raw_courses_massive.json"
CLEAN_FILE = r"data\clean_courses.json"

# 1. Danh sách đen: Bắt đúng từ (Word Boundary) để không chém nhầm
BLACKLIST_EXACT = {
    'vscode', 'visual studio', 'eclipse', 'intellij',
    'maven', 'gradle', 'npm', 'yarn', 'webpack', 'jira', 'slack', 'trello', 'confluence',
    'bash', 'powershell', 'agile', 'scrum', 'debugging'
}

# Danh sách đen: Bắt cụm từ (Substring) chứa các từ chung chung vô nghĩa
BLACKLIST_SUBSTRING = [
    'linux command', 'command line', 'maintainability', 'testability', 'reliability', 
    'design strategies', 'best practices', 'principles', 'software engineering', 
    'computer science', 'communication', 'leadership', 'teamwork', 'problem solving', 
    'critical thinking', 'project management', 'quality assurance', 'troubleshooting', 
    'optimization', 'introduction', 'basics', 'fundamentals', 'advanced', 'concepts', 
    'how to', 'course', 'module', 'learn'
]

# 2. Từ điển map: Chuẩn hóa tên (Alias)
MAPPING = {
    # --- Backend & Ngôn ngữ ---
    'java programming': 'Java', 'core java': 'Java', 'java se': 'Java', 'java ee': 'Java',
    'python programming': 'Python', 'python 3': 'Python', 'interactive python': 'Python',
    'c++ programming': 'C++', 'c plus plus': 'C++', 'modern c++': 'C++',
    'c# programming': 'C#', 'c sharp': 'C#',
    'node.js': 'NodeJS', 'nodejs': 'NodeJS', 'express.js': 'ExpressJS', 'express': 'ExpressJS',
    'golang': 'Go', 'go programming': 'Go',
    'ruby on rails': 'Ruby on Rails', 'rails': 'Ruby on Rails',
    'php programming': 'PHP', 'laravel framework': 'Laravel',
    'application programming interface': 'API', 'restful api': 'REST API', 'rest apis': 'REST API', 'web api': 'REST API',
    'object oriented programming': 'OOP', 'object-oriented': 'OOP', 'oop concepts': 'OOP',
    'microservice architecture': 'Microservices', 'microservices': 'Microservices',
    
    # --- Frontend ---
    'react.js': 'ReactJS', 'reactjs': 'ReactJS', 'react native': 'React Native',
    'vue.js': 'VueJS', 'vuejs': 'VueJS', 'vue': 'VueJS',
    'angularjs': 'Angular', 'angular.js': 'Angular',
    'javascript programming': 'JavaScript', 'js': 'JavaScript', 'ecmascript': 'JavaScript',
    'typescript programming': 'TypeScript', 'ts': 'TypeScript',
    'html5': 'HTML', 'css3': 'CSS', 'cascading style sheets': 'CSS',
    'front-end web development': 'Frontend', 'front end': 'Frontend',
    
    # --- Database & Data ---
    'structured query language': 'SQL', 'sql queries': 'SQL', 'mysql database': 'MySQL',
    'postgresql': 'PostgreSQL', 'postgres': 'PostgreSQL',
    'mongodb': 'MongoDB', 'mongo db': 'MongoDB',
    'relational database': 'RDBMS', 'nosql databases': 'NoSQL',
    'amazon web services': 'AWS', 'google cloud platform': 'GCP', 'microsoft azure': 'Azure',
    
    # --- AI / Data Science ---
    'machine learning': 'Machine Learning', 'ml': 'Machine Learning',
    'artificial intelligence': 'AI', 'genai': 'Generative AI', 'generative ai': 'Generative AI',
    'deep learning': 'Deep Learning', 'dl': 'Deep Learning',
    'natural language processing': 'NLP', 'computer vision': 'Computer Vision',
    
    # --- Mobile ---
    'ios development': 'iOS', 'android development': 'Android', 'android studio': 'Android',

    # --- .NET & C# Ecosystem ---
    'entity framework core': 'Entity Framework',
    'entity framework': 'Entity Framework',
    'ef core': 'Entity Framework',
    'ado.net': 'ADO.NET',
    'linq': 'LINQ',

    # --- Cybersecurity (Bổ sung mới) ---
    'cyber security': 'Cybersecurity', 'information security': 'Information Security',
    'pen testing': 'Penetration Testing', 'ethical hack': 'Ethical Hacking',
    'network sec': 'Network Security', 'crypto': 'Cryptography'
}

def clean_skill_local(skill):
    """Hàm dọn rác bọc thép (Xử lý theo thứ tự tuyệt đối)"""
    s = skill.lower().strip()
    
    if not s or len(s) < 2: 
        return None

    # ==========================================
    # BƯỚC 1: THẺ VIP (MIỄN TỬ KIM BÀI)
    # ==========================================
    VIP_SKILLS = {
        'c#': 'C#', 
        'c++': 'C++', 
        '.net': '.NET', 
        'react': 'ReactJS', 
        'vue': 'VueJS', 
        'node': 'NodeJS',
        'java': 'Java',      
        'python': 'Python',  
        'go ': 'Go',         
        'golang': 'Go',
        'php': 'PHP',
        'git': 'Git',
        'github': 'GitHub',
        'gitlab': 'GitLab',
        'bitbucket': 'Bitbucket',
        'postman': 'Postman',
        'swagger': 'Swagger',
        'agile': 'Agile',
        'scrum': 'Scrum',
        'bash': 'Bash',
        'powershell': 'PowerShell',
        'c (programming language)': 'C',
        'swift': 'Swift',
        'scala': 'Scala',
        'rust': 'Rust',
        'r programming': 'R',
        'ruby': 'Ruby',
        'objective-c': 'Objective-C',
        'visual basic': 'Visual Basic',
        'cobol': 'COBOL',
        'test driven development': 'TDD',
        'behavior-driven development': 'BDD',
        'site reliability': 'SRE',
        'linux': 'Linux',
        'ci/cd': 'CI/CD',
        'express': 'ExpressJS', # Đã sửa lỗi khai báo đè
        'spring boot': 'Spring Boot',
        # --- Bổ sung VIP cho Cybersecurity ---
        'cryptography': 'Cryptography',
        'penetration testing': 'Penetration Testing',
        'ethical hacking': 'Ethical Hacking',
        'cybersecurity': 'Cybersecurity'
    }
    
    for vip_key, vip_val in VIP_SKILLS.items():
        if vip_key in s:
            return vip_val 

    # ==========================================
    # BƯỚC 1.5: MAPPING BÌNH THƯỜNG (Cho các từ còn lại)
    # ==========================================
    for key, val in MAPPING.items():
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

def main():
    print("🚀 BẮT ĐẦU DỌN RÁC BẰNG PYTHON (OFFLINE - SIÊU TỐC)")
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
    main()