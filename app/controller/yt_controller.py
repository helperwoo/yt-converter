import os
from pathlib import Path
from fastapi import Form, APIRouter
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from service import yt_service
import subprocess
import uuid

router = APIRouter(tags=["YT"])

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(exist_ok=True)

@router.get("/ping", response_class=JSONResponse)
async def ping():
    return {"pong": True}

@router.get("/", response_class=HTMLResponse)
async def home():
    return """
    <form action="/convert" method="post">
        <select name="ext">
            <option value="mp3">mp3</option>
            <option value="mp4">mp4</option>
        </select>
        <input type="text" name="url" placeholder="YouTube 링크 입력" style="width:300px"/>
        <button type="submit">Convert</button>
    </form>
    """

@router.post("/convert", response_class=HTMLResponse)
async def convert(ext: str = Form(...), url: str = Form(...)):
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = DOWNLOAD_DIR / filename

    command = ["yt-dlp"]
    command += ["-f", "best"]
    command += ["--extract-audio", "--audio-format" , "mp3"] if ext == "mp3" else []
    command += ["--merge-output-format", "mp4"] if ext == "mp4" else []
    command += ["-o", str(filepath), url]

    try:
        subprocess.run(command, check=True)
        return RedirectResponse(url=f"/result/{filename}", status_code=303)
    except subprocess.CalledProcessError as e:
        return f"""
            ❌ 변환 실패: {e}
        """

@router.get("/result/{filename}", response_class=HTMLResponse)
async def result(filename: str):
    return f"""
        <div>
            ✅ 변환 완료!
        </div>
        <div>
            <a href='/download/{filename}'>다운로드</a>
        </div>
        <div>
            <a href='/send/{filename}' target='_blank'>메일 전송</a>
        </div>
        """

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
