import json
import os

# Đường dẫn tới 2 file của Sếp
old_file_path = r"data\raw_courses_massive.json"  # File cũ 4000 khóa trong folder data
new_file_path = "raw_courses_massive.json"        # File mới 1166 khóa ngoài thư mục gốc

print("⏳ Đang đọc dữ liệu từ cả 2 file...")

# 1. Đọc file cũ
with open(old_file_path, "r", encoding="utf-8") as f:
    old_data = json.load(f)

# 2. Đọc file mới
with open(new_file_path, "r", encoding="utf-8") as f:
    new_data = json.load(f)

print(f"📦 File cũ: {len(old_data)} khóa. File mới: {len(new_data)} khóa.")

# 3. Tiến hành gộp mảng (Nối tiếp dữ liệu)
old_data.extend(new_data)

# 4. Ghi đè lại vào file trong thư mục data
with open(old_file_path, "w", encoding="utf-8") as f:
    json.dump(old_data, f, ensure_ascii=False, indent=4)

print(f"🎉 THÀNH CÔNG! File trong thư mục data hiện tại đã có: {len(old_data)} khóa học.")