import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os

import re


# Nhóm A: chỉ xóa khi skill BẰNG ĐÚNG từ này (exact match toàn chuỗi).
# Đây là các nhãn UI rác hay đứng một mình.
TRASH_EXACT = {
    'skill', 'skills', 'tool', 'tools', 'review', 'reviews', 'minute', 'minutes',
    'hour', 'hours', 'coursera', 'module', 'modules', 'instructor', 'instructors',
    'button', 'cookie', 'cookies', 'details', 'quiz', 'assignment', 'read',
    'learn', 'level', 'certificate', 'gain', 'show all', 'view all', 'related'
}

# Nhóm B: xóa khi skill CHỨA cụm này như một từ/cụm độc lập (word-boundary),
# dùng cho các cụm marketing dài chắc chắn là rác.
TRASH_PHRASES = [
    'show all', 'view all', 'skills you', 'tools you',
]

def is_trash_skill(clean_text: str) -> bool:
    s = clean_text.lower().strip()

    # 1) Bằng đúng một từ rác -> loại
    if s in TRASH_EXACT:
        return True

    # 2) Chứa nguyên một cụm rác (word-boundary, không cắt giữa từ) -> loại
    for phrase in TRASH_PHRASES:
        if re.search(r'\b' + re.escape(phrase) + r'\b', s):
            return True

    return False

# Ánh xạ độ khó hiển thị trên Coursera -> số Level của hệ thống
LEVEL_MAP = {"beginner": 1, "intermediate": 2, "advanced": 3}

# Mẫu khớp CHÍNH XÁC cụm badge "Beginner level" / "Intermediate level" / "Advanced level"
LEVEL_PHRASE_RE = re.compile(r'^\s*(beginner|intermediate|advanced)\s+level\s*$', re.IGNORECASE)

def detect_course_level(soup):
    """
    Đọc ĐÚNG badge độ khó mà Coursera hiển thị (vd: 'Intermediate level').
    Trả về (level_int, raw_text). Nếu không tìm thấy -> (None, None) để còn audit,
    KHÔNG mặc định về 1 nữa (mặc định 1 sẽ làm hỏng dữ liệu level).
    """
    # 1) Ưu tiên: tìm node text khớp chính xác mẫu "<X> level"
    for text_node in soup.find_all(string=LEVEL_PHRASE_RE):
        m = LEVEL_PHRASE_RE.match(text_node.strip())
        if m:
            key = m.group(1).lower()
            return LEVEL_MAP[key], text_node.strip()

    # 2) Dự phòng: tìm cụm "<X> level" trong text (vẫn an toàn hơn dò 1 từ trống)
    page_text = soup.get_text(separator=' ').lower()
    m = re.search(r'(beginner|intermediate|advanced)\s+level', page_text)
    if m:
        return LEVEL_MAP[m.group(1)], m.group(0)

    return None, None

