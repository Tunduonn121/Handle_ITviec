import re
import json
# Import hàm LLM xịn của Sếp từ file skill_extractor
from services.skill_extractor import extract_skills_from_jd 

# 1. Thuật toán Keyword Matching Cũ (Baseline)
STATIC_DICT = ["c#", "java", "react", "angular", "aws", "azure", "gcp", "cloud", "ci/cd", "jenkins", "gitlab ci"]

def baseline_regex_extract(text):
    text_lower = text.lower()
    found = []
    for skill in STATIC_DICT:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found.append(skill)
    return found

# 2. Tập dữ liệu Test nhanh (Sếp có thể thêm vào đây)
TEST_CASES = [
    # --- 2 CÂU BÌNH THƯỜNG (Cơ bản, không đánh đố) ---
    "Yêu cầu ứng viên có tối thiểu 2 năm kinh nghiệm làm việc với Java và Spring Boot. Nắm vững MySQL và thiết kế RESTful API.",
    "Tôi có 1.5 năm kinh nghiệm làm Frontend Developer sử dụng ReactJS và Redux. Từng làm việc với Git và HTML/CSS.",

    # --- 13 CÂU "KHÓ NHẰN" (Chứa HOẶC, HAY, ngoặc kép, kỹ năng mềm gây nhiễu) ---
    "Thành thạo lập trình Backend với C# hoặc Java. Bắt buộc có kinh nghiệm với các hệ quản trị cơ sở dữ liệu quan hệ (MySQL, PostgreSQL hoặc Oracle).",
    
    "Kinh nghiệm 3 năm làm Fullstack. Nắm vững NodeJS/ExpressJS. Đã từng triển khai ứng dụng lên Cloud platforms (AWS, GCP).",
    
    "Ưu tiên ứng viên biết sử dụng các công cụ Message Queue (RabbitMQ hay Kafka) và hệ thống Caching (Redis hoặc Memcached).",
    
    "Chuyên gia về CI/CD pipelines (Jenkins, Github Actions). Sử dụng thành thạo Python hoặc Go. Cần có kỹ năng giao tiếp tốt (Communication skills).",
    
    "Yêu cầu khả năng xử lý dữ liệu lớn (Hadoop hoặc Spark). Biết sử dụng BI Tools (Power BI, Tableau) là một lợi thế rất lớn.",
    
    "Sử dụng công cụ chính là C++ hoặc C#. Biết cơ bản về các nền tảng quản lý container (Docker, Kubernetes).",
    
    "Tìm kiếm lập trình viên Frontend sử dụng React hoặc VueJS. Có kiến thức về CSS Preprocessors (SASS, LESS). Ưu tiên ứng viên có tư duy Design Thinking.",
    
    "2 năm lập trình Mobile App với Flutter hoặc React Native. Từng publish app lên stores. Quen thuộc với Local DB (SQLite, Realm).",
    
    "Yêu cầu 4 năm kinh nghiệm DevOps. Quản lý cấu hình bằng Infrastructure as Code (Terraform hoặc Ansible). Monitoring hệ thống bằng Grafana/Prometheus.",
    
    "Có kinh nghiệm với Data Warehouse (Snowflake, BigQuery). Sử dụng thành thạo SQL hay Python để phân tích dữ liệu trực quan.",
    
    "Nắm vững kiến thức bảo mật ứng dụng web. Có kinh nghiệm dùng các công cụ DAST (OWASP ZAP hoặc Burp Suite). Ưu tiên biết Scripting (Bash hoặc PowerShell).",
    
    "Kinh nghiệm Automation Test 2 năm với công cụ Selenium hoặc Cypress. Quản lý test case qua Jira. Hiểu biết về API Testing (Postman, Swagger).",
    
    "Thiết kế kiến trúc Microservices. Kinh nghiệm sâu sắc với ít nhất một hệ sinh thái Cloud (AWS, Microsoft Azure, Google Cloud). Thành thạo giao tiếp qua gRPC hoặc REST.",

    "Tốt nghiệp loại giỏi, có 6 tháng thực tập làm Python/Django. Đã từng deploy code lên Heroku và Render.",
    "Hơn 5 năm kinh nghiệm thiết kế UI/UX sử dụng Figma và Adobe XD. Biết sử dụng HTML5/CSS3 cơ bản.",
    "Tham gia phát triển game 2D bằng Unity (C#). Có chứng chỉ AWS Certified Cloud Practitioner. Kỹ năng làm việc nhóm cực kỳ tốt.",
    "Tôi là kỹ sư dữ liệu có kinh nghiệm dọn dẹp data bằng Pandas/NumPy và trực quan hóa bằng Matplotlib hay Seaborn.",
    "Đã từng xây dựng hệ thống E-commerce với Next.js và Tailwind CSS. Quản lý state bằng Zustand hoặc Redux Toolkit.",
    "Có 2 năm làm System Admin, quen thuộc với Linux shell scripting (Bash/Zsh). Quản lý server Ubuntu và CentOS.",
    "Tôi chuyên về mảng Testing, thành thạo Appium cho Mobile và Jmeter cho Load Testing. Kỹ năng quản lý thời gian xuất sắc.",
    "Lập trình viên IoT với kinh nghiệm làm việc trên Raspberry Pi và Arduino. Sử dụng C/C++ là ngôn ngữ chính.",
    "Từng làm việc trong dự án Agile/Scrum. Viết backend bằng Golang, tích hợp database MongoDB hoặc Cassandra.",
    "Kinh nghiệm 1 năm làm Blockchain (Solidity, Smart Contracts). Quen thuộc với thư viện Web3.js / Ethers.js.",
    "Đã tham gia vận hành hệ thống ERP (Odoo). Có kỹ năng viết query SQL phức tạp trên SQL Server.",
    "Tôi sử dụng thành thạo Vue 3 (Composition API) và Nuxt.js. Đã từng làm việc với Webpack và Vite.",
    "Chuyên gia về Computer Vision, sử dụng OpenCV và PyTorch. Có khả năng đọc hiểu tài liệu tiếng Anh xuất sắc.",
    "Làm việc với hệ thống Micro-frontend bằng Module Federation. Backend sử dụng NestJS (TypeScript).",
    "Từng setup toàn bộ luồng CI/CD với GitLab CI và SonarQube để check code quality. Nắm vững Docker Compose.",

    # --- 15 TRÍCH ĐOẠN TỪ JD (JOB DESCRIPTION SNIPPETS) ---
    "Tìm kiếm kỹ sư AI/ML có kinh nghiệm huấn luyện mô hình với TensorFlow hoặc Keras. Yêu cầu kỹ năng giải quyết vấn đề (Problem-solving).",
    "Tuyển dụng chuyên viên bảo mật mạng. Ưu tiên ứng viên có chứng chỉ (CEH hoặc CISSP). Sử dụng thành thạo Wireshark / Nmap.",
    "Yêu cầu ứng viên có khả năng lập trình đa luồng với Java (Core). Biết sử dụng framework Hibernate hay MyBatis là điểm cộng.",
    "Cần tuyển Game Developer thành thạo Unreal Engine (C++). Có kiến thức về 3D Modeling (Blender hoặc Maya) là một lợi thế.",
    "Vị trí Data Analyst yêu cầu 2 năm kinh nghiệm. Nắm vững ngôn ngữ truy vấn (MySQL, PostgreSQL). Biết dùng Google Data Studio / Looker.",
    "Yêu cầu kinh nghiệm làm việc với hệ thống Message Broker (ActiveMQ hoặc Apache Pulsar). Hiểu biết sâu về kiến trúc Event-Driven.",
    "Tìm lập trình viên iOS. Bắt buộc thành thạo Swift và Objective-C. Từng làm việc với CocoaPods hoặc Carthage.",
    "Tuyển kỹ sư phần mềm nhúng (Embedded). Yêu cầu kinh nghiệm với RTOS (FreeRTOS, Zephyr). Giao tiếp ngoại vi (SPI, I2C, UART).",
    "Vị trí Cloud Engineer: Yêu cầu khả năng quản lý hạ tầng bằng Pulumi hoặc AWS CloudFormation. Kinh nghiệm với Serverless architecture.",
    "Tìm kiếm QA Engineer có kinh nghiệm viết kịch bản test tự động bằng Playwright hoặc Puppeteer. Kỹ năng tư duy logic tốt.",
    "Yêu cầu kinh nghiệm tối thiểu 3 năm phát triển phần mềm với Ruby on Rails. Quen thuộc với TDD/BDD (RSpec hay Cucumber).",
    "Vị trí Fullstack Developer. Yêu cầu vững Angular (phiên bản 10 trở lên) và Spring Boot. Ưu tiên ứng viên từng làm việc trong ngành ngân hàng (Banking domain).",
    "Cần tuyển DBA (Database Administrator) có kinh nghiệm tối ưu hóa hiệu năng cho Oracle hoặc IBM Db2. Khả năng chịu áp lực cao.",
    "Yêu cầu thành thạo các công cụ phân tích log (ELK Stack: Elasticsearch, Logstash, Kibana) hoặc Splunk.",
    "Tuyển vị trí DevOps. Yêu cầu kinh nghiệm cấu hình Service Mesh (Istio hoặc Linkerd). Biết sử dụng Helm charts để deploy ứng dụng."

]

# 3. Chạy đối chiếu
print("="*60)
print("🚀 BẮT ĐẦU CHẠY BENCHMARK SO SÁNH 2 THUẬT TOÁN")
print("="*60)

for idx, text in enumerate(TEST_CASES, 1):
    print(f"\n📦 [TEST CASE {idx}]: {text}")
    
    # Chạy phương pháp cũ
    old_result = baseline_regex_extract(text)
    print(f" ❌ [KEYWORD CŨ]  : {old_result}")
    
    # Chạy phương pháp mới (LLM của Sếp)
    try:
        new_result = extract_skills_from_jd(text)
        print(f" ✅ [HYBRID LLM]  : {new_result}")
    except Exception as e:
        print(f" ✅ [HYBRID LLM]  : LỖI PARSE JSON - {e}")