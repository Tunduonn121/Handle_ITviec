"""
inspect_runs.py — In title/level/skills của các khóa hệ thống GỢI Ý THẬT (system_runs.json)
==========================================================================================
Để kiểm xem recommendations thật có khớp gap không (khác với pool thô).
CHẠY: py inspect_runs.py --task task_001
      py inspect_runs.py            (in vài task đầu)
"""
import json, re, argparse
import pyodbc
from core.config import SQL_SERVER_NAME, SQL_DATABASE_NAME

def get_courses(ids):
    if not ids: return {}
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER_NAME};"
        f"DATABASE={SQL_DATABASE_NAME};Trusted_Connection=yes;")
    cur = conn.cursor()
    placeholders = ",".join("?"*len(ids))
    cur.execute(f"""
        SELECT c.CourseID, MAX(c.Title) AS title, MAX(c.level) AS lvl,
               STRING_AGG(s.SkillName, ', ') AS skills
        FROM Courses c
        LEFT JOIN Course_Skills cs ON c.CourseID=cs.CourseID
        LEFT JOIN Skills s ON cs.SkillID=s.SkillID
        WHERE c.CourseID IN ({placeholders})
        GROUP BY c.CourseID
    """, ids)
    out = {}
    for r in cur.fetchall():
        out[r.CourseID] = {"title": r.title, "level": r.lvl,
                           "skills": [x.strip() for x in r.skills.split(',')] if r.skills else []}
    cur.close(); conn.close()
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=None)
    ap.add_argument("--runs", default="system_runs.json")
    args = ap.parse_args()

    runs = json.load(open(args.runs, encoding="utf-8"))
    cases = {c["task_id"]: c for c in json.load(open("test_cases_labeled.json", encoding="utf-8"))}

    tasks = [args.task] if args.task else list(runs.keys())[:3]
    for tid in tasks:
        ids = runs.get(tid, [])
        info = get_courses(ids)
        case = cases.get(tid, {})
        print("\n" + "="*80)
        print(f"TASK {tid}  (domain={case.get('domain')}, gap_type={case.get('gap_type')})")
        print(f"JD: {case.get('jd_text','')}")
        print(f"→ Hệ thống GỢI Ý {len(ids)} khóa:")
        for cid in ids:
            c = info.get(cid, {})
            print(f"  [{cid}] L{c.get('level','?')} {c.get('title','(không tìm thấy)')[:55]}")
            print(f"        skills: {', '.join(c.get('skills', [])[:8])}")

if __name__ == "__main__":
    main()