def setup_driver():
    """Khởi tạo trình duyệt ẩn danh, chống Anti-bot"""
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

    
def crawl_course_links(driver, keyword, num_scrolls=100): 
    """
    KỊCH BẢN CÀNG QUÉT V2 (SMOOTH SCROLL + SMART STOP)
    Cuộn mượt mà để chống trượt cảm biến, và tự động ngắt nếu hết data.
    """
    formatted_keyword = keyword.replace(" ", "%20")
    
    url = f"https://www.coursera.org/search?query={formatted_keyword}&productTypeDescription=Courses&productDifficultyLevel=Beginner&productDifficultyLevel=Intermediate&productDifficultyLevel=Advanced&language=English&topic=Computer%20Science&topic=Information%20Technology"
    print(f"🚀 Đang cào (Courses, English, IT): '{keyword}'...")
   
    driver.get(url)
    time.sleep(5)
    
    collected_links = set() 
    previous_count = 0
    stuck_counter = 0 # Bộ đếm phanh
    
    for i in range(num_scrolls):
        # 1. BÓC TÁCH DỮ LIỆU
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag['href']
            if "/learn/" in href:
                full_link = href if href.startswith("http") else f"https://www.coursera.org{href}"
                collected_links.add(full_link)
                
        current_count = len(collected_links)
        print(f"  🚜 Cuộn lần {i+1}/{num_scrolls} - Thu hoạch: {current_count} khóa học...")

        # 2. LOGIC PHANH THÔNG MINH (DỪNG SỚM ĐỠ TỐN THỜI GIAN)
        if current_count == previous_count:
            stuck_counter += 1
            # Nếu 4 lần cuộn liên tiếp (chờ khá lâu) mà không nhặt thêm được link nào
            if stuck_counter >= 4:
                print(f"  🛑 Đã vét cạn sạch sẽ khóa học cho '{keyword}'. Tự động chuyển từ khóa!")
                break
        else:
            stuck_counter = 0 # Có cá mới thì reset phanh
            previous_count = current_count

        # 3. KỸ THUẬT CUỘN MƯỢT (SMOOTH SCROLL)
        # Thay vì nhảy vọt 1500px, ta chia nhỏ ra nhích 3 lần, mỗi lần 500px
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1) # Nghỉ nhẹ giữa các nhịp cuộn
            
        time.sleep(2) # Thời gian chờ tổng cộng cho 1 lần loop là khoảng 5 giây, Coursera load dư sức
        
    return list(collected_links)

def extract_course_details(driver, url):
    """Bóc tách chi tiết: Title, Level (badge chuẩn), Skills, Description"""
    print(f"  -> Đang bóc tách chi tiết: {url}")
    driver.get(url)

    for _ in range(4):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ✅ DỌN RÁC MỘT LẦN Ở ĐẦU: xóa footer + mục "Related" trước khi đọc level/skill
    for footer in soup.find_all('footer'):
        footer.decompose()
    for section in soup.find_all(lambda tag: tag.name == 'section' and tag.get('aria-label') == 'Related'):
        section.decompose()

    course_data = {
        "url": url,
        "title": "N/A",
        "level": None,          # None = chưa xác định (sẽ audit), thay vì mặc định 1
        "level_text": "N/A",    # giữ lại text gốc để bạn kiểm chứng
        "target_skills": [],
        "description": "N/A"
    }

    # 1. Title
    try:
        h1_tag = soup.find("h1")
        if h1_tag:
            course_data["title"] = h1_tag.get_text(strip=True)
    except Exception as e:
        print(f"    ⚠️ Lỗi đọc title: {e}")

    # 2. Level — đọc đúng badge "X level"
    level_int, level_raw = detect_course_level(soup)
    if level_int is not None:
        course_data["level"] = level_int
        course_data["level_text"] = level_raw
    else:
        print(f"    ⚠️ KHÔNG tìm thấy badge level cho: {url}")

    # 3. Skills (giữ logic cũ của bạn, nhưng KHÔNG cần decompose lại nữa)
    try:
        skills = []
        target_phrases = ["skills you'll gain", "tools you'll learn", "skills you will gain"]
        target_headers = soup.find_all(lambda tag: tag.name in ['h2', 'h3', 'h4', 'h5', 'strong', 'div'] and
                                        any(phrase in tag.get_text().lower() for phrase in target_phrases) and
                                        len(tag.get_text()) < 40)
        for header in target_headers:
            container = header.find_parent("div") or header.find_parent("section")
            if container:
                for text in container.stripped_strings:
                    clean_text = text.strip()
                    if 2 < len(clean_text) < 40:
                        if not is_trash_skill(clean_text):
                            skills.append(clean_text)
        course_data["target_skills"] = list(set(skills))
    except Exception as e:
        print(f"    ⚠️ Lỗi đọc skills: {e}")

    # 4. Description
    try:
        about_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'div'] and
                                 "about" in tag.get_text().lower() and "course" in tag.get_text().lower())
        if about_header:
            parent1 = about_header.find_parent()
            parent2 = parent1.find_parent() if parent1 else None
            container = parent2 or parent1
            if container:
                desc_text = container.get_text(separator=' ', strip=True)
                course_data["description"] = desc_text[:500] + "..."
    except Exception as e:
        print(f"    ⚠️ Lỗi đọc description: {e}")

    return course_data

