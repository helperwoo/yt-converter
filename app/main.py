import os
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import subprocess
import uuid

app = FastAPI()

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(exist_ok=True)

@app.get("/ping", response_class=JSONResponse)
async def ping():
    return {"pong": True}

@app.get("/", response_class=HTMLResponse)
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

@app.post("/convert", response_class=HTMLResponse)
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
        return f"""
        <div>
            ✅ 다운로드 완료! <a href='/download/{filename}'>여기서 받기</a>
        </div>
        """
    except subprocess.CalledProcessError as e:
        return f"""
        ❌ 다운로드 실패: {e}
        """

@app.get("/download/{filename}")
async def download(filename: str):
    filepath = DOWNLOAD_DIR / filename
    if filepath.exists():
        return FileResponse(path=filepath, filename=filename, media_type='application/octet-stream')
    return {"error": "파일이 존재하지 않음"}
