from typing import Dict

# ==========================================
# TRẠNG THÁI TOÀN CỤC (GLOBAL STATE)
# Nơi lưu trữ dữ liệu trên RAM để các file khác gọi đến
# ==========================================

# Lưu trữ Cây Khóa Học trên RAM (Giúp DFS chạy nhanh O(1))
GLOBAL_COURSE_TREE = {}

# Lưu trữ trạng thái của các tiến trình đang chạy ngầm (Polling Pattern)
tasks_db: Dict[str, dict] = {}