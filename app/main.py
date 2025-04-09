import os
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
import subprocess
import uuid

app = FastAPI()

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <form action="/convert" method="post">
        <input type="text" name="url" placeholder="YouTube 링크 입력" style="width:300px"/>
        <button type="submit">Convert</button>
    </form>
    """

@app.post("/convert")
async def convert(url: str = Form(...)):
    filename = f"{uuid.uuid4()}.mp4"
    filepath = DOWNLOAD_DIR / filename

    command = [
        "yt-dlp",
        "-f", "best",
        "-o", str(filepath),
        url
    ]

    try:
        subprocess.run(command, check=True)
        return f"✅ 다운로드 완료! <a href='/download/{filename}'>여기서 받기</a>"
    except subprocess.CalledProcessError as e:
        return f"❌ 다운로드 실패: {e}"

@app.get("/download/{filename}")
async def download(filename: str):
    filepath = DOWNLOAD_DIR / filename
    if filepath.exists():
        return FileResponse(path=filepath, filename=filename, media_type='application/octet-stream')
    return {"error": "파일이 존재하지 않음"}
