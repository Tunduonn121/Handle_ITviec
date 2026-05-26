from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import uuid
import re

# IMPORT TOÀN BỘ CÁC MODULE LÕI CỦA SẾP TỪ THƯ MỤC SERVICES
from services.tree_builder import load_courses_from_sql, build_course_tree
from services.tree_searcher import dfs_tree_search
from services.course_ranker import rank_courses_with_llm
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
# THÊM DÒNG NÀY ĐỂ IMPORT HÀM CHUẨN HÓA
from services.aliases import clean_and_normalize



# ==========================================
# 1. KHỞI TẠO APP & DỮ LIỆU TOÀN CỤC (RAM CACHE)
# ==========================================
app = FastAPI(
    title="IT Skill Gap Matching SaaS",
    description="Backend API hệ thống gợi ý khóa học sử dụng Background Tasks & Polling Pattern.",
    version="2.0.0" # Lên version 2.0 luôn cho máu!
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Cho phép mọi Frontend gọi vào (khi deploy thật có thể sửa thành domain của Sếp)
    allow_credentials=True,
    allow_methods=["*"], # Cho phép POST, GET...
    allow_headers=["*"], 
)

GLOBAL_COURSE_TREE = {}
tasks_db: Dict[str, dict] = {}

@app.on_event("startup")
async def startup_event():
    global GLOBAL_COURSE_TREE
    print("⏳ Đang nạp Database và xây dựng Cây Khóa Học lên RAM...")
    flat_data = load_courses_from_sql()
    if flat_data:
        GLOBAL_COURSE_TREE = build_course_tree(flat_data)
        print("✅ KHỞI ĐỘNG THÀNH CÔNG: Cây Khóa Học đã sẵn sàng trên RAM!")
    else:
        print("⚠️ CẢNH BÁO: Database rỗng, không thể xây dựng Cây Khóa Học.")

# ==========================================
# THÊM API ADMIN NÀY VÀO DƯỚI DÒNG: @app.on_event("startup")
# ==========================================
@app.post("/api/v1/admin/reload-tree")
async def admin_reload_tree():
    """API dành cho Admin/Crawler cập nhật Cây Khóa Học từ SQL lên RAM"""
    global GLOBAL_COURSE_TREE
    print("⏳ [HOT-RELOAD] Đang tải lại Cây Khóa Học từ Database...")
    flat_data = load_courses_from_sql()
    if flat_data:
        GLOBAL_COURSE_TREE = build_course_tree(flat_data)
        print(f"✅ [HOT-RELOAD] Cây Khóa Học đã được làm mới với {len(flat_data)} khóa!")
        return {"status": "success", "message": f"Cập nhật RAM thành công với {len(flat_data)} khóa học."}
    else:
        raise HTTPException(status_code=500, detail="Không thể tải dữ liệu từ SQL.")

# ==========================================
# 2. PYDANTIC MODELS (API CONTRACT)
# ==========================================
class CVExtractRequest(BaseModel):
    cv_text: str = Field(..., description="Nội dung CV của ứng viên")

# Thêm cái này ngay dưới CVExtractRequest
class JDExtractRequest(BaseModel):
    jd_text: str = Field(..., description="Nội dung JD")
class GapAnalysisRequest(BaseModel):
    jd_text: str = Field(..., description="Nội dung Job Description")
    cv_text: str = Field(..., description="Nội dung CV của ứng viên")
    verified_skills: Optional[Dict] = Field(None, description="Kỹ năng từ CV đã được user xác nhận Level")
    pre_extracted_jd: Optional[Dict] = Field(None, description="Kỹ năng JD đã bóc tách ngầm") # DÒNG MỚI NÀY
class CourseItem(BaseModel):
    course_id: str
    title: str
    url: str
    level: int
    target_skills: List[str]
    relevance_score: int = 0
    reasoning: str = ""

# Tìm class này và sửa lại trường data
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str = Field(..., description="Trạng thái: processing, completed, failed")
    message: Optional[str] = None
    data: Optional[Any] = None  # Đổi từ List[CourseItem] thành Any để chứa được nhiều thứ