# --- THỰC THI CHÍNH ---
# --- THỰC THI CHÍNH (CHẾ ĐỘ SẢN XUẤT - PRODUCTION MODE) ---
# --- THỰC THI CHÍNH (CHẾ ĐỘ CÀO TÍCH LŨY - INCREMENTAL MODE) ---
# if __name__ == "__main__":
#     driver = setup_driver()

#     try:
#         # Ép đường dẫn cứng vào thư mục data
#         output_file = r"data\raw_courses_massive.json" 
#         existing_results = []
#         existing_urls = set() # Dùng Set để tra cứu trùng lặp siêu tốc O(1)

#         # ==========================================
#         # BƯỚC 1: ĐỌC KHO DỮ LIỆU CŨ (Nếu có)
#         # ==========================================
#         if os.path.exists(output_file):
#             with open(output_file, "r", encoding="utf-8") as f:
#                 try:
#                     existing_results = json.load(f)
#                     # Gom tất cả các URL đã cào vào một mảng để check trùng
#                     existing_urls = {course["url"] for course in existing_results}
#                     print(f"📦 KHO DỮ LIỆU HIỆN TẠI: Đang có {len(existing_results)} khóa học.")
#                 except json.JSONDecodeError:
#                     print("⚠️ File cũ trống hoặc lỗi, sẽ tạo mới từ đầu.")

#         # ==========================================
#         # BƯỚC 2: CÀO LINK MỚI TỪ TỪ KHÓA MỚI
#         # ==========================================

#         #1. Phân khu Backend (Lõi hệ thống)
#         #new_keywords = ["Java", "C#", "C++", "Python",  "Java Backend", "Spring Boot", "Data Structures", "Object Oriented Programming"] # Nhập các từ khóa mới vào đây
        
#         #2. Phân khu Frontend (Giao diện)
#         #new_keywords = ["React.js", "Angular", "Vue.js", "JavaScript", "TypeScript", "HTML CSS", "Tailwind CSS", "Front-End Web Development"]
        
#         #3. Phân khu Data Science & AI (Xu hướng hiện tại)
#         #new_keywords = ["Machine Learning", "Deep Learning", "Artificial Intelligence", "Data Analytics", "Data Engineering", "Natural Language Processing", "Computer Vision"]
        
#         #4. Phân khu Database (Lưu trữ)
#         #new_keywords=["SQL", "MySQL", "PostgreSQL", "NoSQL", "MongoDB", "Redis", "Database Design"]
        
#         #5. Phân khu DevOps & Cloud 
#         #new_keywords = ["AWS", "Docker", "Kubernetes", "Google Cloud Platform", "Microsoft Azure", "CI/CD", "Linux System Administration", "DevOps"]

#         #6. Phân khu Mobile (Di động)
#         #new_keywords = ["Flutter", "React Native", "iOS Development", "Swift Programming", "Android Development", "Kotlin"]

#         #7.Phân khu Core CS & Architecture
#         #new_keywords = ["System Design", "Microservices", "Software Architecture", "REST API", "Software Testing", "Agile Software Development"]

#         #8. Phân khu An ninh mạng (Cybersecurity)
#         new_keywords = ["Cybersecurity", "Ethical Hacking", "Network Security", "Information Security", "Penetration Testing", "Cyber Threat Intelligence", "Security Operations", "Cryptography"]

#         new_links = []
        
#         for kw in new_keywords:
#             links = crawl_course_links(driver, kw, num_scrolls=20)
#             new_links.extend(links)
            
#         # Loại bỏ các link trùng lặp nội bộ trong mẻ cào mới này
#         unique_new_links = list(set(new_links))
#         print(f"\n🔍 Vừa cào được {len(unique_new_links)} link từ Coursera. Bắt đầu đối chiếu bộ lọc...")

#         # ==========================================
#         # BƯỚC 3: ĐỐI CHIẾU VÀ CÀO CHI TIẾT
#         # ==========================================
#         new_results = []
        
