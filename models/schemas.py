# Nội dung file models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CVExtractRequest(BaseModel):
    cv_text: str = Field(..., description="Nội dung CV của ứng viên")

class JDExtractRequest(BaseModel):
    jd_text: str = Field(..., description="Nội dung JD")

class GapAnalysisRequest(BaseModel):
    jd_text: str = Field(..., description="Nội dung Job Description")
    cv_text: str = Field(..., description="Nội dung CV của ứng viên")
    verified_skills: Optional[Dict] = None
    pre_extracted_jd: Optional[Dict] = None

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None
    data: Optional[Any] = None  