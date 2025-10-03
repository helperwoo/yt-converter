# YouTube Converter

YouTube 영상을 MP3(오디오) 또는 MP4(비디오)로 간편하게 변환하는 웹 서비스입니다.

## 주요 기능

- 🎵 **MP3 변환**: YouTube 영상을 고품질 오디오 파일로 변환 (128/192/256/320 kbps)
- 🎬 **MP4 변환**: YouTube 영상을 다양한 해상도로 다운로드 (360p/480p/720p/1080p)
- 📊 **실시간 진행 상황**: 백그라운드 작업 처리 및 실시간 진행률 표시
- 📋 **작업 관리**: 모든 변환 작업 내역 조회, 재시도, 삭제 기능
- 🎨 **모던 UI**: Tailwind CSS 기반의 직관적이고 반응형 사용자 인터페이스

## 기술 스택

- **Backend**: FastAPI (Python 3.10)
- **Database**: SQLite (SQLAlchemy async ORM)
- **Converter**: yt-dlp
- **Frontend**: Jinja2 Templates + Tailwind CSS
- **Deployment**: Docker + Docker Compose + Traefik

## 빠른 시작

### 사전 요구사항

- Docker
- Docker Compose
- Traefik 네트워크 (프로덕션 환경)

### 실행 방법

1. 저장소 클론
```bash
git clone <repository-url>
cd yt-converter
```

2. Docker Compose로 실행
```bash
docker-compose up --build
```

3. 브라우저에서 접속
```
http://localhost:8000
```

### 로컬 개발 환경

Docker 없이 직접 실행:

```bash
cd app
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**참고**: ffmpeg가 시스템에 설치되어 있어야 합니다.

## 사용 방법

1. **변환 시작**
   - 파일 형식 선택 (MP3 또는 MP4)
   - 원하는 품질 선택
   - YouTube URL 입력
   - "변환 시작" 버튼 클릭

2. **진행 상황 확인**
   - 변환 시작 후 자동으로 작업 상태 페이지로 이동
   - 실시간으로 진행률 표시 (PENDING → PROCESSING → COMPLETED/FAILED)
   - 완료되면 자동으로 다운로드 링크 표시

3. **작업 관리**
   - `/jobs` 페이지에서 모든 작업 내역 확인
   - 실패한 작업 재시도 가능
   - 불필요한 작업 삭제 가능

## API 엔드포인트

### 웹 UI
- `GET /` - 메인 페이지
- `POST /convert` - 변환 작업 생성
- `GET /job/{job_id}` - 작업 상태 페이지
- `GET /jobs` - 작업 목록 페이지
- `GET /download/{filename}` - 파일 다운로드

### REST API
- `GET /api/job/{job_id}` - 작업 정보 조회 (JSON)
- `DELETE /api/job/{job_id}` - 작업 삭제
- `POST /api/job/{job_id}/retry` - 작업 재시도
- `GET /ping` - 헬스체크

## 프로젝트 구조

```
yt-converter/
├── app/
│   ├── controller/          # FastAPI 라우터
│   │   └── yt_controller.py
│   ├── service/             # 비즈니스 로직
│   │   └── job_service.py
│   ├── models/              # SQLAlchemy 모델
│   │   └── job.py
│   ├── templates/           # Jinja2 템플릿
│   ├── database.py          # DB 연결 및 세션 관리
│   ├── main.py              # FastAPI 앱 진입점
│   └── requirements.txt     # Python 의존성
├── docker-compose.yml       # Docker Compose 설정
├── Dockerfile               # Docker 이미지 빌드
└── README.md
```

## 환경 변수

- `DATABASE_URL`: 데이터베이스 연결 문자열 (기본값: `sqlite+aiosqlite:///jobs.db`)
- `DOWNLOAD_DIR`: 다운로드 파일 저장 경로 (기본값: `downloads`)

## 배포

이 프로젝트는 Traefik 리버스 프록시와 함께 사용하도록 설정되어 있습니다.

1. Traefik 네트워크 생성 (한 번만 실행)
```bash
docker network create traefik
```

2. 애플리케이션 시작
```bash
docker-compose up -d
```

## 작업 흐름

1. 사용자가 변환 요청 제출
2. `ConversionJob` 레코드가 PENDING 상태로 생성
3. 백그라운드 작업이 `asyncio.create_task()`로 시작
4. 작업 상태가 PROCESSING으로 변경
5. yt-dlp가 subprocess로 실행되어 변환 수행
6. 완료 시 COMPLETED 상태로 변경 및 파일 저장
7. 실패 시 FAILED 상태로 변경 및 에러 메시지 저장

## 라이선스

이 프로젝트는 개인 프로젝트로 제작되었습니다.

## 주의사항

- YouTube의 이용 약관을 준수하여 사용하세요
- 저작권이 있는 콘텐츠의 무단 다운로드는 법적 문제가 발생할 수 있습니다
- 개인적인 용도로만 사용하시기 바랍니다
