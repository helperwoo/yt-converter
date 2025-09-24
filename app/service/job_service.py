import asyncio
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.job import ConversionJob, JobStatus
from database import async_session
import os

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(exist_ok=True)

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
            
            # 작업 정보 다시 조회 (비동기 작업을 위해)
            async with async_session() as session:
                result = await session.execute(
                    select(ConversionJob).where(ConversionJob.job_id == job_id)
                )
                job = result.scalar_one_or_none()
                
                if not job:
                    return
                
                # 파일명 생성
                filename = f"{job_id}.{job.format}"
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
                job.progress = 50
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
                            job.completed_at = datetime.utcnow()
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
                
                # 파일이 있다면 삭제
                if job.filename:
                    filepath = DOWNLOAD_DIR / job.filename
                    if filepath.exists():
                        filepath.unlink()
                
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