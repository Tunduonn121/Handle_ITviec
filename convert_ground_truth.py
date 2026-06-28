"""
convert_ground_truth.py — chuyển template ĐÃ GÁN NHÃN (dễ đọc) sang định dạng phẳng
====================================================================================
Template (ground_truth_TEMPLATE.json sau khi bạn điền) có dạng:
  {task: {"_gap_can_hoc":[...], "_cv":..., "_jd":..., "courses": {cid: {..., "label": 1|0}}}}

Script này rút thành định dạng phẳng cho evaluate_offline.py & benchmark_prune_strategies.py:
  {task: {cid: 1|0}}

CHẠY: py convert_ground_truth.py
  (đọc ground_truth_TEMPLATE.json đã điền -> ghi ground_truth.json)
Hoặc:
  py convert_ground_truth.py --in ground_truth_TEMPLATE.json --out ground_truth.json
"""
import json, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="ground_truth_TEMPLATE.json")
    ap.add_argument("--out", dest="out", default="ground_truth.json")
    args = ap.parse_args()

    data = json.load(open(args.inp, encoding="utf-8"))
    flat = {}
    n_label = n_blank = 0
    for task, node in data.items():
        courses = node.get("courses", node)  # chịu được cả format phẳng lẫn mới
        flat[task] = {}
        for cid, info in courses.items():
            if cid.startswith("_"):  # bỏ field meta _gap/_cv/_jd nếu lẫn
                continue
            label = info.get("label", "") if isinstance(info, dict) else info
            if label == "" or label is None:
                n_blank += 1
                continue  # chưa chấm -> bỏ qua (không đưa vào ground truth)
            flat[task][cid] = int(label)
            n_label += 1
        if not flat[task]:
            del flat[task]

    json.dump(flat, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ Đã ghi {args.out}")
    print(f"   Số nhãn đã chấm: {n_label} | Số khóa CHƯA chấm (bỏ qua): {n_blank}")
    if n_blank > 0:
        print(f"   ⚠️ Còn {n_blank} khóa chưa điền label. Chấm nốt rồi chạy lại nếu muốn đầy đủ.")

if __name__ == "__main__":
    main()