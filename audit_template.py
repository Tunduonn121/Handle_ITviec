"""
audit_template.py — Kiểm template: khóa nào KHÔNG có skill trùng gap (bug?) vs có-nhưng-phụ
============================================================================================
CHẠY: py audit_template.py
Đọc ground_truth_TEMPLATE.json, với mỗi khóa kiểm xem có skill nào khớp gap không.
Nếu nhiều khóa KHÔNG khớp gì -> group_courses_by_gap đang hỏng (bug), không phải tag data.
"""
import json
from services.aliases import is_skill_match, clean_and_normalize

tpl = json.load(open("ground_truth_TEMPLATE.json", encoding="utf-8"))

total = 0
no_match = 0   # khóa KHÔNG có skill nào khớp gap (NGHI BUG)
has_match = 0  # khóa có ít nhất 1 skill khớp gap

print("="*80)
for tid, node in list(tpl.items())[:5]:   # xem 5 task đầu cho gọn
    # lấy tên gap (bỏ phần level trong ngoặc nếu có)
    raw_gap = node.get("_gap_can_hoc", [])
    gaps = [g.split(" (")[0].strip() for g in raw_gap]
    courses = node.get("courses", {})
    print(f"\n### {tid}  gap={gaps}")
    for cid, info in courses.items():
        skills = info.get("skills", [])
        matched = []
        for g in gaps:
            for s in skills:
                if is_skill_match(clean_and_normalize(g), clean_and_normalize(s)):
                    matched.append(f"{g}<-{s}")
                    break
        total += 1
        if matched:
            has_match += 1
            flag = "  ok  "
        else:
            no_match += 1
            flag = "❌BUG?"
        print(f"  {flag} [{cid}] {info.get('title','')[:42]:42} | khớp: {matched if matched else 'KHÔNG KHỚP GÌ'}")

# đếm toàn bộ (mọi task)
total_all = nomatch_all = 0
for tid, node in tpl.items():
    raw_gap = node.get("_gap_can_hoc", [])
    gaps = [g.split(" (")[0].strip() for g in raw_gap]
    for cid, info in node.get("courses", {}).items():
        skills = info.get("skills", [])
        m = any(is_skill_match(clean_and_normalize(g), clean_and_normalize(s))
                for g in gaps for s in skills)
        total_all += 1
        if not m: nomatch_all += 1

print("\n" + "="*80)
print(f"TOÀN BỘ TEMPLATE: {total_all} khóa | KHÔNG khớp gap nào: {nomatch_all} "
      f"({nomatch_all/total_all*100:.0f}%)")
if nomatch_all > total_all * 0.1:
    print("🚨 >10% khóa KHÔNG khớp gap -> group_courses_by_gap CÓ BUG, phải sửa code!")
else:
    print("✅ Hầu hết khóa đều khớp gap (≥1 skill). Các '0' của bạn là do tag PHỤ, không phải bug.")