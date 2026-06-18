import pyodbc
import json

# =====================================================================
# KHỐI 1: CẤU HÌNH KẾT NỐI DATABASE (SQL SERVER)
# Mục đích: Định nghĩa thông tin Server và Tên Database chứa dữ liệu
# =====================================================================
SERVER_NAME = r'LAPTOP-3MUGN234\TUNDUONN' 
DATABASE_NAME = 'ITviecMini'

# =====================================================================
# KHỐI 2: HÀM KÉO DỮ LIỆU TỪ SQL (DATA EXTRACTION)
# Mục đích: Thực thi câu lệnh SQL phức tạp (JOIN 4 bảng) để gom toàn bộ 
# thông tin Khóa học và Kỹ năng tương ứng vào một danh sách phẳng (Flat List).
# =====================================================================
def load_courses_from_sql():
    """Truy vấn SQL JOIN đa bảng để lấy Cấu trúc 3 Tầng + Full Data Khóa học"""
    try:
        # Khởi tạo kết nối tới SQL Server sử dụng Windows Authentication (Trusted_Connection)
        conn = pyodbc.connect(f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;")
        cursor = conn.cursor()
        
        # 🚀 CÂU LỆNH SQL ĐÃ BỌC THÉP: 
        # - Dùng MAX() để né lỗi GROUP BY đối với chuỗi dài.
        # - Dùng AS để ép tên biến về chữ thường cho Python dễ đọc.
        # - Dùng STRING_AGG để gom nhiều kỹ năng (Skill) của 1 khóa học thành 1 chuỗi cách nhau bởi dấu phẩy.
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
        
        # Tiền xử lý dữ liệu: Chuyển dữ liệu thô từ SQL thành mảng Dictionary chuẩn của Python
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
                # Tách chuỗi kỹ năng được gom bởi STRING_AGG thành mảng list[] chuẩn chỉnh
                "target_skills": [s.strip() for s in row.target_skills.split(',')] if row.target_skills else []
            })
            
        # Đóng kết nối để giải phóng bộ nhớ
        cursor.close()
        conn.close()
        return flat_data
        
    except Exception as e:
        print(f"❌ Lỗi SQL: {e}")
        return []

# =====================================================================
# KHỐI 3: HÀM XÂY DỰNG CÂY PHÂN CẤP (HIERARCHICAL TREE BUILDER)
# Mục đích: Chuyển đổi danh sách phẳng (Flat List) thành Cấu trúc Cây 3 Tầng 
# (Category -> Subcategory -> Mảng Khóa Học) để tối ưu hóa thuật toán DFS tìm kiếm.
# =====================================================================
def build_course_tree(flat_courses_list):
    """
    Gom nhóm thành Cây 3 Tầng: Category -> Subcategory -> [Danh sách khóa học ĐẦY ĐỦ DATA]
    """
    course_tree = {} 

    for item in flat_courses_list:
        cat = item['category']       # Tầng 1: Nhóm ngành lớn (VD "Backend")
        subcat = item['subcategory'] # Tầng 2: Nhóm kỹ năng con (VD "Java Ecosystem")

        # 1. Tạo Tầng 1 (Category) nếu chưa tồn tại trong cây
        if cat not in course_tree:
            course_tree[cat] = {}

        # 2. Tạo Tầng 2 (Subcategory) nếu chưa tồn tại trong nhánh Tầng 1
        if subcat not in course_tree[cat]:
            course_tree[cat][subcat] = []

        # 3. 🚀 TẠO TẦNG 3 (Object Khóa học vũ trang đầy đủ để LLM ranking)
        # Bóc tách các trường thông tin cần thiết từ flat_data
        course_info = {
            "course_id": item['course_id'],
            "title": item['title'],
            "url": item['url'],
            "level": item['level'],
            "target_skills": item['target_skills'],
            "description": item['description']
        }

        # Đẩy khóa học vào đúng nhánh (lá) của cây
        course_tree[cat][subcat].append(course_info)

    # CẢNH BÁO: đếm khóa chưa phân loại để biết auto_categorize đã chạy đủ chưa
    unknown_count = 0
    if "Unknown" in course_tree:
        unknown_count = sum(len(courses) for courses in course_tree["Unknown"].values())
    if unknown_count > 0:
        print(f"⚠️ CẢNH BÁO: {unknown_count} khóa học CHƯA phân loại (nằm trong nhánh 'Unknown').")
        print("   -> Hãy chạy: py services\\auto_categorize_db.py  rồi khởi động lại server.")

    return course_tree

# =====================================================================
# KHỐI 4: KỊCH BẢN CHẠY THỬ NGHIỆM (TESTING BLOCK)
# Mục đích: Kiểm tra xem việc kéo dữ liệu và xây cây có diễn ra thành công không.
# Sẽ in ra console cấu trúc cây để xác thực.
# =====================================================================
# --- PHẦN TEST KIỂM TRA 3 TẦNG ---
if __name__ == "__main__":
    print("⏳ Đang kéo dữ liệu từ SQL và xây Cây 3 Tầng...")
    flat_data = load_courses_from_sql()
    
    if flat_data:
        # Gọi hàm xây cây từ dữ liệu thô
        my_tree = build_course_tree(flat_data)
        
        # Lấy thử một mảng lớn (VD: Backend hoặc Frontend) để in ra xem
        test_cat = list(my_tree.keys())[0] # Lấy mảng đầu tiên tìm thấy
        
        print(f"\n✅ ĐÃ XÂY XONG CÂY! TỔNG SỐ KHÓA HỌC: {len(flat_data)}")
        print(f"\n🌳 Các mảng IT lớn (Tầng 1) hiện có: {list(my_tree.keys())}")
        print(f"\n🌿 Trong mảng '{test_cat}', có các phân mục (Tầng 2) là:")
        print(list(my_tree[test_cat].keys()))
        
        # In thử khóa học của một kỹ năng đầu tiên trong nhóm đó
        first_subcat = list(my_tree[test_cat].keys())[0]
        print(f"\n📚 2 Khóa học tiêu biểu của nhánh '{first_subcat}':")
        # In ra định dạng JSON đẹp mắt để Sếp thấy bây giờ khóa học đã có đủ Level và Skills
        print(json.dumps(my_tree[test_cat][first_subcat][:10], indent=4, ensure_ascii=False))