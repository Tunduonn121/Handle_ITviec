"""
benchmark_prune_strategies.py — P4: ABLATION CHIẾN LƯỢC PRUNE (validate Con đường 1)
====================================================================================
So 3 cách prune cây trên cùng tập test + ground-truth:
  (1) LLM-BY-NAME    : hỏi LLM theo TÊN category (cách cũ, kiểu LLMTreeRec)
  (2) DETERMINISTIC  : giao skill-set 2 tầng (Con đường 1) - 0 lời gọi LLM
  (3) HYBRID         : deterministic + LLM định tuyến category khi deterministic miss

Đo cho mỗi cách: RECALL (giữ được bao nhiêu khóa relevant theo ground-truth),
số LỜI GỌI LLM, thời gian. => Bằng chứng: deterministic không mất recall mà 0 gọi LLM.

CHẠY: py benchmark_prune_strategies.py --gt ground_truth.json
(cần DB sạch + test_cases.json + ground_truth.json đã gán nhãn ở P3)
"""
import json, time, re, argparse

import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.aliases import clean_and_normalize, is_skill_match
import services.tree_searcher as ts

# ---- đếm số lời gọi LLM bằng cách bọc client ----
LLM_CALLS = {"n": 0}
_orig_chat = None
def _wrap_llm():
    global _orig_chat
    from core.config import ollama_client
    _orig_chat = ollama_client.chat
    def counting_chat(*a, **k):
        LLM_CALLS["n"] += 1
        return _orig_chat(*a, **k)
    ollama_client.chat = counting_chat

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

# ===== Chiến lược 1: LLM-BY-NAME (tái hiện cách cũ trên cấu trúc cây mới) =====
def prune_llm_by_name(tree, gap_dict):
    from core.config import ollama_client as client, MODEL_NAME
    out = []
    gap_skills = list(gap_dict.keys())
    def llm_says(node_name):
        prompt = (f'Danh mục "{node_name}" có chứa khóa học dạy MỘT TRONG các kỹ năng '
                  f'{", ".join(gap_skills)} không? Trả lời YES hoặc NO.')
        try:
            r = client.chat(model=MODEL_NAME, messages=[{'role':'user','content':prompt}],
                            stream=False, options={'temperature':0.0})
            return bool(re.search(r'\bYES\b', r['message']['content'].upper()))
        except Exception:
            return True
    for cat, cnode in tree.items():
        if not llm_says(cat):
            continue
        for sub, snode in cnode["_subs"].items():
            if llm_says(f"{cat} -> {sub}"):
                out.extend(snode["_courses"])
    return out

# ===== Chiến lược 2 & 3 dùng dfs_tree_search của Con đường 1 =====
def prune_deterministic(tree, gap_dict):
    return [c for c in ts.dfs_tree_search(tree, gap_dict, use_llm_routing=False) if isinstance(c, dict)]
def prune_hybrid(tree, gap_dict):
    return [c for c in ts.dfs_tree_search(tree, gap_dict, use_llm_routing=True) if isinstance(c, dict)]

def recall_vs_gt(candidate_ids, relevant_ids):
    """Recall = (khóa relevant theo GT mà prune GIỮ được) / (tổng relevant theo GT)."""
    if not relevant_ids:
        return None
    kept = len(set(candidate_ids) & set(relevant_ids))
    return kept / len(relevant_ids)

def run_strategy(name, fn, tree, search_gap):
    LLM_CALLS["n"] = 0
    t = time.perf_counter()
    cand = fn(tree, search_gap)
    dt = (time.perf_counter()-t)*1000
    ids = [c.get("course_id") or c.get("id") for c in cand]
    return ids, LLM_CALLS["n"], dt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True, help="ground_truth.json (từ P3)")
    args = ap.parse_args()

    print("⏳ Nạp cây + bọc đếm LLM...")
    flat = load_courses_from_sql()
    if not flat:
        print("❌ DB rỗng."); return
    tree = build_course_tree(flat)
    _wrap_llm()

    gt = json.load(open(args.gt, encoding="utf-8"))
    cases = json.load(open("test_cases.json", encoding="utf-8"))
    case_by_id = {c["task_id"]: c for c in cases}

    agg = {"LLM-BY-NAME": [0,0,0,0], "DETERMINISTIC": [0,0,0,0], "HYBRID": [0,0,0,0]}
    # [tổng recall, số task, tổng lời gọi LLM, tổng ms]
    strategies = [("LLM-BY-NAME", prune_llm_by_name),
                  ("DETERMINISTIC", prune_deterministic),
                  ("HYBRID", prune_hybrid)]

    for task_id, labels in gt.items():
        relevant_ids = [cid for cid, lbl in labels.items() if int(lbl) == 1]
        if not relevant_ids or task_id not in case_by_id:
            continue
        case = case_by_id[task_id]
        jd = extract_skills_from_jd(case["jd_text"]); cv = extract_skills_from_cv(case["cv_text"])
        gap_raw, _ = compute_skill_gap(cv, jd)
        if not gap_raw: continue
        search_gap = build_search_gap(gap_raw)

        for name, fn in strategies:
            ids, calls, ms = run_strategy(name, fn, tree, search_gap)
            r = recall_vs_gt(ids, relevant_ids)
            if r is None: continue
            agg[name][0] += r; agg[name][1] += 1; agg[name][2] += calls; agg[name][3] += ms

    print("\n" + "="*70)
    print(f"{'Chiến lược':>16} | {'Recall TB':>10} | {'LLM calls TB':>13} | {'ms TB':>8}")
    print("-"*70)
    for name, _ in strategies:
        s = agg[name]
        if s[1] == 0: continue
        print(f"{name:>16} | {s[0]/s[1]*100:>9.1f}% | {s[2]/s[1]:>13.1f} | {s[3]/s[1]:>7.1f}")
    print("="*70)
    print("\n💡 Kỳ vọng: DETERMINISTIC recall ≈ hoặc > LLM-BY-NAME mà 0 lời gọi LLM.")
    print("   HYBRID recall cao nhất (bù từ vựng) với ít lời gọi. -> validate Con đường 1.")

if __name__ == "__main__":
    main()