# ==========================================
# 3. BACKGROUND TASK CORE LOGIC (Não bộ xử lý ngầm)
# LƯU Ý: Dùng 'def' thay vì 'async def' để FastAPI tự đẩy vào ThreadPool, không làm nghẽn Server
# ==========================================
# Sửa lại tham số đầu vào, thêm verified_skills
# Cập nhật tham số có thêm pre_extracted_jd
# LƯU Ý: Dùng 'def' thay vì 'async def' để FastAPI tự đẩy vào ThreadPool, không làm nghẽn Server
# LƯU Ý: Dùng 'def' thay vì 'async def' để FastAPI tự đẩy vào ThreadPool, không làm nghẽn Server
def process_llm_logic(task_id: str, cv_text: str, jd_text: str, verified_skills: dict = None, pre_extracted_jd: dict = None):
    global GLOBAL_COURSE_TREE
    try:
        print(f"\n🚀 [TASK {task_id}] BẮT ĐẦU LUỒNG PHÂN TÍCH TOÀN TRÌNH")
        
        if pre_extracted_jd:
            jd_skills = pre_extracted_jd
        else:
            jd_skills = extract_skills_from_jd(jd_text)

        if verified_skills:
            cv_skills = verified_skills
        else:
            cv_skills = extract_skills_from_cv(cv_text)

        if not jd_skills:
            tasks_db[task_id] = {"status": "failed", "message": "Không thể trích xuất kỹ năng từ JD này."}
            return

        gap_raw, matched = compute_skill_gap(cv_skills, jd_skills)
        if not gap_raw:
            tasks_db[task_id] = {"status": "completed", "data": [], "message": "Ứng viên xuất sắc, CV đã cover 100% JD!"}
            return

        search_gap_dict = {}
        
        for skill_key, gap_info in gap_raw.items():
            missing_lvls = gap_info["missing_levels"]
            if gap_info["match_mode"] == "EXACT":
                skill_name = gap_info.get("user_skill_name") or skill_key
                # SỬ DỤNG HÀM TỪ ALIASES.PY THAY VÌ DICT CỤC BỘ
                mapped_skill = clean_and_normalize(skill_name)
                search_gap_dict[mapped_skill] = missing_lvls
            else:
                best_match = gap_info.get("user_best_match")
                if best_match:
                    match = re.match(r'([^\(]+)(?:\((.*)\))?', best_match)
                    if match:
                        main_skill = match.group(1).strip()
                        # SỬ DỤNG HÀM TỪ ALIASES.PY
                        mapped_main = clean_and_normalize(main_skill)
                        search_gap_dict[mapped_main] = missing_lvls
                        if match.group(2):
                            sub_skills = [s.strip() for s in match.group(2).split(',')]
                            for sub in sub_skills:
                                # SỬ DỤNG HÀM TỪ ALIASES.PY
                                mapped_sub = clean_and_normalize(sub)
                                search_gap_dict[mapped_sub] = missing_lvls

        # --- BƯỚC 3: TÌM KIẾM CÂY (DFS TREE SEARCH) ---
        print(f"🌲 [TASK {task_id}] Đang lùng sục Cây Khóa Học...")
        candidate_courses_raw = dfs_tree_search(GLOBAL_COURSE_TREE, search_gap_dict)
        
        # 🛡️ KIỂM SOÁT ĐẦU VÀO TỪ DFS (CHỐNG LỖI STRING)
        candidate_courses = []
        for c in candidate_courses_raw:
            if isinstance(c, dict):
                candidate_courses.append(c)

        if not candidate_courses:
            tasks_db[task_id] = {"status": "completed", "data": [], "message": "Không tìm thấy khóa học nào khớp với Gap."}
            return

        # --- BƯỚC 4: CHẤM ĐIỂM & RANKING (AI QWEN) ---
        print(f"🏆 [TASK {task_id}] Đang gọi Qwen xếp hạng Tính Sư Phạm...")
        ranked_result = rank_courses_with_llm(candidate_courses, search_gap_dict, top_k=3)

        # --- BƯỚC 5: BÓC TÁCH DỮ LIỆU ĐÃ PHÂN LOẠI SẴN ---
        print(f"📦 [TASK {task_id}] Đang đóng gói dữ liệu Combo và Regular...")
        
        combo_courses = []
        regular_courses = []
        
        # 🛡️ KIỂM SOÁT ĐẦU RA TỪ AI
        if isinstance(ranked_result, dict):
            combo_courses = ranked_result.get("combo_courses", [])
            regular_courses = ranked_result.get("regular_courses", [])
            
        # 🔥 CHÈN ĐOẠN ĐÁNH GIÁ THỰC TẾ (LIVE TELEMETRY) VÀO ĐÂY 🔥
        try:
            from services.evaluator import log_live_evaluation_metrics
            # Mang toàn bộ kết quả thật (gồm khóa Thường + khóa Combo), rổ ứng viên thật, và Gap thật ra đo đạc
            log_live_evaluation_metrics(
                task_id=task_id, 
                recommended_list=regular_courses, 
                combo_list=combo_courses, # <--- BIẾN MỚI ĐƯỢC TRUYỀN VÀO Ở ĐÂY
                candidate_pool=candidate_courses, 
                gap_dict=search_gap_dict
            )
        except Exception as eval_e:
            print(f"⚠️ Không thể in Metrics đánh giá trực tuyến: {eval_e}")
        # 🔥 ======================================================= 🔥

        tasks_db[task_id] = {
            "status": "completed", 
            "data": {
                "cv_skills": cv_skills,
                "jd_skills": jd_skills,
                "gap": search_gap_dict,
                "combo_courses": combo_courses,
                "regular_courses": regular_courses
            }, 
            "message": "Phân tích thành công!"
        }
        print(f"✅ [TASK {task_id}] HOÀN TẤT VÀ ĐÃ LƯU KẾT QUẢ VÀO CACHE.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ [TASK {task_id}] LỖI CRASH: {str(e)}")
        tasks_db[task_id] = {"status": "failed", "message": f"Lỗi hệ thống: {str(e)}"}
