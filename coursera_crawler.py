import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os

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
    """Bóc tách chi tiết: Lấy cả Skills & Tools, LOẠI BỎ nếu rỗng"""
    print(f"  -> Đang bóc tách chi tiết: {url}")
    driver.get(url)
    
    for _ in range(4):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.5) 
        
    soup = BeautifulSoup(driver.page_source, "html.parser")
    course_data = {
        "url": url,
        "title": "N/A",
        "level": 1, 
        "target_skills": [],
        "description": "N/A"
    }
    
    # 1. Bóc tách Title
    try:
        h1_tag = soup.find("h1")
        if h1_tag:
            course_data["title"] = h1_tag.get_text(strip=True)
    except: pass
    
    # 2. Bóc tách Level
    try:
        page_text = soup.get_text(separator=' ').lower()
        if "advanced level" in page_text:
            course_data["level"] = 3
        elif "intermediate level" in page_text:
            course_data["level"] = 2
        elif "beginner level" in page_text:
            course_data["level"] = 1
        elif "advanced" in page_text and "intermediate" not in page_text and "beginner" not in page_text:
            course_data["level"] = 3
        elif "intermediate" in page_text and "beginner" not in page_text:
            course_data["level"] = 2
        else:
            course_data["level"] = 1
    except: pass

    # 3. Bóc tách Kỹ năng (Lấy cả Skills và Tools - CHỐNG FOOTER)
    try:
        # CHIẾN THUẬT 1: Hủy diệt phần Footer để tránh nhận vơ dữ liệu rác ở đáy trang
        for footer in soup.find_all('footer'):
            footer.decompose() # Xóa vĩnh viễn phần footer khỏi mã HTML hiện tại
            
        # Hủy luôn các vùng hay chứa link gợi ý (Related courses)
        for section in soup.find_all(lambda tag: tag.name == 'section' and tag.get('aria-label') == 'Related'):
            section.decompose()

        skills = []
        # CHIẾN THUẬT 2: Tìm CHÍNH XÁC cụm từ thay vì chỉ tìm chữ "skills"
        target_phrases = ["skills you'll gain", "tools you'll learn", "skills you will gain"]
        
        target_headers = soup.find_all(lambda tag: tag.name in ['h2', 'h3', 'h4', 'h5', 'strong', 'div'] and 
                                      any(phrase in tag.get_text().lower() for phrase in target_phrases) and 
                                      len(tag.get_text()) < 40)
        
        for header in target_headers:
            # Lấy vùng div bao bọc ngay bên ngoài tiêu đề này
            container = header.find_parent("div") or header.find_parent("section")
            if container:
                for text in container.stripped_strings:
                    clean_text = text.strip()
                    
                    # Cập nhật Blacklist (Đã thêm chữ 'gain' vào để lọc cụm "Skills you'll gain")
                    trash_words = ['skill', 'tool', 'review', 'minute', 'hour', 'coursera', 'module', 'instructor', 'button', 'cookie', 'details', 'quiz', 'assignment', 'read', 'learn', 'level', 'certificate', 'gain', 'show all', 'view all', 'related']
                    
                    if 2 < len(clean_text) < 40:
                        if not any(trash in clean_text.lower() for trash in trash_words):
                            skills.append(clean_text)
        
        course_data["target_skills"] = list(set(skills))
    except Exception as e:
        pass
    
    # 4. Bóc tách Description
    try:
        about_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'div'] and "about" in tag.get_text().lower() and "course" in tag.get_text().lower())
        if about_header:
            parent1 = about_header.find_parent()
            parent2 = parent1.find_parent() if parent1 else None
            container = parent2 or parent1
            if container:
                desc_text = container.get_text(separator=' ', strip=True)
                course_data["description"] = desc_text[:500] + "..."
    except: pass

    return course_data

