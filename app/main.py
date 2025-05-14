from fastapi import FastAPI
from dotenv import load_dotenv
from controller import yt_controller

app = FastAPI()
load_dotenv()
app.include_router(yt_controller.router)