# ==========================================
# 4. ENDPOINTS (API ROUTES CHÍNH)
# ==========================================
@app.post("/api/v1/extract-jd")
async def api_extract_jd(request: JDExtractRequest):
    """API bóc tách JD chạy ngầm trong lúc user đang ở Màn hình 2"""
    try:
        skills = extract_skills_from_jd(request.jd_text)
        return {"status": "success", "data": skills}
    except Exception as e:
        return {"status": "failed", "message": str(e)}  

@app.post("/api/v1/extract-cv")
async def api_extract_cv(request: CVExtractRequest):
    """
    API 0: Bóc tách CV nhanh để hiển thị lên màn hình cho User tự đánh giá Level.
    """
    try:
        skills = extract_skills_from_cv(request.cv_text)
        return {"status": "success", "data": skills}
    except Exception as e:
        return {"status": "failed", "message": str(e)}

@app.post("/api/v1/analyze-gap", response_model=TaskStatusResponse)
async def start_gap_analysis(request: GapAnalysisRequest, background_tasks: BackgroundTasks):
    """
    API 1: Nhận JD & CV (hoặc Skill đã verify), ném việc cho Background Worker chạy ngầm.
    """
    if not GLOBAL_COURSE_TREE:
        raise HTTPException(status_code=500, detail="Hệ thống chưa tải xong dữ liệu Cây Khóa Học.")

    task_id = str(uuid.uuid4())
    
    # Lưu trạng thái ban đầu vào DB tạm
    tasks_db[task_id] = {"status": "processing"}
    
    # Đẩy nguyên cục Pipeline vào chạy ngầm (Nhớ truyền thêm verified_skills)
    background_tasks.add_task(process_llm_logic, task_id, request.cv_text, request.jd_text, request.verified_skills, request.pre_extracted_jd)
    
    return TaskStatusResponse(
        task_id=task_id, 
        status="processing", 
        message="Hệ thống AI đang phân tích dữ liệu, vui lòng chờ..."
    )

@app.get("/api/v1/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    # ... (Giữ nguyên API get_task_status như cũ)
    """
    API 2: Polling Endpoint. Frontend gọi API này liên tục mỗi 3 giây để hỏi xem có kết quả chưa.
    """
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task ID không tồn tại hoặc đã hết hạn.")
        
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        message=task.get("message"),
        data=task.get("data")
    )

# ==========================================
# 5. CHẠY SERVER
# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)