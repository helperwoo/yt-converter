import os
from pathlib import Path
from fastapi import Form, APIRouter, Request, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from service.job_service import JobService
from utils.datetime_helper import format_datetime_utc
from random import random
import math
import subprocess
import uuid

router = APIRouter(tags=["YT"])
templates = Jinja2Templates(directory="templates")

# Jinja2 필터 등록
templates.env.filters['to_iso'] = format_datetime_utc

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(exist_ok=True)

@router.get("/ping", response_class=JSONResponse)
async def ping():
    return {"pong": True}

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/convert")
async def convert(request: Request, ext: str = Form(...), quality: str = Form(...), url: str = Form(...)):
    # 백그라운드 작업 생성
    job_id = await JobService.create_job(url, ext, quality)
    
    # 작업 상태 페이지로 리다이렉트
    return RedirectResponse(url=f"/jobs", status_code=303)

@router.get("/jobs")
async def jobs_list(request: Request, page: int = 1, per_page: int = 10):
    # 페이지 번호와 페이지당 항목 수 검증
    page = max(1, page)
    if per_page not in [10, 20, 100]:
        per_page = 10

    # 전체 작업 수와 페이지네이션된 작업 목록 가져오기
    total_jobs, jobs = await JobService.get_paginated_jobs(page, per_page)

    # 전체 페이지 수 계산
    total_pages = (total_jobs + per_page - 1) // per_page

    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "jobs": jobs,
        "page": page,
        "per_page": per_page,
        "total_jobs": total_jobs,
        "total_pages": total_pages
    })

@router.get("/api/job/{job_id}")
async def get_job_api(job_id: str):
    job = await JobService.get_job(job_id)
    if not job:
        return {"error": "Job not found"}

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "title": job.title,
        "filename": job.filename,
        "error_message": job.error_message,
        "created_at": format_datetime_utc(job.created_at) or None,
        "completed_at": format_datetime_utc(job.completed_at) or None
    }

@router.get("/api/jobs")
async def get_jobs_api(job_ids: list[str] = Query(default=[])):
    jobs = await JobService.get_jobs(job_ids)
    if not jobs:
        return {"error": "Jobs not found"}
    
    return [{
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "title": job.title,
        "filename": job.filename,
        "error_message": job.error_message,
        "created_at": format_datetime_utc(job.created_at) or None,
        "completed_at": format_datetime_utc(job.completed_at) or None
    } for job in jobs]


@router.delete("/api/job/{job_id}")
async def delete_job_api(job_id: str):
    success = await JobService.delete_job(job_id)
    if success:
        return {"message": "Job deleted successfully"}
    return {"error": "Job not found or could not be deleted"}

@router.post("/api/job/{job_id}/retry")
async def retry_job_api(job_id: str):
    new_job_id = await JobService.retry_job(job_id)
    if new_job_id:
        return {"message": "Job retry started", "new_job_id": new_job_id}
    return {"error": "Job not found or could not be retried"}

@router.get("/download/{filename}")
async def download(filename: str):
    filepath = DOWNLOAD_DIR / filename
    if filepath.exists():
        return FileResponse(path=filepath, filename=filename, media_type='application/octet-stream')
    return {"error": "파일이 존재하지 않음"}

