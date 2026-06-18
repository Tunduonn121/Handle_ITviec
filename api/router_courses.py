from fastapi import APIRouter, HTTPException
import core.state as state # Lấy két sắt ra
from services.tree_builder import load_courses_from_sql, build_course_tree

# Khởi tạo Lễ Tân mảng Khóa học
router = APIRouter(prefix="/api/v1/admin", tags=["Course & System Admin"])

@router.post("/reload-tree")
async def admin_reload_tree():
    """API dành cho Admin/Crawler cập nhật Cây Khóa Học từ SQL lên RAM"""
    print("⏳ [HOT-RELOAD] Đang tải lại Cây Khóa Học từ Database...")
    flat_data = load_courses_from_sql()
    
    if flat_data:
        # Cập nhật trực tiếp vào két sắt
        state.GLOBAL_COURSE_TREE = build_course_tree(flat_data)
        from services.tree_searcher import clear_pruning_cache
        clear_pruning_cache()   # ⭐ tránh prune theo dữ liệu cũ
        print(f"✅ [HOT-RELOAD] Cây Khóa Học đã được làm mới với {len(flat_data)} khóa!")
        return {"status": "success", "message": f"Cập nhật RAM thành công với {len(flat_data)} khóa học."}
    else:
        raise HTTPException(status_code=500, detail="Không thể tải dữ liệu từ SQL.")