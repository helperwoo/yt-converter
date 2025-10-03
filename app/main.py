from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from controller import yt_controller
from database import create_tables
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 데이터베이스 테이블 생성
    await create_tables()
    yield
    # 종료 시 정리 작업 (필요한 경우)

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

load_dotenv()
app.include_router(yt_controller.router)

