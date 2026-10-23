import os
import json
import pyodbc
import requests
from dotenv import load_dotenv

# ==========================================
# CẤU HÌNH KẾT NỐI (⭐ VÁ: đưa ra .env, path đa nền tảng)
# ==========================================
load_dotenv()
SERVER_NAME   = os.getenv("DB_SERVER", r"LAPTOP-3MUGN234\TUNDUONN")
DATABASE_NAME = os.getenv("DB_NAME", "ITviecMini")
CLEAN_FILE    = os.path.join("data", "clean_courses.json")
RELOAD_URL    = os.getenv("RELOAD_URL", "http://127.0.0.1:8000/api/v1/admin/reload-tree")


def import_clean_data_to_sql():
    conn = None
    cursor = None
    try:
        print("🚀 BẮT ĐẦU BƯỚC LOAD: Đổ dữ liệu siêu sạch vào SQL Server...")

        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        try:
            with open(CLEAN_FILE, "r", encoding="utf-8") as f:
                courses = json.load(f)
        except FileNotFoundError:
            print(f"❌ Lỗi: Không tìm thấy file {CLEAN_FILE}.")
            return

        print(f"📦 Đã tải {len(courses)} khóa học từ {CLEAN_FILE}.")

        # ==========================================================
        # ⭐ VÁ (Mục 2): Đọc MAX id KHÔNG cắt cứng 4 ký tự (tránh lỗi C10000)
        # ==========================================================
        cursor.execute("""
            SELECT MAX(CAST(SUBSTRING(CourseID, 2, LEN(CourseID)) AS INT))
            FROM Courses
            WHERE CourseID LIKE 'C%'
              AND ISNUMERIC(SUBSTRING(CourseID, 2, LEN(CourseID))) = 1
        """)
        max_id = cursor.fetchone()[0]
        course_counter = (max_id or 0) + 1

        inserted_count = 0
        updated_count = 0

        for course in courses:
            title = course.get("title", "N/A")
            url   = course.get("url", "")
            # ⭐ VÁ: None/0/"" -> 1 (vì .get(..,1) KHÔNG cứu được giá trị None)
            level = course.get("level") or 1
            desc  = course.get("description", "")
            cleaned_skills = course.get("target_skills", [])

            if not cleaned_skills or not url:
                continue

            # --- KIỂM TRA KHÓA HỌC CŨ ---
            cursor.execute("SELECT CourseID FROM Courses WHERE url = ?", (url,))
            existing_course = cursor.fetchone()

            if existing_course:
                real_course_id = existing_course[0]
                # ⭐ VÁ (Mục 3): Cập nhật metadata mới (đặc biệt là LEVEL vừa cào lại)
                #    KHÔNG đụng url / CategoryID / SubcategoryID -> giữ nguyên phân loại.
                cursor.execute("""
                    UPDATE Courses
                    SET title = ?, description = ?, level = ?
                    WHERE CourseID = ?
                """, (title, desc, level, real_course_id))

                # ⭐ VÁ (Mục 1 - Lựa chọn 1): Dọn sạch link skill CŨ của ĐÚNG khóa này
                #    trước khi nối skill mới -> đồng bộ với luận văn 3.4.1.4 (Data Integrity).
                cursor.execute("DELETE FROM Course_Skills WHERE CourseID = ?", (real_course_id,))
                updated_count += 1
            else:
                real_course_id = f"C{course_counter:04d}"  # đệm tối thiểu 4 số, >9999 vẫn đúng
                cursor.execute("""
                    INSERT INTO Courses (CourseID, title, description, level, url)
                    VALUES (?, ?, ?, ?, ?)
                """, (real_course_id, title, desc, level, url))
                course_counter += 1
                inserted_count += 1

            # --- NỐI LẠI CÁC KỸ NĂNG MỚI ĐÃ ĐƯỢC LÀM SẠCH ---
            for skill in cleaned_skills:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM Skills WHERE SkillName = ?)
                    BEGIN
                        INSERT INTO Skills (SkillName) VALUES (?)
                    END
                """, (skill, skill))

                cursor.execute("SELECT SkillID FROM Skills WHERE SkillName = ?", (skill,))
                skill_id = cursor.fetchone()[0]

                # Sau khi đã DELETE link cũ ở trên, IF NOT EXISTS ở đây chỉ còn tác dụng
                # chống trùng skill nội bộ trong cùng 1 khóa (phòng skill lặp trong JSON).
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM Course_Skills WHERE CourseID = ? AND SkillID = ?)
                    BEGIN
                        INSERT INTO Course_Skills (CourseID, SkillID) VALUES (?, ?)
                    END
                """, (real_course_id, skill_id, real_course_id, skill_id))

        conn.commit()
        print(f"🎉 NGHIỆM THU THÀNH CÔNG: Nạp mới {inserted_count} khóa, cập nhật {updated_count} khóa cũ.")

        # ==========================================================
        # BÁO CHO FASTAPI SERVER LÀM MỚI CÂY (HOT-RELOAD)
        # ==========================================================
        try:
            print("🚀 Đang gọi API đánh thức FastAPI làm mới Cây Khóa Học trên RAM...")
            response = requests.post(RELOAD_URL, timeout=10)
            if response.status_code == 200:
                print(f"✅ Web Server đã nhận tin: {response.json().get('message')}")
            else:
                print(f"⚠️ Web Server bận/tắt (HTTP {response.status_code}). Sẽ tự lấy DB mới ở lần khởi động sau.")
        except Exception as api_e:
            print(f"⚠️ Không thể kết nối Web Server (có thể đang tắt): {api_e}")

    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng: {e}")
        if conn is not None:
            conn.rollback()
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    import_clean_data_to_sql()