"""
check_categorization.py — KIỂM TRA CHẤT LƯỢNG PHÂN LOẠI (random N khóa)
======================================================================
Lấy N khóa ngẫu nhiên ĐÃ phân loại, in ra: Title | Category > Subcategory | Skills
để bạn SOI MẮT xem có hợp lý không. Kèm cờ cảnh báo tự động khi nghi sai.

CHẠY: py check_categorization.py            (mặc định 100 khóa)
      py check_categorization.py --n 50     (50 khóa)
      py check_categorization.py --suspect  (chỉ in các khóa NGHI sai)
"""
import argparse
import pyodbc
from core.config import SQL_SERVER_NAME, SQL_DATABASE_NAME
from services.aliases import is_skill_match, clean_and_normalize

# Lấy taxonomy để biết Category nào "nên" chứa skill gì (heuristic cảnh báo nhẹ)
from services.auto_categorize_db import VALID_V2_STRUCTURE

def fetch_random(n, only_suspect):
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER_NAME};"
        f"DATABASE={SQL_DATABASE_NAME};Trusted_Connection=yes;"
    )
    cur = conn.cursor()
    cur.execute(f"""
        SELECT TOP {n}
            c.CourseID,
            MAX(c.Title) AS title,
            MAX(cat.CategoryName) AS category,
            MAX(sub.SubcategoryName) AS subcategory,
            STRING_AGG(s.SkillName, ', ') AS skills
        FROM Courses c
        LEFT JOIN Categories cat ON c.CategoryID = cat.CategoryID
        LEFT JOIN Subcategories sub ON c.SubcategoryID = sub.SubcategoryID
        LEFT JOIN Course_Skills cs ON c.CourseID = cs.CourseID
        LEFT JOIN Skills s ON cs.SkillID = s.SkillID
        WHERE cat.CategoryName IS NOT NULL AND cat.CategoryName <> 'Uncategorized'
        GROUP BY c.CourseID
        ORDER BY NEWID()
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def category_skill_pool(category):
    """Gom tất cả tên subcategory của 1 category làm 'gợi ý ngữ nghĩa' để so khớp thô."""
    subs = VALID_V2_STRUCTURE.get(category, [])
    return [category.lower()] + [s.lower() for s in subs]

def looks_suspect(category, subcategory, skills):
    """Cờ NGHI SAI (heuristic nhẹ): không skill nào của khóa khớp tên cat/sub."""
    if not skills:
        return True  # không có skill -> khó tin phân loại đúng
    pool = category_skill_pool(category) + [subcategory.lower()]
    for sk in skills:
        sk_n = clean_and_normalize(sk)
        for p in pool:
            if is_skill_match(sk_n, p) or sk_n in p or p in sk_n:
                return False  # có ít nhất 1 skill ăn khớp -> tạm ổn
    return True  # không skill nào khớp -> NGHI

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--suspect", action="store_true", help="chỉ in khóa nghi sai")
    args = ap.parse_args()

    rows = fetch_random(args.n, args.suspect)
    shown = suspect_count = 0
    print(f"\n{'='*100}\n🔍 KIỂM TRA {len(rows)} KHÓA NGẪU NHIÊN (cờ ⚠️ = nghi phân loại sai)\n{'='*100}")
    for r in rows:
        skills = [s.strip() for s in r.skills.split(',')] if r.skills else []
        suspect = looks_suspect(r.category, r.subcategory or "", skills)
        if suspect: suspect_count += 1
        if args.suspect and not suspect:
            continue
        flag = "⚠️ NGHI" if suspect else "  ✅  "
        shown += 1
        print(f"\n{flag} [{r.CourseID}] {r.title[:60]}")
        print(f"      📂 {r.category} > {r.subcategory}")
        print(f"      🧩 {', '.join(skills[:8])}{'...' if len(skills)>8 else ''}")

    print(f"\n{'='*100}")
    print(f"📊 Tổng: {len(rows)} khóa | Nghi sai (heuristic): {suspect_count} "
          f"({suspect_count/len(rows)*100:.0f}%)")
    print("⚠️ LƯU Ý: cờ 'nghi' chỉ là heuristic thô (skill không khớp tên cat/sub).")
    print("   Bạn vẫn nên SOI MẮT vài chục khóa để đánh giá thật. Heuristic có thể báo nhầm.")

if __name__ == "__main__":
    main()