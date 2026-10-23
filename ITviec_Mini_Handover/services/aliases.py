import re

# Coi chữ/số/+/#/. là một phần của "từ" để 'c' không dính nhầm 'c#', 'c++'
_SKILL_BOUNDARY = r'[a-z0-9+#.]'

def _token_in(needle: str, haystack: str) -> bool:
    """needle có xuất hiện như một token/cụm ĐỘC LẬP trong haystack không (không cắt giữa từ)."""
    if not needle:
        return False
    pat = r'(?<!' + _SKILL_BOUNDARY + r')' + re.escape(needle) + r'(?!' + _SKILL_BOUNDARY + r')'
    return re.search(pat, haystack) is not None

def is_skill_match(a: str, b: str) -> bool:
    """
    HÀM SO KHỚP KỸ NĂNG DUY NHẤT của toàn hệ thống (Single Source of Truth).
    Chuẩn hóa cả hai qua alias map, khớp khi: bằng nhau, HOẶC cái này là token độc lập trong cái kia.
    An toàn cho c#, c++, .net; KHÔNG khớp nhầm java↔javascript, go↔django.
    """
    ca, cb = clean_and_normalize(a), clean_and_normalize(b)
    if ca == cb:
        return True
    return _token_in(ca, cb) or _token_in(cb, ca)

def is_level_fit(course_level: int, missing_levels: list) -> bool:
    """Khóa có dạy đúng MỘT trong các level đang thiếu không."""
    try:
        return int(course_level) in set(missing_levels)
    except (ValueError, TypeError):
        return False

# =====================================================================
# BỘ TỪ ĐIỂN ALIAS TOÀN CỤC BỌC THÉP (GLOBAL ALIAS MAP) - VERSION KHÓA LUẬN
# Định nghĩa duy nhất tại đây để tuân thủ nghiêm ngặt nguyên tắc DRY (Don't Repeat Yourself)
# =====================================================================

GLOBAL_ALIAS_MAP = {
    # Ngôn ngữ & Nền tảng Backend chính
    "c#": "c#",
    "c sharp": "c#",
    "c#.net": "c#",
    "c#.net core": "c#",
    ".net": ".net",
    ".net 8": ".net",
    ".net 7": ".net",
    ".net 6": ".net",
    ".net 5": ".net",
    ".net core": ".net",
    "asp.net core": ".net",
    "asp.net": ".net",
    "java": "java",
    "java 8": "java",
    "java 11": "java",
    "java 17": "java",
    "java 21": "java",
    "core java": "java",
    "j2ee": "java",
    "node.js": "nodejs",
    "node js": "nodejs",
    "nodejs": "nodejs",
    "node": "nodejs",
    "golang": "go",
    "go programming": "go",
    "go": "go",
    "c plus plus": "c++",
    "cpp": "c++",
    "c++": "c++",
    "python 3": "python",
    "python": "python",

    # Frameworks Backend & ORM
    "spring boot": "spring boot",
    "spring": "spring boot",
    "spring mvc": "spring boot",
    "spring data jpa": "jpa",
    "jpa": "jpa",
    "hibernate": "jpa",
    "entity framework": "entity framework",
    "orm": "entity framework",
    "object-relational mapping": "entity framework",
    "ef core": "entity framework",
    "entity framework core": "entity framework",

    # Hệ sinh thái Frontend
    "react": "reactjs",
    "react.js": "reactjs",
    "reactjs": "reactjs",
    "vue": "vuejs",
    "vue.js": "vuejs",
    "vuejs": "vuejs",
    "angular": "angular",
    "angularjs": "angular",
    "angular.js": "angular",
    "js": "javascript",
    "javascript": "javascript",
    "ecmascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",

    # DevOps, Cloud Platforms & CI/CD
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
   
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "azure": "azure",
    "microsoft azure": "azure",
    "ci/cd": "ci/cd",
    "continuous integration": "ci/cd",
    "continuous deployment": "ci/cd",
    "gitlab ci/cd": "ci/cd",
    "gitlab ci": "ci/cd",
    "gitlab": "ci/cd",
    "github actions": "ci/cd",

    # Cơ sở dữ liệu & Caching (Database Layer)
    "sql": "sql",
    "relational db": "sql",
    "sql server": "sql server",
    "microsoft sql servers": "sql server",
    "microsoft sql server": "sql server",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "mongodb": "mongodb",
    "mongo db": "mongodb",
    "mongo": "mongodb",
    "redis": "redis",
    "elasticsearch": "elasticsearch",
    "oracle": "oracle",

    # Khoa học dữ liệu, AI & Các khái niệm Core CS
    "machine learning": "machine learning",
    "ml": "machine learning",
    "artificial intelligence": "artificial intelligence",
    "ai": "artificial intelligence",
    "ai tools": "artificial intelligence",
    "copilot": "artificial intelligence",
    "chatgpt": "artificial intelligence",
    "automl": "artificial intelligence",
    "deep learning": "deep learning",
    "dl": "deep learning",
    "natural language processing": "natural language processing",
    "nlp": "natural language processing",
    "oop": "oop",
    "object oriented programming": "oop",
    "object-oriented": "oop",
    "data structures": "data structures",
    "data structures & algorithms": "data structures",
    "dsa": "data structures",
    "algorithms": "algorithms",
    "penetration testing": "penetration testing",
    "pen testing": "penetration testing",
    "ethical hacking": "penetration testing",
    "information security": "information security",
    "infosec": "information security",
    "cybersecurity": "information security",
    "cyber security": "information security",
    "etl": "etl",
    "data lake": "data lake",
    "power bi": "power bi",
    "tableau": "power bi",
    "google data studio": "power bi",
    "bi tools": "power bi",
    "microservices": "microservices",
    "microservice": "microservices",
    "microservices architecture": "microservices",
    "rest api": "rest api",
    "restful api": "rest api",
    "api restful": "rest api",
    "web api": "rest api",
    "api design": "rest api",
    "jwt": "jwt",
    "oauth 2": "oauth 2",
    "ssr": "ssr",
    "csr": "csr",
    "bootstrap": "bootstrap",
    "tailwindcss": "tailwindcss",
    # Container & Version Control & DevOps (Coursera emit rất nhiều)
    "docker": "docker",
    "containerization": "docker",
    "git": "git",
    "github": "git",
    "version control": "git",
    "devops": "devops",
    
    "continuous delivery": "ci/cd",
    
}

def clean_and_normalize(skill_name: str) -> str:
    """Chuẩn hóa skill về tên chuẩn. Thử khớp BẢN GỐC trước, rồi mới thử bản đã làm sạch."""
    s = skill_name.lower().strip()
    if s in GLOBAL_ALIAS_MAP:            # thử nguyên gốc trước -> giữ được 'ci/cd'
        return GLOBAL_ALIAS_MAP[s]
    s2 = s.replace("/", " ").replace("-", " ")
    return GLOBAL_ALIAS_MAP.get(s2, s2)