from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
from models.schemas import GapAnalysisRequest, JDExtractRequest, TaskStatusResponse, CVExtractRequest


# Kéo dữ liệu từ két sắt và xưởng AI ra
# TÌM VÀ XÓA DÒNG NÀY:
# from core.state import tasks_db, GLOBAL_COURSE_TREE

# DÁN DÒNG NÀY VÀO THAY THẾ:
import core.state as state
from services.background_tasks import process_llm_logic
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv

# Khởi tạo Lễ Tân
router = APIRouter(prefix="/api/v1", tags=["CV & JD Matching API"])



# --- KHAI BÁO CÁC ĐƯỜNG DẪN API ---
@router.post("/extract-jd")
async def api_extract_jd(request: JDExtractRequest):
    try:
        skills = extract_skills_from_jd(request.jd_text)
        return {"status": "success", "data": skills}
    except Exception as e:
        return {"status": "failed", "message": str(e)}  

@router.post("/extract-cv")
async def api_extract_cv(request: CVExtractRequest):
    try:
        skills = extract_skills_from_cv(request.cv_text)
        return {"status": "success", "data": skills}
    except Exception as e:
        return {"status": "failed", "message": str(e)}

@router.post("/analyze-gap", response_model=TaskStatusResponse)
async def start_gap_analysis(request: GapAnalysisRequest, background_tasks: BackgroundTasks):
    if not state.GLOBAL_COURSE_TREE:
        raise HTTPException(status_code=500, detail="Hệ thống chưa tải xong dữ liệu Cây Khóa Học.")

    task_id = str(uuid.uuid4())
    state.tasks_db[task_id] = {"status": "processing"}
    
    # Giao việc cho xưởng AI chạy ngầm
    background_tasks.add_task(process_llm_logic, task_id, request.cv_text, request.jd_text, request.verified_skills, request.pre_extracted_jd)
    
    return TaskStatusResponse(
        task_id=task_id, 
        status="processing", 
        message="Hệ thống AI đang phân tích dữ liệu, vui lòng chờ..."
    )

@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    task = state.tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task ID không tồn tại hoặc đã hết hạn.")
        
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        message=task.get("message"),
        data=task.get("data")
    )