#         for link in unique_new_links:
#             # KIỂM TRA TRÙNG LẶP: Nếu URL này đã có trong file JSON cũ -> Bỏ qua ngay!
#             if link in existing_urls:
#                 print(f" ⏭️ BỎ QUA (Đã có trong Database): {link}")
#                 continue 

#             # Nếu là link mới tinh -> Mới tiến hành cho bot chui vào bóc tách
#             details = extract_course_details(driver, link)
#             if details and details["target_skills"]:
#                 new_results.append(details)
#                 existing_urls.add(link) # Cập nhật vào bộ nhớ RAM ngay lập tức
                
#             time.sleep(1.5)

#         # ==========================================
#         # BƯỚC 4: GỘP DỮ LIỆU VÀ GHI ĐÈ LẠI
#         # ==========================================
#         if new_results:
#             # Nối mảng mới vào sau mảng cũ
#             final_results = existing_results + new_results 
            
#             # Ghi đè toàn bộ mảng đã gộp vào lại file JSON
#             with open(output_file, "w", encoding="utf-8") as f:
#                 json.dump(final_results, f, ensure_ascii=False, indent=4)
                
#             print(f"\n🎉 THÀNH CÔNG! Đã cào thêm {len(new_results)} khóa học mới.")
#             print(f"📈 TỔNG SỐ KHÓA HỌC TRONG KHO HIỆN TẠI: {len(final_results)}")
#         else:
#             print("\n🤷‍♂️ Mẻ này không thu hoạch được khóa nào mới (Có thể do trùng hết hoặc không lấy được kỹ năng).")

#     finally:
#         driver.quit()


# main bóc tách level từ coursera
# if __name__ == "__main__":
#     driver = setup_driver()
#     try:
#         # 🔬 CHẾ ĐỘ TEST: dán 1-2 link khóa học để kiểm tra việc đọc Level
#         TEST_URLS = [
#             "https://www.coursera.org/learn/continuous-integration-and-continuous-delivery-ci-cd",  # kỳ vọng: Intermediate (2)
#             # "https://www.coursera.org/learn/<khóa-beginner-bạn-chọn>",  # thêm 1 khóa Beginner để đối chiếu
#         ]

#         print("=" * 70)
#         print("🔬 TEST CÀO THỬ 1-2 KHÓA HỌC (KIỂM TRA LEVEL)")
#         print("=" * 70)

#         links = crawl_course_links(driver, "CI/CD", num_scrolls=3)
#         for u in links[:2]:
#             data = extract_course_details(driver, u)
#             print("\n" + "-" * 70)
#             print(f"📌 Title       : {data['title']}")
#             print(f"🎯 Level       : {data['level']}  (badge gốc: '{data['level_text']}')")
#             print(f"🧩 Skills ({len(data['target_skills'])}) : {data['target_skills'][:10]}")
#             print(f"📝 Desc        : {data['description'][:120]}...")

#         print("\n✅ Test xong. Kiểm tra cột Level có khớp badge trên web không.")
#     finally:
#         driver.quit()        

#test trashword

if __name__ == "__main__":
    # --- TEST LỌC RÁC SKILL (không cần Selenium) ---
    SHOULD_KEEP = ["Machine Learning", "Deep Learning", "Threading",
                   "Multithreading", "Low-level Programming", "Tooling", "React"]
    SHOULD_DROP = ["Skill", "Tools", "Review", "Learn", "Level",
                   "Coursera", "Show all", "View all"]

    print("✅ PHẢI GIỮ LẠI (không được loại):")
    for s in SHOULD_KEEP:
        flag = "❌ BỊ LOẠI OAN" if is_trash_skill(s) else "🟢 giữ"
        print(f"   {flag:<14} {s}")

    print("\n🗑️  PHẢI LOẠI (rác):")
    for s in SHOULD_DROP:
        flag = "🟢 loại đúng" if is_trash_skill(s) else "❌ LỌT RÁC"
        print(f"   {flag:<14} {s}")