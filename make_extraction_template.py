"""
make_extraction_template.py — P1: SINH TEMPLATE GÁN NHÃN SKILL-JD (ground truth cho trích xuất)
================================================================================================
P1 đo: LLM trích xuất skill từ JD GIỎI hơn keyword baseline tới đâu, SO VỚI nhãn người gán.
Để đo được, cần một "đáp án vàng" (gold) skill cho mỗi JD do NGƯỜI xác định — file này
sinh ra khung để bạn điền.

Sinh ra: extraction_gold_TEMPLATE.json
  {task_id: {
      "domain": "...", "gap_type": "...",
      "jd_text": "<nguyên văn JD>",
      "_llm_suggested": ["..."],     # CHỈ là gợi ý của LLM để bạn tham khảo — KHÔNG phải đáp án
      "gold_skills": [],             # << BẠN ĐIỀN: danh sách skill JD THỰC SỰ yêu cầu (chuẩn hóa)
      "gold_levels": {}              # << (TÙY CHỌN) {skill: level 1-3} nếu muốn đo cả độ chính xác level
  }}

QUY TẮC ĐIỀN gold_skills (để công bằng và nhất quán với hệ thống):
  • Viết tên skill ở dạng CHUẨN, thường (vd: "ci/cd", "terraform", "linux", "sql server").
  • Nhóm "HOẶC" (disjunction) viết bằng dấu | trong MỘT chuỗi: vd JD "C# hoặc Java" -> "c#|java".
  • Nhóm trong ngoặc (vd "AI tools (Copilot, ChatGPT)") -> chỉ lấy tool bên trong: "copilot|chatgpt".
  • CHỈ lấy hard tech skill. BỎ soft skill / phương pháp (Agile, Scrum, communication) và raw tool
    nếu hệ thống coi là nhiễu — nhưng cứ điền theo ĐÁNH GIÁ ĐỘC LẬP của bạn về cái JD đòi hỏi;
    đừng chỉ copy _llm_suggested (nếu copy thì phép đo thành "LLM tự chấm LLM" = vô nghĩa).
  • Phân vân thì đọc lại JD, quyết theo nghĩa văn bản, không theo gợi ý máy.

CHẠY: py make_extraction_template.py            # mặc định 36 JD trong test_cases_labeled.json
      py make_extraction_template.py --n 20     # chỉ lấy 20 JD (cân bằng domain)
      py make_extraction_template.py --src test_cases.json
⚠️ ĐỪNG chạy lại sau khi đã bắt đầu điền (sẽ ghi đè mất nhãn). File tự né ghi đè nếu đã tồn tại.
"""
import json, argparse, os
from collections import defaultdict

from services.skill_extractor import extract_skills_from_jd
from services.aliases import clean_and_normalize


def llm_suggest(jd_text):
    """Chạy LLM trích xuất -> list chuỗi skill (giữ nguyên nhóm | của ANY). CHỈ để tham khảo."""
    try:
        d = extract_skills_from_jd(jd_text)
    except Exception as e:
        print(f"   ⚠️ LLM lỗi 1 JD: {e}")
        return []
    out = []
    for name in d.keys():
        # name có thể là "c#|java" cho ANY; chuẩn hóa từng nhánh nhưng giữ dấu |
        parts = [clean_and_normalize(p.strip()) for p in name.split("|")]
        out.append("|".join(parts))
    return out


def balanced_pick(cases, n):
    """Lấy n case cân bằng theo domain (round-robin)."""
    if n is None or n >= len(cases):
        return cases
    by_dom = defaultdict(list)
    for c in cases:
        by_dom[c.get("domain", "?")].append(c)
    picked, doms = [], list(by_dom.keys())
    i = 0
    while len(picked) < n:
        d = doms[i % len(doms)]
        if by_dom[d]:
            picked.append(by_dom[d].pop(0))
        i += 1
        if all(len(v) == 0 for v in by_dom.values()):
            break
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="test_cases_labeled.json",
                    help="nguồn JD (mặc định test_cases_labeled.json, 36 cặp)")
    ap.add_argument("--n", type=int, default=None, help="số JD muốn gán nhãn (cân bằng domain)")
    ap.add_argument("--out", default="extraction_gold_TEMPLATE.json")
    args = ap.parse_args()

    if os.path.exists(args.out):
        print(f"⛔ {args.out} đã tồn tại — KHÔNG ghi đè để tránh mất nhãn.")
        print("   Muốn sinh mới: xóa/đổi tên file cũ, hoặc dùng --out tên_khác.json")
        return

    cases = json.load(open(args.src, encoding="utf-8"))
    cases = balanced_pick(cases, args.n)
    print(f"⏳ Sinh template cho {len(cases)} JD (gọi LLM để lấy gợi ý)...")

    tpl = {}
    for i, c in enumerate(cases, 1):
        tid = c["task_id"]
        sug = llm_suggest(c["jd_text"])
        tpl[tid] = {
            "domain": c.get("domain", ""),
            "gap_type": c.get("gap_type", ""),
            "jd_text": c["jd_text"],
            "_llm_suggested": sug,
            "gold_skills": [],
            "gold_levels": {},
        }
        print(f"   [{i}/{len(cases)}] {tid:>10} | gợi ý: {sug}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(tpl, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Đã ghi {args.out} ({len(tpl)} JD).")
    print("👉 Mở file, điền 'gold_skills' (và tùy chọn 'gold_levels') theo đánh giá ĐỘC LẬP.")
    print("   Xong thì chạy: py benchmark_extraction.py --gold extraction_gold_TEMPLATE.json")


if __name__ == "__main__":
    main()