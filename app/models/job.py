from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum

Base = declarative_base()

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ConversionJob(Base):
    __tablename__ = "conversion_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True)  # UUID
    url = Column(Text, nullable=False)
    format = Column(String(10), nullable=False)  # mp3, mp4
    quality = Column(String(10), nullable=False)  # 320, 1080, etc
    filename = Column(String(255), nullable=True)
    status = Column(String(20), default=JobStatus.PENDING)
    progress = Column(Integer, default=0)  # 0-100%
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)