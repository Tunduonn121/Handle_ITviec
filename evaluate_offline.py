"""
evaluate_offline.py — ĐÁNH GIÁ ĐỘC LẬP (GROUND-TRUTH DO NGƯỜI GÁN NHÃN)
========================================================================
Mục đích: Đo Precision / Recall / F1 THẬT của hệ thống gợi ý khóa học,
so với nhãn do CON NGƯỜI gán (độc lập với logic matcher của hệ thống),
và chạy ablation HAVE vs NO guardrail để chứng minh giá trị của E(c).

CÁCH DÙNG:
  1) Chạy make_labeling_template.py để sinh khung ground_truth.json
  2) Người chấm mở ground_truth.json, điền nhãn 1 (relevant) / 0 (not) cho từng khóa
     (lý tưởng: 2 người chấm -> 2 file -> tính Cohen's kappa)
  3) py evaluate_offline.py --gt ground_truth.json --runs system_runs.json
"""
import json
import argparse
from typing import Dict, List


# ---------------------------------------------------------------------
# 1) ĐỌC DỮ LIỆU
# ---------------------------------------------------------------------
def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------
# 2) PRECISION / RECALL / F1 so với GROUND-TRUTH NGƯỜI GÁN
# ground_truth: { task_id: { course_id: 1|0 } }  (1 = thật sự relevant)
# system_runs : { task_id: [course_id, ...] }    (danh sách hệ thống gợi ý)
# ---------------------------------------------------------------------
def precision_recall_f1(ground_truth: Dict, system_runs: Dict) -> Dict:
    TP = FP = FN = 0
    per_task = {}

    for task_id, recommended in system_runs.items():
        labels = ground_truth.get(task_id, {})
        if not labels:
            continue  # task chưa được gán nhãn -> bỏ qua

        recommended_set = set(recommended)
        # Tập "thật sự relevant" theo người gán (nhãn = 1) trong TOÀN BỘ pool đã gán
        relevant_set = {cid for cid, lbl in labels.items() if int(lbl) == 1}

        tp = len(recommended_set & relevant_set)
        fp = len([c for c in recommended_set if labels.get(c, 0) == 0])  # gợi ý nhưng người gán nói KHÔNG
        fn = len(relevant_set - recommended_set)                        # relevant nhưng hệ thống bỏ sót

        TP += tp; FP += fp; FN += fn
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        per_task[task_id] = {"precision": p, "recall": r, "f1": f1, "tp": tp, "fp": fp, "fn": fn}

    P = TP / (TP + FP) if (TP + FP) else 0.0
    R = TP / (TP + FN) if (TP + FN) else 0.0
    F1 = 2 * P * R / (P + R) if (P + R) else 0.0
    return {"precision": P, "recall": R, "f1": F1, "TP": TP, "FP": FP, "FN": FN, "per_task": per_task}


# ---------------------------------------------------------------------
# 3) COHEN'S KAPPA (độ đồng thuận giữa 2 người gán nhãn)
# ---------------------------------------------------------------------
def cohen_kappa(gt_a: Dict, gt_b: Dict) -> float:
    pairs = []
    for task_id in set(gt_a) & set(gt_b):
        a, b = gt_a[task_id], gt_b[task_id]
        for cid in set(a) & set(b):
            pairs.append((int(a[cid]), int(b[cid])))
    if not pairs:
        return float("nan")
    n = len(pairs)
    po = sum(1 for x, y in pairs if x == y) / n
    # xác suất đồng thuận ngẫu nhiên
    a1 = sum(1 for x, _ in pairs if x == 1) / n
    b1 = sum(1 for _, y in pairs if y == 1) / n
    pe = a1 * b1 + (1 - a1) * (1 - b1)
    return (po - pe) / (1 - pe) if (1 - pe) else float("nan")


# ---------------------------------------------------------------------
# 4) IN BÁO CÁO
# ---------------------------------------------------------------------
def print_report(title: str, res: Dict):
    print("\n" + "=" * 64)
    print(f"📊 {title}")
    print("=" * 64)
    print(f"  Precision = {res['precision']*100:5.1f}%   "
          f"Recall = {res['recall']*100:5.1f}%   "
          f"F1 = {res['f1']*100:5.1f}%")
    print(f"  (TP={res['TP']}  FP={res['FP']}  FN={res['FN']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True, help="ground_truth.json (nhãn người gán)")
    ap.add_argument("--runs", required=True,
                    help="system_runs.json: {task_id: [course_id gợi ý CÓ guardrail]}")
    ap.add_argument("--runs_noguard", default=None,
                    help="(tùy chọn) {task_id: [course_id gợi ý KHÔNG guardrail]} để ablation")
    ap.add_argument("--gt2", default=None, help="(tùy chọn) ground_truth của người chấm thứ 2 -> kappa")
    args = ap.parse_args()

    gt = load_json(args.gt)
    runs = load_json(args.runs)

    # --- GP1: Precision/Recall/F1 thật ---
    res = precision_recall_f1(gt, runs)
    print_report("KẾT QUẢ THẬT (so với nhãn người gán) — CÓ guardrail E(c)", res)

    # --- GP2: Ablation (nếu có file không-guardrail) ---
    if args.runs_noguard:
        runs_ng = load_json(args.runs_noguard)
        res_ng = precision_recall_f1(gt, runs_ng)
        print_report("ABLATION — KHÔNG guardrail E(c)", res_ng)
        dp = (res["precision"] - res_ng["precision"]) * 100
        print(f"\n  ➤ Guardrail E(c) thay đổi Precision: {res_ng['precision']*100:.1f}% → "
              f"{res['precision']*100:.1f}%  ({dp:+.1f} điểm %)")

    # --- Cohen's kappa (nếu có 2 người gán) ---
    if args.gt2:
        gt2 = load_json(args.gt2)
        k = cohen_kappa(gt, gt2)
        print(f"\n🤝 Cohen's kappa (đồng thuận 2 người gán): {k:.3f}")
        lvl = ("rất tốt" if k > 0.8 else "tốt" if k > 0.6 else "trung bình" if k > 0.4 else "yếu")
        print(f"   -> Mức đồng thuận: {lvl}")

    print()


if __name__ == "__main__":
    main()