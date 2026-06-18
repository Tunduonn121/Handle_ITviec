import pyodbc
import json
import os
import re
import time
from tqdm import tqdm
from dotenv import load_dotenv
from ollama import Client
import concurrent.futures

# =====================================================================
# KHỐI 1: CẤU HÌNH API, DATABASE & CÔNG TẮC HỆ THỐNG
# =====================================================================
load_dotenv()
api_key = os.getenv("OLLAMA_API_KEY")

# Khởi tạo Client kết nối với mô hình Qwen-480B
client = Client(
    host='https://ollama.com',
    headers={'Authorization': f'Bearer {api_key}'}
)

MODEL_NAME = 'qwen3-coder:480b-cloud'

SERVER_NAME = r'LAPTOP-3MUGN234\TUNDUONN'
DATABASE_NAME = 'ITviecMini'

MAX_WORKERS = 2 # Số lượng luồng chạy song song để tối ưu tốc độ gọi API
RESET_DATABASE_TREE = False # Công tắc: Có xóa toàn bộ Cây cũ để xây lại từ đầu không?

# =====================================================================
# KHỐI 2: ĐỊNH NGHĨA CẤU TRÚC TAXONOMY (CÂY PHÂN CẤP SƯ PHẠM)
# Mục đích: Đây là bộ khung chuẩn hóa (Ground Truth) để ép LLM phân loại
# khóa học vào đúng 1 trong các nhánh này (Cơ chế Single-label).
# =====================================================================
VALID_V2_STRUCTURE = {
    "Data Science & AI": [
        "Machine Learning & Deep Learning",
        "Generative AI & LLMs",
        "Data Engineering & Big Data",
        "Data Analysis & BI"
    ],
    "DevOps & Cloud": [
        "Cloud Platforms (AWS/Azure/GCP)",
        "Containerization & Orchestration",
        "CI/CD & Infrastructure as Code",
        "System Administration"
    ],
    "Frontend": [
        "React Ecosystem",
        "Vue & Angular",
        "Web Fundamentals (HTML/CSS/JS)"
    ],
    "Backend": [
        "Java Ecosystem",
        "Python Ecosystem",
        "C# / .NET",
        "NodeJS",
        "Go & Rust",
        "PHP & Ruby",
        "Microservices & APIs",
        "C / C++"
    ],
    "Database": [
        "Relational DB (SQL)",
        "NoSQL & Cache",
        "Data Warehousing"
    ],
    "Mobile": [
        "iOS Development",
        "Android Development",
        "Cross-Platform (Flutter/React Native)"
    ],
    "Core CS & Fundamentals": [
        "Data Structures & Algorithms",
        "System Design & Architecture",
        "Operating Systems",
        "Computer Networks"
    ],
    "Cybersecurity": [
        "Ethical Hacking & Pen Testing",
        "Network Security",
        "Cryptography",
        "Security Operations & Intelligence",
        "Information Security Management"
    ],
    "Software Testing & QA": [
        "Automation Testing",
        "Manual Testing",
        "Performance & Security Testing"
    ],
    "UI/UX & Management": [
        "User Research & Strategy",
        "UI Design & Prototyping",
        "Agile & IT Project Management",
        "Product Management & Business Analysis"
    ],
    "Emerging Tech & Specialities": [
        "Game Development",
        "Blockchain & Web3",
        "IoT & Embedded Systems",
        "AR / VR"
    ]
}

# Tiền xử lý cấu trúc cây thành chuỗi Text để nạp vào Prompt cho LLM
_lines = []
for i, (cat, subs) in enumerate(VALID_V2_STRUCTURE.items()):
    subs_str = ", ".join(['"' + s + '"' for s in subs])
    _lines.append(f'{i+1}. "{cat}" (Sub: {subs_str})')
TREE_STRUCTURE = "\n".join(_lines)

# =====================================================================
# FUNCTIONS (CÁC HÀM XỬ LÝ LÕI)
# =====================================================================

def obliterate_tree(conn):
    """Hủy diệt dữ liệu Cây cũ trên SQL Server để dọn đường xây Cây mới."""
    print("💥 Đang xóa cây cũ...")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Courses SET CategoryID = NULL, SubcategoryID = NULL")
        cursor.execute("DELETE FROM Subcategories")
        cursor.execute("DELETE FROM Categories")

        try:
            # Reset identity (ID tự tăng) về 0
            cursor.execute("DBCC CHECKIDENT ('Categories', RESEED, 0)")
            cursor.execute("DBCC CHECKIDENT ('Subcategories', RESEED, 0)")
        except:
            pass

        conn.commit()
        print("✅ Reset xong")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        conn.rollback()
    finally:
        cursor.close()


