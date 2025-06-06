FROM python:3.10-slim

RUN apt-get update
RUN apt-get install -y ffmpeg
RUN apt-get clean

WORKDIR /home/app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p downloads

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]