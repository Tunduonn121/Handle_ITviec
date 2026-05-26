import pyodbc
import json

# ==========================================
# CẤU HÌNH KẾT NỐI DATABASE
# ==========================================
SERVER_NAME = r'LAPTOP-3MUGN234\TUNDUONN' 
DATABASE_NAME = 'ITviecMini'

def load_courses_from_sql():
    """Truy vấn SQL JOIN đa bảng để lấy Cấu trúc 3 Tầng + Full Data Khóa học"""
    try:
        conn = pyodbc.connect(f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;")
        cursor = conn.cursor()
        
        # 🚀 CÂU LỆNH SQL ĐÃ BỌC THÉP: 
        # - Dùng MAX() để né lỗi GROUP BY đối với chuỗi dài.
        # - Dùng AS để ép tên biến về chữ thường cho Python dễ đọc.
        query = """
            SELECT 
                MAX(cat.CategoryName) AS category_name,
                MAX(sub.SubcategoryName) AS subcategory_name,
                c.CourseID AS course_id,
                MAX(c.Title) AS title,
                MAX(c.URL) AS url,
                MAX(c.level) AS course_level,
                MAX(CAST(c.Description AS NVARCHAR(4000))) AS description,
                STRING_AGG(s.SkillName, ', ') AS target_skills
            FROM Courses c
            LEFT JOIN Categories cat ON c.CategoryID = cat.CategoryID
            LEFT JOIN Subcategories sub ON c.SubcategoryID = sub.SubcategoryID
            LEFT JOIN Course_Skills cs ON c.CourseID = cs.CourseID
            LEFT JOIN Skills s ON cs.SkillID = s.SkillID
            GROUP BY c.CourseID
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        flat_data = []
        for row in rows:
            flat_data.append({
                "category": row.category_name if row.category_name else "Unknown",
                "subcategory": row.subcategory_name if row.subcategory_name else "Unknown",
                "course_id": row.course_id,
                "title": row.title,
                "url": row.url,
                "level": row.course_level if row.course_level else 1,
                "description": row.description if row.description else "",
                # Tách chuỗi thành mảng list[] chuẩn chỉnh
                "target_skills": [s.strip() for s in row.target_skills.split(',')] if row.target_skills else []
            })
            
        cursor.close()
        conn.close()
        return flat_data
        
    except Exception as e:
        print(f"❌ Lỗi SQL: {e}")
        return []

def build_course_tree(flat_courses_list):
    """
    Gom nhóm thành Cây 3 Tầng: Category -> Subcategory -> [Danh sách khóa học ĐẦY ĐỦ DATA]
    """
    course_tree = {} 

    for item in flat_courses_list:
        cat = item['category']       # Tầng 1: VD "Backend"
        subcat = item['subcategory'] # Tầng 2: VD "Java Ecosystem"

        # 1. Tạo Tầng 1 (Category) nếu chưa có
        if cat not in course_tree:
            course_tree[cat] = {}

        # 2. Tạo Tầng 2 (Subcategory) nếu chưa có
        if subcat not in course_tree[cat]:
            course_tree[cat][subcat] = []

        # 3. 🚀 TẠO TẦNG 3 (Object Khóa học vũ trang đầy đủ để LLM ranking)
        course_info = {
            "course_id": item['course_id'],
            "title": item['title'],
            "url": item['url'],
            "level": item['level'],
            "target_skills": item['target_skills'],
            "description": item['description']
        }

        # Đẩy khóa học vào đúng nhánh
        course_tree[cat][subcat].append(course_info)

    return course_tree

# --- PHẦN TEST KIỂM TRA 3 TẦNG ---
if __name__ == "__main__":
    print("⏳ Đang kéo dữ liệu từ SQL và xây Cây 3 Tầng...")
    flat_data = load_courses_from_sql()
    
    if flat_data:
        my_tree = build_course_tree(flat_data)
        
        # Lấy thử một mảng lớn (VD: Backend hoặc Frontend) để in ra xem
        test_cat = list(my_tree.keys())[0] # Lấy mảng đầu tiên tìm thấy
        
        print(f"\n✅ ĐÃ XÂY XONG CÂY! TỔNG SỐ KHÓA HỌC: {len(flat_data)}")
        print(f"\n🌳 Các mảng IT lớn (Tầng 1) hiện có: {list(my_tree.keys())}")
        print(f"\n🌿 Trong mảng '{test_cat}', có các phân mục (Tầng 2) là:")
        print(list(my_tree[test_cat].keys()))
        
        # In thử khóa học của một kỹ năng
        first_subcat = list(my_tree[test_cat].keys())[0]
        print(f"\n📚 2 Khóa học tiêu biểu của nhánh '{first_subcat}':")
        # In ra để Sếp thấy bây giờ khóa học đã có đủ Level và Skills
        print(json.dumps(my_tree[test_cat][first_subcat][:10], indent=4, ensure_ascii=False))