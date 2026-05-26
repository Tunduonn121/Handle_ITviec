import pyodbc
import json
import os
import re
import time
from tqdm import tqdm
from dotenv import load_dotenv
from ollama import Client
import concurrent.futures

# ==========================================
# CẤU HÌNH API, DATABASE & CÔNG TẮC
# ==========================================
load_dotenv()
api_key = os.getenv("OLLAMA_API_KEY")

client = Client(
    host='https://ollama.com',
    headers={'Authorization': f'Bearer {api_key}'}
)

MODEL_NAME = 'qwen3-coder:480b-cloud'

SERVER_NAME = r'LAPTOP-3MUGN234\TUNDUONN'
DATABASE_NAME = 'ITviecMini'

MAX_WORKERS = 2
RESET_DATABASE_TREE = False

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

TREE_STRUCTURE = "\n".join([f'{i+1}. "{cat}" (Sub: {", ".join([f'"{s}"' for s in subs])})' for i, (cat, subs) in enumerate(VALID_V2_STRUCTURE.items())])


# ==========================================
# FUNCTIONS
# ==========================================
def obliterate_tree(conn):
    print("💥 Đang xóa cây cũ...")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Courses SET CategoryID = NULL, SubcategoryID = NULL")
        cursor.execute("DELETE FROM Subcategories")
        cursor.execute("DELETE FROM Categories")

        try:
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
    cursor = conn.cursor()

    for main_cat, subs in VALID_V2_STRUCTURE.items():
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM Categories WHERE CategoryName = ?)
            INSERT INTO Categories (CategoryName) VALUES (?)
        """, (main_cat, main_cat))

        cursor.execute("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (main_cat,))
        cat_id = cursor.fetchone()[0]
        cat_cache[main_cat] = cat_id

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
    c_id, title, skills = course_data

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
                options={'temperature': 0.0}
            )

            result_text = response['message']['content'].strip()

            match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)

            if not match:
                match = re.search(r'\{.*?\}', result_text, re.DOTALL)

            if match:
                data = json.loads(match.group(1) if "```json" in result_text else match.group(0))

                final_cat = data.get("category", "").strip()
                final_sub = data.get("subcategory", "").strip()

                for m_cat, subs in VALID_V2_STRUCTURE.items():
                    if final_sub in subs:
                        return c_id, title, m_cat, final_sub

                return c_id, title, final_cat, final_sub

        except Exception:
            time.sleep(2)

    return c_id, title, "Uncategorized", "Need Manual Review"


def process_and_save_batch(conn, results, cat_cache, subcat_cache, pbar):
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            with tqdm(total=len(rows), desc="Đang chạy tiếp", unit="khóa") as pbar:
                batch_size = 1 
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


if __name__ == "__main__":
    main()