# --- THỰC THI CHÍNH ---
# --- THỰC THI CHÍNH (CHẾ ĐỘ SẢN XUẤT - PRODUCTION MODE) ---
# --- THỰC THI CHÍNH (CHẾ ĐỘ CÀO TÍCH LŨY - INCREMENTAL MODE) ---
if __name__ == "__main__":
    driver = setup_driver()

    try:
        # Ép đường dẫn cứng vào thư mục data
        output_file = r"data\raw_courses_massive.json" 
        existing_results = []
        existing_urls = set() # Dùng Set để tra cứu trùng lặp siêu tốc O(1)

        # ==========================================
        # BƯỚC 1: ĐỌC KHO DỮ LIỆU CŨ (Nếu có)
        # ==========================================
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                try:
                    existing_results = json.load(f)
                    # Gom tất cả các URL đã cào vào một mảng để check trùng
                    existing_urls = {course["url"] for course in existing_results}
                    print(f"📦 KHO DỮ LIỆU HIỆN TẠI: Đang có {len(existing_results)} khóa học.")
                except json.JSONDecodeError:
                    print("⚠️ File cũ trống hoặc lỗi, sẽ tạo mới từ đầu.")

        # ==========================================
        # BƯỚC 2: CÀO LINK MỚI TỪ TỪ KHÓA MỚI
        # ==========================================

        #1. Phân khu Backend (Lõi hệ thống)
        #new_keywords = ["Java", "C#", "C++", "Python",  "Java Backend", "Spring Boot", "Data Structures", "Object Oriented Programming"] # Nhập các từ khóa mới vào đây
        
        #2. Phân khu Frontend (Giao diện)
        #new_keywords = ["React.js", "Angular", "Vue.js", "JavaScript", "TypeScript", "HTML CSS", "Tailwind CSS", "Front-End Web Development"]
        
        #3. Phân khu Data Science & AI (Xu hướng hiện tại)
        #new_keywords = ["Machine Learning", "Deep Learning", "Artificial Intelligence", "Data Analytics", "Data Engineering", "Natural Language Processing", "Computer Vision"]
        
        #4. Phân khu Database (Lưu trữ)
        #new_keywords=["SQL", "MySQL", "PostgreSQL", "NoSQL", "MongoDB", "Redis", "Database Design"]
        
        #5. Phân khu DevOps & Cloud 
        #new_keywords = ["AWS", "Docker", "Kubernetes", "Google Cloud Platform", "Microsoft Azure", "CI/CD", "Linux System Administration", "DevOps"]

        #6. Phân khu Mobile (Di động)
        #new_keywords = ["Flutter", "React Native", "iOS Development", "Swift Programming", "Android Development", "Kotlin"]

        #7.Phân khu Core CS & Architecture
        #new_keywords = ["System Design", "Microservices", "Software Architecture", "REST API", "Software Testing", "Agile Software Development"]

        #8. Phân khu An ninh mạng (Cybersecurity)
        new_keywords = ["Cybersecurity", "Ethical Hacking", "Network Security", "Information Security", "Penetration Testing", "Cyber Threat Intelligence", "Security Operations", "Cryptography"]

        new_links = []
        
        for kw in new_keywords:
            links = crawl_course_links(driver, kw, num_scrolls=20)
            new_links.extend(links)
            
        # Loại bỏ các link trùng lặp nội bộ trong mẻ cào mới này
        unique_new_links = list(set(new_links))
        print(f"\n🔍 Vừa cào được {len(unique_new_links)} link từ Coursera. Bắt đầu đối chiếu bộ lọc...")

        # ==========================================
        # BƯỚC 3: ĐỐI CHIẾU VÀ CÀO CHI TIẾT
        # ==========================================
        new_results = []
        
        for link in unique_new_links:
            # KIỂM TRA TRÙNG LẶP: Nếu URL này đã có trong file JSON cũ -> Bỏ qua ngay!
            if link in existing_urls:
                print(f" ⏭️ BỎ QUA (Đã có trong Database): {link}")
                continue 

            # Nếu là link mới tinh -> Mới tiến hành cho bot chui vào bóc tách
            details = extract_course_details(driver, link)
            if details and details["target_skills"]:
                new_results.append(details)
                existing_urls.add(link) # Cập nhật vào bộ nhớ RAM ngay lập tức
                
            time.sleep(1.5)

        # ==========================================
        # BƯỚC 4: GỘP DỮ LIỆU VÀ GHI ĐÈ LẠI
        # ==========================================
        if new_results:
            # Nối mảng mới vào sau mảng cũ
            final_results = existing_results + new_results 
            
            # Ghi đè toàn bộ mảng đã gộp vào lại file JSON
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(final_results, f, ensure_ascii=False, indent=4)
                
            print(f"\n🎉 THÀNH CÔNG! Đã cào thêm {len(new_results)} khóa học mới.")
            print(f"📈 TỔNG SỐ KHÓA HỌC TRONG KHO HIỆN TẠI: {len(final_results)}")
        else:
            print("\n🤷‍♂️ Mẻ này không thu hoạch được khóa nào mới (Có thể do trùng hết hoặc không lấy được kỹ năng).")

    finally:
        driver.quit()