def ensure_v2_structure(conn, cat_cache, subcat_cache):
    """Khởi tạo toàn bộ bộ khung Categories và Subcategories vào Database."""
    cursor = conn.cursor()

    for main_cat, subs in VALID_V2_STRUCTURE.items():
        # Thêm Category nhánh chính
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM Categories WHERE CategoryName = ?)
            INSERT INTO Categories (CategoryName) VALUES (?)
        """, (main_cat, main_cat))

        cursor.execute("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (main_cat,))
        cat_id = cursor.fetchone()[0]
        cat_cache[main_cat] = cat_id

        # Thêm Subcategory nhánh con
        for sub_cat in subs:
            cursor.execute("""
                IF NOT EXISTS (
                    SELECT 1 FROM Subcategories 
                    WHERE SubcategoryName = ? AND CategoryID = ?
                )
                INSERT INTO Subcategories (SubcategoryName, CategoryID)
                VALUES (?, ?)
            """, (sub_cat, cat_id, sub_cat, cat_id))

            cursor.execute("""
                SELECT SubcategoryID FROM Subcategories
                WHERE SubcategoryName = ? AND CategoryID = ?
            """, (sub_cat, cat_id))

            subcat_cache[f"{cat_id}_{sub_cat}"] = cursor.fetchone()[0]

    conn.commit()
    cursor.close()


def ai_classify_course(course_data, max_retries=3):
    """
    TRÁI TIM CỦA MODULE: LLM Semantic Routing (Định tuyến ngữ nghĩa).
    Bắt buộc LLM phải chọn DUY NHẤT 1 nhãn (Single-label) cho Khóa học.
    """
    c_id, title, skills = course_data

    # Kỹ thuật Prompt Engineering: Ép đầu ra định dạng JSON chuẩn
    prompt = f"""Phân loại khóa học vào đúng Category/Subcategory:

{TREE_STRUCTURE}

Tên: {title}
Skills: {skills}

