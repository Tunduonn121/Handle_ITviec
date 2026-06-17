from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import két sắt và hàm xây cây
import core.state as state
from services.tree_builder import load_courses_from_sql, build_course_tree

# Import các Lễ tân (Routers) đã tạo ở Bước 3 và 4
from api import router_cv, router_courses

# ==========================================
# KHỞI TẠO APP
# ==========================================
app = FastAPI(
    title="IT Skill Gap Matching SaaS",
    description="Backend API hệ thống kiến trúc Clean Architecture chuẩn Enterprise.",
    version="2.0.0" 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.on_event("startup")
async def startup_event():
    print("⏳ Đang nạp Database và xây dựng Cây Khóa Học lên RAM...")
    flat_data = load_courses_from_sql()
    if flat_data:
        # Nạp dữ liệu vào két sắt
        state.GLOBAL_COURSE_TREE = build_course_tree(flat_data)
        print("✅ KHỞI ĐỘNG THÀNH CÔNG: Cây Khóa Học đã sẵn sàng trên RAM!")
    else:
        print("⚠️ CẢNH BÁO: Database rỗng, không thể xây dựng Cây Khóa Học.")

# ==========================================
# NỐI ROUTERS (KÍCH HOẠT CÁC PHÒNG BAN)
# ==========================================
# Nhúng Router CV vào hệ thống
app.include_router(router_cv.router)

# Nhúng Router Admin Khóa học vào hệ thống
app.include_router(router_courses.router)

if __name__ == "__main__":
    import uvicorn
    # Chạy Server
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)