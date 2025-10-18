import asyncio
import subprocess
import uuid
import re
import json
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.job import ConversionJob, JobStatus
from database import async_session
import os

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(exist_ok=True)

def sanitize_filename(title: str, max_length: int = 100) -> str:
    """
    YouTube 제목을 파일명으로 사용할 수 있도록 변환
    - 파일시스템에서 사용할 수 없는 문자 제거
    - 길이 제한
    - 공백 처리
    """
    # 파일명에 사용할 수 없는 문자 제거 (Windows, Linux, macOS 모두 고려)
    # < > : " / \ | ? * 와 제어 문자 제거
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', title)

    # 연속된 공백을 하나로, 앞뒤 공백 제거
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()

    # 점(.)으로 시작하는 파일명 방지 (숨김 파일)
    sanitized = sanitized.lstrip('.')

    # 파일명이 비어있으면 기본값 사용
    if not sanitized:
        sanitized = "untitled"

    # 길이 제한 (너무 긴 파일명 방지)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()

    return sanitized

async def get_video_title(url: str) -> str:
    """
    yt-dlp를 사용하여 YouTube 영상의 제목을 가져옴
    """
    try:
        # yt-dlp로 메타데이터만 가져오기 (다운로드 하지 않음)
        process = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0 and stdout:
            metadata = json.loads(stdout.decode())
            return metadata.get('title', 'Untitled Video')
        else:
            # 제목을 가져오지 못한 경우 기본값 반환
            return 'Untitled Video'
    except Exception as e:
        # 오류 발생 시 기본값 반환
        return 'Untitled Video'

