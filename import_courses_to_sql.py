import json
import pyodbc
import requests

# ==========================================
# CẤU HÌNH KẾT NỐI
# ==========================================
SERVER_NAME = r'LAPTOP-3MUGN234\TUNDUONN' 
DATABASE_NAME = 'ITviecMini'
CLEAN_FILE = r"data\clean_courses.json"

def import_clean_data_to_sql():
    try:
        print("🚀 BẮT ĐẦU BƯỚC LOAD: Đổ dữ liệu siêu sạch vào SQL Server...")
        
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        try:
            with open(CLEAN_FILE, 'r', encoding='utf-8') as f:
                courses = json.load(f)
        except FileNotFoundError:
            print(f"❌ Lỗi: Không tìm thấy file {CLEAN_FILE}.")
            return
            
        print(f"📦 Đã tải {len(courses)} khóa học từ {CLEAN_FILE}.")

        # ==============================================================
        # 🧹 BƯỚC QUAN TRỌNG NHẤT: XÓA SẠCH MỐI NỐI KỸ NĂNG CŨ TRƯỚC KHI NẠP
        # ==============================================================
        #print("🧹 Đang dọn dẹp các Kỹ năng 'rác' cũ trong Database...")
        # cursor.execute("DELETE FROM Course_Skills")
        #print("✅ Đã xóa sạch nối kết cũ! Đang tiến hành nạp tag Kỹ năng mới...\n")
        
        cursor.execute("SELECT MAX(CAST(SUBSTRING(CourseID, 2, 4) AS INT)) FROM Courses WHERE CourseID LIKE 'C%'")
        max_id = cursor.fetchone()[0]
        course_counter = (max_id or 0) + 1 

        inserted_count = 0
        
        for course in courses:
            title = course.get("title", "N/A")
            url = course.get("url", "")
            level = course.get("level", 1)
            desc = course.get("description", "")
            cleaned_skills = course.get("target_skills", [])

            if not cleaned_skills or not url:
                continue 

            # --- KIỂM TRA KHÓA HỌC CŨ ---
            cursor.execute("SELECT CourseID FROM Courses WHERE url = ?", (url,))
            existing_course = cursor.fetchone()

            if existing_course:
                # Vẫn giữ nguyên khóa học cũ (để bảo toàn Category)
                real_course_id = existing_course[0]
            else:
                real_course_id = f"C{course_counter:04d}" 
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
                
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM Course_Skills WHERE CourseID = ? AND SkillID = ?)
                    BEGIN
                        INSERT INTO Course_Skills (CourseID, SkillID) VALUES (?, ?)
                    END
                """, (real_course_id, skill_id, real_course_id, skill_id))

        # DƯỚI ĐÂY LÀ ĐOẠN CUỐI CÙNG CỦA HÀM import_clean_data_to_sql()
        conn.commit()
        print(f"🎉 NGHIỆM THU THÀNH CÔNG: Đã làm sạch toàn bộ Data. Nạp mới {inserted_count} khóa học.")
        
        # ==============================================================
        # 🔔 BƯỚC MỚI: BÁO CHO FASTAPI SERVER LÀM MỚI CÂY (HOT-RELOAD)
        # ==============================================================
        try:
            print("🚀 Đang gọi API đánh thức FastAPI làm mới Cây Khóa Học trên RAM...")
            response = requests.post("http://127.0.0.1:8000/api/v1/admin/reload-tree")
            if response.status_code == 200:
                print(f"✅ Web Server đã nhận tin: {response.json().get('message')}")
            else:
                print(f"⚠️ Web Server đang bận hoặc tắt, nó sẽ tự lấy DB mới ở lần khởi động sau.")
        except Exception as api_e:
             print(f"⚠️ Không thể kết nối tới Web Server (Có thể Sếp đang tắt Web): {api_e}")
        
    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng: {e}")
        if 'conn' in locals(): conn.rollback()
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()


if __name__ == "__main__":
    import_clean_data_to_sql()