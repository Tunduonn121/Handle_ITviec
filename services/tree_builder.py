import pyodbc
import json
from core.config import SQL_SERVER_NAME, SQL_DATABASE_NAME
from services.aliases import clean_and_normalize

# =====================================================================
# KHỐI 1: KÉO DỮ LIỆU TỪ SQL (giữ nguyên logic cũ)
# =====================================================================
def load_courses_from_sql():
    """Truy vấn SQL JOIN đa bảng để lấy Category/Subcategory + full data khóa học."""
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER_NAME};"
            f"DATABASE={SQL_DATABASE_NAME};Trusted_Connection=yes;"
        )
        cursor = conn.cursor()
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
                "target_skills": [s.strip() for s in row.target_skills.split(',')] if row.target_skills else []
            })
        cursor.close(); conn.close()
        return flat_data
    except Exception as e:
        print(f"❌ Lỗi SQL: {e}")
        return []

# =====================================================================
# KHỐI 2: XÂY CÂY + PRECOMPUTE SKILL-SET (CON ĐƯỜNG 1)
# Cấu trúc cây MỚI (giữ CẢ Category + Subcategory):
#   tree = {
#     cat: {
#       "_skills": set(...),          # gom skill (đã chuẩn hóa) của CẢ category
#       "_subs": {
#         sub: {"_skills": set(...), "_courses": [course_info, ...]}
#       }
#     }
#   }
# Skill-set precompute 1 lần lúc build -> DFS prune bằng phép GIAO, không gọi LLM.
# =====================================================================
def build_course_tree(flat_courses_list):
    course_tree = {}
    for item in flat_courses_list:
        cat = item['category']
        subcat = item['subcategory']

        course_tree.setdefault(cat, {"_skills": set(), "_subs": {}})
        course_tree[cat]["_subs"].setdefault(subcat, {"_skills": set(), "_courses": []})

        course_info = {
            "course_id": item['course_id'],
            "title": item['title'],
            "url": item['url'],
            "level": item['level'],
            "target_skills": item['target_skills'],
            "description": item['description'],
        }
        course_tree[cat]["_subs"][subcat]["_courses"].append(course_info)

        # ⭐ PRECOMPUTE: gom skill đã chuẩn hóa lên Subcategory và Category
        norm = {clean_and_normalize(s) for s in item['target_skills']}
        course_tree[cat]["_subs"][subcat]["_skills"] |= norm
        course_tree[cat]["_skills"] |= norm

    # Cảnh báo khóa chưa phân loại
    if "Unknown" in course_tree:
        unknown_count = sum(len(sub["_courses"]) for sub in course_tree["Unknown"]["_subs"].values())
        if unknown_count > 0:
            print(f"⚠️ CẢNH BÁO: {unknown_count} khóa CHƯA phân loại (nhánh 'Unknown').")
            print("   -> Chạy: py -m services.auto_categorize_db  rồi khởi động lại server.")

    return course_tree


if __name__ == "__main__":
    flat = load_courses_from_sql()
    if not flat:
        print("❌ Cây rỗng! Kiểm tra DB.")
    else:
        tree = build_course_tree(flat)
        print(f"✅ Cây: {len(tree)} category.")
        for cat, node in list(tree.items())[:5]:
            print(f"  {cat}: {len(node['_subs'])} sub, {len(node['_skills'])} skill gom")