class JobService:
    @staticmethod
    async def create_job(url: str, format: str, quality: str) -> str:
        job_id = str(uuid.uuid4())
        
        async with async_session() as session:
            job = ConversionJob(
                job_id=job_id,
                url=url,
                format=format,
                quality=quality,
                status=JobStatus.PENDING
            )
            session.add(job)
            await session.commit()
            
        # 백그라운드 작업 시작
        asyncio.create_task(JobService.process_job(job_id))
        
        return job_id
    
    @staticmethod
    async def process_job(job_id: str):
        try:
            # 작업 상태를 PROCESSING으로 변경
            async with async_session() as session:
                result = await session.execute(
                    select(ConversionJob).where(ConversionJob.job_id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    return

                job.status = JobStatus.PROCESSING
                job.progress = 10
                await session.commit()

            # YouTube 제목 추출
            video_title = await get_video_title(job.url)

            # 제목을 DB에 저장
            async with async_session() as session:
                result = await session.execute(
                    select(ConversionJob).where(ConversionJob.job_id == job_id)
                )
                job = result.scalar_one_or_none()

                if job:
                    job.title = video_title
                    job.progress = 20
                    await session.commit()

            # 작업 정보 다시 조회 (비동기 작업을 위해)
            async with async_session() as session:
                result = await session.execute(
                    select(ConversionJob).where(ConversionJob.job_id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    return

                # 파일명 생성 - 제목 기반으로 변경
                sanitized_title = sanitize_filename(job.title or "untitled")
                filename = f"{sanitized_title}.{job.format}"
                filepath = DOWNLOAD_DIR / filename
                
                # yt-dlp 명령어 구성
                command = ["yt-dlp"]
                
                if job.format == "mp3":
                    command += ["--extract-audio", "--audio-format", "mp3"]
                    command += ["--audio-quality", job.quality + "K"]
                    command += ["-f", "bestaudio/best"]
                else:  # mp4
                    if job.quality == "1080":
                        command += ["-f", "best[height<=1080]"]
                    elif job.quality == "720":
                        command += ["-f", "best[height<=720]"]
                    elif job.quality == "480":
                        command += ["-f", "best[height<=480]"]
                    elif job.quality == "360":
                        command += ["-f", "best[height<=360]"]
                    else:
                        command += ["-f", "best"]
                    command += ["--merge-output-format", "mp4"]
                
                command += ["-o", str(filepath), job.url]

                # 진행률 업데이트
                job.progress = 60
                await session.commit()
                
            # 변환 실행 (비동기) - 세션 외부에서 실행
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                result_code = process.returncode
                
                # 결과 업데이트
                async with async_session() as session:
                    result = await session.execute(
                        select(ConversionJob).where(ConversionJob.job_id == job_id)
                    )
                    job = result.scalar_one_or_none()
                    
                    if job:
                        if result_code == 0:
                            # 성공
                            job.status = JobStatus.COMPLETED
                            job.progress = 100
                            job.filename = filename
                            job.completed_at = datetime.now(timezone.utc)
                        else:
                            # 실패
                            job.status = JobStatus.FAILED
                            job.error_message = stderr.decode() if stderr else stdout.decode()

                        await session.commit()
                
            except Exception as e:
                # 변환 실행 중 오류
                async with async_session() as session:
                    result = await session.execute(
                        select(ConversionJob).where(ConversionJob.job_id == job_id)
                    )
                    job = result.scalar_one_or_none()
                    
                    if job:
                        job.status = JobStatus.FAILED
                        job.error_message = str(e)
                        await session.commit()
                        
        except Exception as e:
            # 전체 프로세스 오류
            try:
                async with async_session() as session:
                    result = await session.execute(
                        select(ConversionJob).where(ConversionJob.job_id == job_id)
                    )
                    job = result.scalar_one_or_none()
                    
                    if job:
                        job.status = JobStatus.FAILED
                        job.error_message = f"Process error: {str(e)}"
                        await session.commit()
            except:
                pass  # 로깅 시스템이 있다면 여기서 로그
    
    @staticmethod
    async def get_job(job_id: str) -> ConversionJob:
        async with async_session() as session:
            result = await session.execute(
                select(ConversionJob).where(ConversionJob.job_id == job_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_jobs(limit: int = 50) -> list[ConversionJob]:
        async with async_session() as session:
            result = await session.execute(
                select(ConversionJob)
                .order_by(ConversionJob.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()

    @staticmethod
    async def get_paginated_jobs(page: int, per_page: int) -> tuple[int, list[ConversionJob]]:
        """
        페이지네이션된 작업 목록과 전체 작업 수를 반환
        """
        async with async_session() as session:
            # 전체 작업 수 조회
            count_result = await session.execute(
                select(ConversionJob)
            )
            total_count = len(count_result.scalars().all())

            # 페이지네이션된 작업 목록 조회
            offset = (page - 1) * per_page
            result = await session.execute(
                select(ConversionJob)
                .order_by(ConversionJob.created_at.desc())
                .limit(per_page)
                .offset(offset)
            )
            jobs = result.scalars().all()

            return total_count, jobs
    
    @staticmethod
    async def get_jobs_by_status(status: JobStatus, limit: int = 50) -> list[ConversionJob]:
        async with async_session() as session:
            result = await session.execute(
                select(ConversionJob)
                .where(ConversionJob.status == status)
                .order_by(ConversionJob.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    @staticmethod
    async def delete_job(job_id: str) -> bool:
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(ConversionJob).where(ConversionJob.job_id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    return False

                # 파일 삭제 시도
                file_deleted = False
                file_error = None

                # 1. filename 속성이 있으면 해당 파일 삭제
                if job.filename:
                    filepath = DOWNLOAD_DIR / job.filename
                    try:
                        if filepath.exists():
                            filepath.unlink()
                            file_deleted = True
                    except Exception as e:
                        file_error = e

                # 2. filename이 없지만 title이 있으면 title 기반 파일명으로 삭제 시도
                elif job.title and job.format:
                    sanitized_title = sanitize_filename(job.title)
                    filename = f"{sanitized_title}.{job.format}"
                    filepath = DOWNLOAD_DIR / filename
                    try:
                        if filepath.exists():
                            filepath.unlink()
                            file_deleted = True
                    except Exception as e:
                        file_error = e

                # 파일 삭제 실패 시에도 DB에서는 제거 (파일이 이미 없을 수 있음)
                # 단, 파일이 존재했는데 삭제 실패한 경우에만 예외 발생
                if file_error and not file_deleted:
                    # 파일이 존재했는데 삭제 실패한 경우
                    # 이 경우에도 DB 레코드는 삭제하도록 진행
                    pass

                await session.delete(job)
                await session.commit()
                return True

        except Exception as e:
            return False
    
    @staticmethod
    async def retry_job(job_id: str) -> str:
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(ConversionJob).where(ConversionJob.job_id == job_id)
                )
                old_job = result.scalar_one_or_none()
                
                if not old_job:
                    return None
                
                # 새로운 작업 생성
                new_job_id = str(uuid.uuid4())
                new_job = ConversionJob(
                    job_id=new_job_id,
                    url=old_job.url,
                    format=old_job.format,
                    quality=old_job.quality,
                    status=JobStatus.PENDING
                )
                session.add(new_job)
                await session.commit()
                
                # 백그라운드 작업 시작
                asyncio.create_task(JobService.process_job(new_job_id))
                
                return new_job_id
                
        except Exception as e:
            return None