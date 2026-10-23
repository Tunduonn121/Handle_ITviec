import json
import collections
import re

RAW_FILE = r"data\raw_courses_massive.json"

# ==========================================
# HÀNH LÝ MANG THEO (KHÔNG CÓ LÀ BÁO LỖI)
# ==========================================
BLACKLIST_EXACT = {
    'vscode', 'visual studio', 'eclipse', 'intellij',
    'maven', 'gradle', 'npm', 'yarn', 'webpack', 'jira', 'slack', 'trello', 'confluence', 'debugging'
}

BLACKLIST_SUBSTRING = [
    'linux command', 'command line', 'maintainability', 'testability', 'reliability', 
    'design strategies', 'best practices', 'principles', 'software engineering', 
    'computer science', 'communication', 'leadership', 'teamwork', 'problem solving', 
    'critical thinking', 'project management', 'quality assurance', 'troubleshooting', 
    'optimization', 'introduction', 'basics', 'fundamentals', 'advanced', 'concepts', 
    'how to', 'course', 'module', 'learn'
]

MAPPING = {
    'java programming': 'Java', 'core java': 'Java', 'java se': 'Java', 'java ee': 'Java',
    'python programming': 'Python', 'python 3': 'Python', 'interactive python': 'Python',
    'c++ programming': 'C++', 'c plus plus': 'C++', 'modern c++': 'C++',
    'c# programming': 'C#', 'c sharp': 'C#',
    'node.js': 'NodeJS', 'nodejs': 'NodeJS', 'express.js': 'ExpressJS', 'express': 'ExpressJS',
    'golang': 'Go', 'go programming': 'Go',
    'ruby on rails': 'Ruby on Rails', 'rails': 'Ruby on Rails',
    'php programming': 'PHP', 'laravel framework': 'Laravel',
    'application programming interface': 'API', 'restful api': 'REST API', 'rest apis': 'REST API',
    'object oriented programming': 'OOP', 'object-oriented': 'OOP', 'oop concepts': 'OOP',
    'microservice architecture': 'Microservices', 'microservices': 'Microservices',
    'react.js': 'ReactJS', 'reactjs': 'ReactJS', 'react native': 'React Native',
    'vue.js': 'VueJS', 'vuejs': 'VueJS', 'vue': 'VueJS',
    'angularjs': 'Angular', 'angular.js': 'Angular',
    'javascript programming': 'JavaScript', 'js': 'JavaScript', 'ecmascript': 'JavaScript',
    'typescript programming': 'TypeScript', 'ts': 'TypeScript',
    'html5': 'HTML', 'css3': 'CSS', 'cascading style sheets': 'CSS',
    'front-end web development': 'Frontend', 'front end': 'Frontend',
    'structured query language': 'SQL', 'sql queries': 'SQL', 'mysql database': 'MySQL',
    'postgresql': 'PostgreSQL', 'postgres': 'PostgreSQL',
    'mongodb': 'MongoDB', 'mongo db': 'MongoDB',
    'relational database': 'RDBMS', 'nosql databases': 'NoSQL',
    'amazon web services': 'AWS', 'google cloud platform': 'GCP', 'microsoft azure': 'Azure',
    'machine learning': 'Machine Learning', 'ml': 'Machine Learning',
    'artificial intelligence': 'AI', 'genai': 'Generative AI', 'generative ai': 'Generative AI',
    'deep learning': 'Deep Learning', 'dl': 'Deep Learning',
    'natural language processing': 'NLP', 'computer vision': 'Computer Vision',
    'ios development': 'iOS', 'android development': 'Android', 'android studio': 'Android'
}

# ==========================================
# HÀM LỌC RÁC
# ==========================================
def clean_skill_local(skill):
    s = skill.lower().strip()
    
    if not s or len(s) < 2: 
        return None

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
        # --- CÁC TOOL ĐƯỢC ÂN XÁ ---
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
        # --- NGÔN NGỮ BỊ OAN ---
        'c (programming language)': 'C',
        'swift': 'Swift',
        'scala': 'Scala',
        'rust': 'Rust',
        'r programming': 'R',
        'ruby': 'Ruby',
        'objective-c': 'Objective-C',
        'visual basic': 'Visual Basic',
        'cobol': 'COBOL',
        
        # --- KỸ NĂNG THỰC CHIẾN XỊN ---
        'test driven development': 'TDD',
        'behavior-driven development': 'BDD',
        'site reliability': 'SRE',
        'linux': 'Linux'
    }
    
    for vip_key, vip_val in VIP_SKILLS.items():
        if vip_key in s:
            return vip_val 

    for key, val in MAPPING.items():
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, s):
            return val

    for bad in BLACKLIST_EXACT:
        pattern = r'\b' + re.escape(bad) + r'\b'
        if re.search(pattern, s):
            return None

    for trash in BLACKLIST_SUBSTRING:
        if trash in s:
            return None
            
    if "programming" in s or "development" in s:
        return None

    s = re.sub(r'[^a-zA-Z0-9\+\#\-\.]', ' ', s) 
    s = ' '.join(s.split()) 
    
    if len(s) < 2: 
        return None
        
    return s.title()

# ==========================================
# HÀM THANH TRA CHẠY CHÍNH
# ==========================================
def main():
    print("🔍 ĐANG QUÉT NHỮNG KỸ NĂNG BỊ HỆ THỐNG TỪ CHỐI...")
    try:
        with open(RAW_FILE, 'r', encoding='utf-8') as f:
            courses = json.load(f)
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file {RAW_FILE}. Sếp check lại đường dẫn nhé!")
        return

    rejected_skills = collections.Counter()
    
    for course in courses:
        for raw_skill in course.get("target_skills", []):
            if clean_skill_local(raw_skill) is None:
                rejected_skills[raw_skill] += 1

    with open("data/thanh_tra_rac.txt", "w", encoding="utf-8") as f:
        f.write("=== DANH SÁCH CÁC TỪ KHÓA BỊ CHÉM BỎ ===\n")
        for skill, count in rejected_skills.most_common():
            f.write(f"Bị chém {count} lần: {skill}\n")

    print("✅ Đã xuất báo cáo ra file 'data/thanh_tra_rac.txt'!")
    print("👉 Sếp mở file đó lên lướt 1 vòng xem có sót môn học nào quan trọng không nhé!")

if __name__ == "__main__":
    main()