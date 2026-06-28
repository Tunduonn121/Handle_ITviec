"""
benchmark_ranking_strategies.py — P5: ABLATION CHIẾN LƯỢC RANKING (validate việc siết xác định)
==============================================================================================
So 3 cách CHỌN 1 khóa từ shortlist ≤3 của mỗi mốc (blueprint chung, xác định):
  (1) SMART-DET   : chọn khóa hạng 1 theo _relevance_score (HIỆN TẠI - xác định, thông minh)
  (2) BY-ID       : chọn khóa có course_id nhỏ nhất (baseline xác định "ngây thơ")
  (3) LLM         : hỏi LLM chọn 1 trong ≤3 (cách CŨ - không tất định, tốn lời gọi)

Đo 2 trục:
  • PRECISION  (so ground_truth.json): chất lượng khóa chọn ra.
  • TẤT ĐỊNH  (chạy R lần, đo độ trùng khớp Jaccard giữa các lần): reproducibility.
  • Số LỜI GỌI LLM mỗi chiến lược.

=> Kết luận kỳ vọng: SMART-DET đạt precision ≈ hoặc > LLM, tất định 100%, 0 lời gọi LLM
   -> bỏ LLM khỏi ranking được reproducibility mà không mất chất lượng.

CHẠY: py benchmark_ranking_strategies.py --gt ground_truth.json
      (cần DB sạch + test_cases_labeled.json + ground_truth.json đã gán nhãn)
"""
import json, re, argparse, itertools
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.course_ranker import group_courses_by_gap
from services.aliases import clean_and_normalize
from core.config import ollama_client as client, MODEL_NAME

# đếm lời gọi LLM
LLM_CALLS = {"n": 0}

def build_search_gap(gap_raw):
    sg = {}
    for sk, gi in gap_raw.items():
        lv = gi["missing_levels"]
        if gi["match_mode"] == "EXACT":
            sg[clean_and_normalize(gi.get("user_skill_name") or sk)] = lv
        else:
            bm = gi.get("user_best_match")
            if bm:
                m = re.match(r'([^\(]+)(?:\((.*)\))?', bm)
                if m:
                    sg[clean_and_normalize(m.group(1).strip())] = lv
                    if m.group(2):
                        for s in m.group(2).split(','):
                            sg[clean_and_normalize(s.strip())] = lv
    return sg

# ---------- 3 chiến lược chọn 1 khóa/mốc từ shortlist blueprint ----------
def pick_smart_det(blueprint):
    """Khóa hạng 1 (blueprint đã sort theo _relevance_score)."""
    return [courses[0]["course_id"] for courses in blueprint.values() if courses]

def pick_by_id(blueprint):
    """Khóa course_id nhỏ nhất trong shortlist (baseline ngây thơ)."""
    out = []
    for courses in blueprint.values():
        if courses:
            out.append(min(courses, key=lambda c: str(c["course_id"]))["course_id"])
    return out

def pick_llm(blueprint):
    """Hỏi LLM chọn 1 trong ≤3 mỗi mốc (id-constrained). KHÔNG tất định."""
    out = []
    steps = list(blueprint.items())
    chunk = 4
    chosen = {}
    for i in range(0, len(steps), chunk):
        part = dict(steps[i:i+chunk])
        bp_str = json.dumps({k: [{"course_id": c["course_id"], "title": c["title"]} for c in v]
                             for k, v in part.items()}, ensure_ascii=False)
        prompt = (f"Với mỗi Mốc, chọn 1 course_id TỐT NHẤT (phải là mã trong mốc đó).\n{bp_str}\n"
                  f"Trả JSON: {{step: course_id}}")
        try:
            LLM_CALLS["n"] += 1
            r = client.chat(model=MODEL_NAME, messages=[{'role':'user','content':prompt}],
                            stream=False, options={'temperature':0.0}, format='json')
            raw = r['message']['content']; s,e = raw.find('{'), raw.rfind('}')+1
            js = re.sub(r',\s*([}\]])', r'\1', raw[s:e])
            res = json.loads(js)
            for k, v in res.items():
                chosen[k] = v if isinstance(v, str) else (v.get("course_id") if isinstance(v, dict) else None)
        except Exception:
            pass
    for step, courses in blueprint.items():
        valid = {c["course_id"] for c in courses}
        cid = chosen.get(step)
        out.append(cid if cid in valid else (courses[0]["course_id"] if courses else None))
    return [c for c in out if c]