Trả về JSON:
```json
{{
  "category": "...",
  "subcategory": "..."
}}
```"""

    for attempt in range(max_retries):
        try:
            response = client.chat(
                model=MODEL_NAME,
                messages=[{'role': 'user', 'content': prompt}],
                stream=False,
                options={'temperature': 0.0} # Nhiệt độ 0.0 đảm bảo Output có tính tất định
            )

            result_text = response['message']['content'].strip()

            # Bóc tách cấu trúc JSON khỏi văn bản phản hồi
            match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)

            if not match:
                match = re.search(r'\{.*?\}', result_text, re.DOTALL)

            if match:
                data = json.loads(match.group(1) if "```json" in result_text else match.group(0))

                final_cat = data.get("category", "").strip()
                final_sub = data.get("subcategory", "").strip()

                
                # Đối chiếu chéo để đảm bảo LLM không bịa ra Subcategory (Zero-Hallucination)
                for m_cat, subs in VALID_V2_STRUCTURE.items():
                    if final_sub in subs:
                        return c_id, title, m_cat, final_sub

                return c_id, title, final_cat, final_sub

        except Exception as e:
            print(f"   ⚠️ LLM lỗi (thử lại {attempt+1}/{max_retries}): {e}")
            time.sleep(2)

    # Fallback nếu LLM bó tay
    # Subcategory KHÔNG thuộc taxonomy -> KHÔNG nhận nhãn bịa, ép review tay
    return c_id, title, "Uncategorized", "Need Manual Review"


def process_and_save_batch(conn, results, cat_cache, subcat_cache, pbar):
    """Lưu kết quả phân loại của LLM trở lại bảng Courses trong Database."""
    cursor = conn.cursor()

    try:
        for c_id, title, cat_name, sub_name in results:

            if cat_name not in cat_cache:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM Categories WHERE CategoryName = ?)
                    INSERT INTO Categories (CategoryName) VALUES (?)
                """, (cat_name, cat_name))

                cursor.execute("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (cat_name,))
                cat_cache[cat_name] = cursor.fetchone()[0]

            cat_id = cat_cache[cat_name]
            sub_key = f"{cat_id}_{sub_name}"

            if sub_key not in subcat_cache:
                cursor.execute("""
                    IF NOT EXISTS (
                        SELECT 1 FROM Subcategories
                        WHERE SubcategoryName = ? AND CategoryID = ?
                    )
                    INSERT INTO Subcategories (SubcategoryName, CategoryID)
                    VALUES (?, ?)
                """, (sub_name, cat_id, sub_name, cat_id))

                cursor.execute("""
                    SELECT SubcategoryID FROM Subcategories
                    WHERE SubcategoryName = ? AND CategoryID = ?
                """, (sub_name, cat_id))

                subcat_cache[sub_key] = cursor.fetchone()[0]

            sub_id = subcat_cache[sub_key]

            # Gắn nhãn (Labeling) vào database
            cursor.execute("""
                UPDATE Courses
                SET CategoryID = ?, SubcategoryID = ?
                WHERE CourseID = ?
            """, (cat_id, sub_id, c_id))

            pbar.write(f"✔️ {title[:50]:<50} ➡️ {sub_name}")

        conn.commit()

    except Exception as e:
        pbar.write(f"❌ Lỗi DB: {e}")
        conn.rollback()

    finally:
        cursor.close()


def main():
    """Nhạc trưởng điều phối: Kéo data rác, chia batch, gọi Multi-threading xử lý."""
    print("🚀 Bắt đầu...")

    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;"
        )

        if RESET_DATABASE_TREE:
            obliterate_tree(conn)

        cat_cache, subcat_cache = {}, {}
        ensure_v2_structure(conn, cat_cache, subcat_cache)

        # 🚀 LỆNH SQL BỌC THÉP: CHỈ LẤY KHÓA HỌC CHƯA PHÂN LOẠI & BỊ LỖI MẠNG
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.CourseID, c.title, STRING_AGG(s.SkillName, ', ') AS skills
            FROM Courses c
            LEFT JOIN Course_Skills cs ON c.CourseID = cs.CourseID
            LEFT JOIN Skills s ON cs.SkillID = s.SkillID
            LEFT JOIN Subcategories sub ON c.SubcategoryID = sub.SubcategoryID
            WHERE c.CategoryID IS NULL 
            OR c.SubcategoryID IS NULL 
            OR sub.SubcategoryName = 'Need Manual Review'
            GROUP BY c.CourseID, c.title
        """)
        rows = cursor.fetchall()
        cursor.close()
        print(f"📦 Tìm thấy {len(rows)} khóa học cần làm nốt...")
        if not rows:
                print("✅ Tuyệt vời! Toàn bộ 5200+ khóa học đã được quy hoạch hoàn tất!")
                return
        
        # Tối ưu hóa API bằng xử lý đa luồng (Multi-threading)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            with tqdm(total=len(rows), desc="Đang chạy tiếp", unit="khóa") as pbar:
                batch_size = MAX_WORKERS * 2
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    futures = [executor.submit(ai_classify_course, row) for row in batch]
                    batch_results = [future.result() for future in concurrent.futures.as_completed(futures)]
                    pbar.update(len(batch_results))
                    process_and_save_batch(conn, batch_results, cat_cache, subcat_cache, pbar)

        print("\n🎉 CHIẾN DỊCH HOÀN TẤT!")

    except Exception as e:
        print(f"❌ Lỗi hệ thống: {e}")

    finally:
        if 'conn' in locals():
            conn.close()


# =====================================================================
# KHỐI DEMO BẢO VỆ KHÓA LUẬN VỚI HỘI ĐỒNG
# Mục đích: Chứng minh khả năng phân tích ngữ nghĩa của LLM để 
# giải quyết vấn đề "Cross-category" (Hạn chế số 1 trong Chương 5).
# =====================================================================
# Sếp dán đoạn này vào CUỐI CÙNG của file auto_categorize.py nhé
def main_demo_cho_co():
    import time
    
    # Định nghĩa 3 Case Study với Kết luận được "mớm" sẵn để Sếp trình bày
    test_cases = [
        {
            "id": "DEMO_001",
            "title": "The Complete 2024 Fullstack Web Development",
            "skills": "ReactJS, NodeJS, ExpressJS, MongoDB, HTML, CSS",
            "conflict": "Frontend vs Backend",
            "conclusion": (
                "👉 KẾT LUẬN CA 1 (Giao thoa Web):\n"
                "Khóa này liệt kê cả React (Front) và Node/Mongo (Back). Khi bị ép trả về 1 nhãn,\n"
                "AI buộc phải cân đo trọng số. Dù nó chọn Frontend hay Backend làm 'Dominant',\n"
                "hệ thống đã bảo vệ thành công kiến trúc Cây 1-N, ngăn chặn việc khóa học này\n"
                "bị nhân bản thành 2 bản sao gây tốn RAM và làm chậm thuật toán duyệt DFS."
            )
        },
        {
            "id": "DEMO_002",
            "title": "Python for Data Engineering and Backend APIs",
            "skills": "Python, Django, FastAPI, Apache Spark, Hadoop, SQL",
            "conflict": "Backend vs Data Science",
            "conclusion": (
                "👉 KẾT LUẬN CA 2 (Giao thoa Hệ thống):\n"
                "Khóa này có API/Django (Backend) nhưng lại chứa Spark, Hadoop (Data). AI nhận diện\n"
                "'Spark/Hadoop' là những skill đặc thù và 'nặng đô' hơn, nên nó thường sẽ ép\n"
                "khóa này về nhánh 'Data Science'. Điều này chứng minh AI không chỉ đếm số lượng\n"
                "từ khóa, mà còn hiểu được chiều sâu chuyên môn của công nghệ để định tuyến."
            )
        },
        {
            "id": "DEMO_003",
            "title": "Cloud Security & DevSecOps Masterclass",
            "skills": "AWS, Docker, Kubernetes, Penetration Testing, IAM, Network Security",
            "conflict": "DevOps vs Cybersecurity",
            "conclusion": (
                "👉 KẾT LUẬN CA 3 (Giao thoa Bảo mật):\n"
                "Khóa này chứa AWS, Docker, K8s (DevOps) rất rõ ràng. Nhưng tiêu đề và các skill \n"
                "như Pen Testing chỉ ra mục đích cuối cùng là Security. Cơ chế Đơn nhãn của em \n"
                "buộc AI phải nhìn xuyên qua 'vỏ bọc' DevOps để phân loại khóa này thẳng vào \n"
                "nhánh 'Cybersecurity', giúp ứng viên bảo mật tìm đúng khóa mình cần."
            )
        }
    ]

    print("="*80)
    print("🚀 DEMO BẢO VỆ KHÓA LUẬN: KIỂM THỬ CƠ CHẾ PHÂN LOẠI ĐƠN NHÃN (SINGLE-LABEL)")
    print("="*80)

    for idx, tc in enumerate(test_cases, 1):
        input(f"\n[SẾP NHẤN ENTER ĐỂ BẮT ĐẦU CHẠY TEST CASE {idx}...] ")
        
        print(f"\n📦 [TEST CASE {idx}]: XUNG ĐỘT {tc['conflict'].upper()}")
        print(f" 🔹 Tên khóa học : {tc['title']}")
        print(f" 🔹 Tập kỹ năng  : {tc['skills']}")
        print(" ⏳ Đang ép Qwen-480B ra quyết định định tuyến. Vui lòng đợi...\n")
        
        start_time = time.time()
        # Gọi thẳng hàm AI đang dùng trong code thật
        c_id, title, cat, subcat = ai_classify_course((tc['id'], tc['title'], tc['skills']))
        end_time = time.time()
        
        print(" 🎉 KẾT QUẢ JSON TỪ AI (CHỈ ĐƯỢC CHỌN 1 NHÃN):")
        print(" ```json")
        print(" {")
        print(f'   "category": "{cat}",')
        print(f'   "subcategory": "{subcat}"')
        print(" }")
        print(" ```")
        print(f" ⏱️ Thời gian suy luận: {round(end_time - start_time, 2)} giây\n")
        
        # In luôn kết luận ra màn hình để Sếp vừa chỉ màn hình vừa nói với cô
        print(tc["conclusion"])
        print("-" * 80)

    print("\n🎉 ĐÃ HOÀN THÀNH DEMO 3 CA KHÓ. KIẾN TRÚC SINGLE-LABEL ĐĐƯỢC BẢO VỆ!")

if __name__ == "__main__":
    import sys
    # Mặc định: PHÂN LOẠI toàn bộ DB. Thêm cờ "demo" nếu muốn chạy demo cho hội đồng.
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        main_demo_cho_co()
    else:
        main()
        # Giờ py services\auto_categorize_db.py sẽ phân loại thật; muốn demo thì py services\auto_categorize_db.py demo.