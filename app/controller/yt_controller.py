import os
from pathlib import Path
from fastapi import Form, APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from service import yt_service
import subprocess
import uuid

router = APIRouter(tags=["YT"])
templates = Jinja2Templates(directory="templates")

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
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = DOWNLOAD_DIR / filename

    command = ["yt-dlp"]
    
    if ext == "mp3":
        # MP3 오디오 변환 설정
        command += ["--extract-audio", "--audio-format", "mp3"]
        command += ["--audio-quality", quality + "K"]  # 320K, 256K, 192K, 128K
        command += ["-f", "bestaudio/best"]
    else:  # mp4
        # MP4 비디오 변환 설정
        if quality == "1080":
            command += ["-f", "best[height<=1080]"]
        elif quality == "720":
            command += ["-f", "best[height<=720]"]
        elif quality == "480":
            command += ["-f", "best[height<=480]"]
        elif quality == "360":
            command += ["-f", "best[height<=360]"]
        else:
            command += ["-f", "best"]
        command += ["--merge-output-format", "mp4"]
    
    command += ["-o", str(filepath), url]

    try:
        subprocess.run(command, check=True)
        return RedirectResponse(url=f"/result/{filename}?ext={ext}&quality={quality}", status_code=303)
    except subprocess.CalledProcessError as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": str(e)
        })

@router.get("/result/{filename}")
async def result(request: Request, filename: str, ext: str = None, quality: str = None):
    # 품질 정보를 사용자 친화적으로 변환
    quality_info = ""
    if ext == "mp3" and quality:
        quality_info = f"{quality}kbps MP3"
    elif ext == "mp4" and quality:
        quality_info = f"{quality}p MP4"
    
    return templates.TemplateResponse("result.html", {
        "request": request,
        "filename": filename,
        "quality_info": quality_info
    })

@router.get("/download/{filename}")
async def download(filename: str):
    filepath = DOWNLOAD_DIR / filename
    if filepath.exists():
        return FileResponse(path=filepath, filename=filename, media_type='application/octet-stream')
    return {"error": "파일이 존재하지 않음"}

@router.get("/send/{filename}")
async def send(filename: str):
    filepath = DOWNLOAD_DIR / filename
    if filepath.exists():
        return yt_service.send_mail(filepath)
    return {"error": "파일이 존재하지 않음"}