# ---------- đo lường ----------
def precision_vs_gt(picked_ids, gt_labels):
    """Precision = (khóa chọn được gán 1) / (khóa chọn CÓ nhãn). Bỏ khóa chưa gán nhãn."""
    judged = [cid for cid in picked_ids if cid in gt_labels]
    if not judged:
        return None, 0
    hit = sum(1 for cid in judged if int(gt_labels[cid]) == 1)
    return hit / len(judged), len(judged)

def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 1.0

def avg_pairwise_jaccard(runs):
    if len(runs) < 2: return 1.0
    pairs = list(itertools.combinations(runs, 2))
    return sum(jaccard(x, y) for x, y in pairs) / len(pairs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--det_runs", type=int, default=2, help="số lần chạy đo tất định (chiến lược xác định)")
    ap.add_argument("--llm_runs", type=int, default=3, help="số lần chạy đo tất định (LLM)")
    ap.add_argument("--llm_det_tasks", type=int, default=6, help="số task đo tất định LLM (tiết kiệm lời gọi)")
    args = ap.parse_args()

    print("⏳ Nạp cây..."); flat = load_courses_from_sql()
    if not flat: print("❌ DB rỗng."); return
    tree = build_course_tree(flat); state.GLOBAL_COURSE_TREE = tree
    gt = json.load(open(args.gt, encoding="utf-8"))
    cases = {c["task_id"]: c for c in json.load(open("test_cases_labeled.json", encoding="utf-8"))}

    # Tiền xử lý: blueprint cho mỗi task (xác định, tính 1 lần)
    blueprints = {}
    for tid in gt:
        if tid not in cases: continue
        case = cases[tid]
        jd = extract_skills_from_jd(case["jd_text"]); cv = extract_skills_from_cv(case["cv_text"])
        graw, _ = compute_skill_gap(cv, jd)
        if not graw: continue
        sg = build_search_gap(graw)
        cand = [c for c in dfs_tree_search(tree, sg) if isinstance(c, dict)]
        blueprints[tid] = group_courses_by_gap(cand, sg)

    # ===== TRỤC 1: PRECISION =====
    print("\n" + "="*68)
    print("TRỤC 1 — PRECISION (so ground_truth)")
    print("="*68)
    strategies = {"SMART-DET": pick_smart_det, "BY-ID": pick_by_id, "LLM": pick_llm}
    prec_agg = {}
    for name, fn in strategies.items():
        LLM_CALLS["n"] = 0
        tot_p, n_task, tot_calls = 0.0, 0, 0
        for tid, bp in blueprints.items():
            picked = fn(bp)
            p, judged = precision_vs_gt(picked, gt[tid])
            if p is not None:
                tot_p += p; n_task += 1
        prec_agg[name] = (tot_p / n_task if n_task else 0, LLM_CALLS["n"])
        print(f"  {name:10}: Precision TB = {prec_agg[name][0]*100:5.1f}%  | LLM calls = {LLM_CALLS['n']}")

    # ===== TRỤC 2: TẤT ĐỊNH (reproducibility) =====
    print("\n" + "="*68)
    print("TRỤC 2 — TÍNH TẤT ĐỊNH (Jaccard giữa các lần chạy, 1.0 = hoàn toàn tái lập)")
    print("="*68)
    sample_tids = list(blueprints.keys())[:args.llm_det_tasks]
    for name, fn, R in [("SMART-DET", pick_smart_det, args.det_runs),
                        ("BY-ID", pick_by_id, args.det_runs),
                        ("LLM", pick_llm, args.llm_runs)]:
        jsum, jn = 0.0, 0
        for tid in sample_tids:
            runs = [fn(blueprints[tid]) for _ in range(R)]
            jsum += avg_pairwise_jaccard(runs); jn += 1
        print(f"  {name:10}: Jaccard TB = {jsum/jn if jn else 1.0:.3f}  ({R} lần × {len(sample_tids)} task)")

    print("\n" + "="*68)
    print("💡 KỲ VỌNG: SMART-DET precision ≈/> LLM, Jaccard=1.000, 0 lời gọi LLM")
    print("   -> bỏ LLM khỏi ranking: được tái lập 100% + miễn phí, không mất chất lượng.")

if __name__ == "__main__":
    main()