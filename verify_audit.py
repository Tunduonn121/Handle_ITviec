"""
verify_audit.py — Vì sao audit báo 'KHÔNG KHỚP' nhưng khóa vẫn vào template?
===========================================================================
Lấy các khóa _source và kiểm: chúng khớp gap qua course_matches_gap (có level)
hay không? Audit (chỉ skill) vs course_matches_gap (skill+level) khác nhau ở đâu.
CHẠY: py verify_audit.py
"""
import json
from services.aliases import is_skill_match, clean_and_normalize, is_level_fit

tpl = json.load(open("ground_truth_TEMPLATE.json", encoding="utf-8"))

# build_search_gap tái dựng từ _gap_can_hoc? Không — _gap_can_hoc đã mất match_mode.
# Thay vào đó kiểm trực tiếp: với mỗi khóa trong template, skill có khớp tên gap không
# (audit cách) VÀ liệt kê _source để biết nó là recommended hay sample.
src_count = {"recommended": [0,0], "sample": [0,0]}  # [tổng, không-khớp-skill]
examples = []

for tid, node in tpl.items():
    raw_gap = node.get("_gap_can_hoc", [])
    gaps = [g.split(" (")[0].strip() for g in raw_gap]
    for cid, info in node.get("courses", {}).items():
        src = info.get("_source", "?")
        skills = info.get("skills", [])
        matched = any(is_skill_match(clean_and_normalize(g), clean_and_normalize(s))
                      for g in gaps for s in skills)
        if src not in src_count: src_count[src] = [0,0]
        src_count[src][0] += 1
        if not matched:
            src_count[src][1] += 1
            if len(examples) < 12:
                examples.append((tid, cid, src, info.get("title","")[:40], gaps, skills))

print("="*70)
print("Khóa KHÔNG khớp skill gap, theo _source:")
for src, (tot, nm) in src_count.items():
    print(f"  {src:12}: {nm}/{tot} không khớp skill")
print("\nVí dụ khóa 'không khớp' + skill thật của nó:")
for tid, cid, src, title, gaps, skills in examples:
    print(f"\n  [{cid}] ({src}) {title}")
    print(f"     gap={gaps}")
    print(f"     skills={skills}")
print("\n" + "="*70)
print(">> Nếu phần lớn KHÔNG-khớp là _source='sample': KHÔNG phải bug.")
print("   (sample lấy từ pool lọc theo skill+LEVEL; có thể khớp qua skill khác")
print("    audit không bắt, hoặc khớp diện rộng. Sẽ kiểm tiếp nếu cần.)")
print(">> Nếu KHÔNG-khớp xuất hiện ở _source='recommended': cần xem kỹ.")