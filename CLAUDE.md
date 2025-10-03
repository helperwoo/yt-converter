# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube video/audio converter service built with FastAPI and yt-dlp. The application converts YouTube content to MP3 (audio) or MP4 (video) formats with configurable quality settings, using background job processing with SQLite for job tracking.

## Development Commands

### Running the Application

```bash
# Build and start with Docker Compose
docker-compose up --build

# The app runs on port 8000 (exposed via Traefik network)
# Uvicorn runs with --reload for auto-reloading on file changes
```

### Direct Development (without Docker)

```bash
cd app
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Architecture

### Application Structure

The codebase follows a clean layered architecture:

- **Controller Layer** (`controller/yt_controller.py`): FastAPI routes and request handling
  - Web UI endpoints serving Jinja2 templates
  - REST API endpoints for job management (GET, DELETE, POST for retry)
  - File download endpoint

- **Service Layer** (`service/job_service.py`): Business logic and job processing
  - Creates background tasks using `asyncio.create_task()`
  - Manages conversion jobs via yt-dlp subprocess execution
  - Handles job lifecycle (create, process, get, delete, retry)

- **Database Layer** (`database.py`): SQLAlchemy async session management
  - Uses `sqlite+aiosqlite` for async SQLite operations
  - Configurable via `DATABASE_URL` environment variable
  - Auto-creates tables on application startup via lifespan event

- **Models** (`models/job.py`): SQLAlchemy ORM models
  - `ConversionJob`: Tracks URL, format, quality, status, progress, timestamps
  - `JobStatus`: Enum with PENDING, PROCESSING, COMPLETED, FAILED states

### Background Job Processing

Jobs are processed asynchronously using `asyncio.create_task()`:

1. User submits conversion request → creates job record with PENDING status
2. Background task starts immediately (`JobService.process_job()`)
3. Job status transitions: PENDING → PROCESSING → COMPLETED/FAILED
4. Progress tracked at 0% → 10% → 50% → 100%
5. Files saved to `downloads/` directory with `{job_id}.{format}` naming

**Important**: Each job processing session carefully manages SQLAlchemy async sessions to avoid "object is already attached to session" errors. Sessions are opened and closed strategically around blocking subprocess calls.

### yt-dlp Integration

Format-specific yt-dlp command construction in `JobService.process_job()`:

- **MP3**: `--extract-audio --audio-format mp3 --audio-quality {quality}K -f bestaudio/best`
- **MP4**: `-f best[height<={quality}] --merge-output-format mp4`

Quality options:
- MP3: 128, 192, 256, 320 (kbps)
- MP4: 360, 480, 720, 1080 (resolution height)

### Frontend

Jinja2 templates in `templates/`:
- `index.html`: Main conversion form
- `job_status.html`: Job progress tracking with auto-refresh
- `jobs.html`: All jobs list view
- `result.html`: Download page after completion
- `error.html`: Error display

Uses Tailwind CSS for styling (loaded from base template).

## Environment Variables

- `DATABASE_URL`: Database connection string (default: `sqlite+aiosqlite:///jobs.db`)
- `DOWNLOAD_DIR`: Download directory path (default: `downloads`)

## Dependencies

Key packages in `requirements.txt`:
- `fastapi` + `uvicorn[standard]`: Web framework and ASGI server
- `yt-dlp>=2025.9.23`: YouTube downloader
- `sqlalchemy` + `aiosqlite` + `greenlet`: Async ORM and SQLite driver
- `jinja2`: Template engine
- `python-multipart`: Form data parsing

System dependency: `ffmpeg` (installed in Dockerfile for audio/video processing)

## Deployment

Uses Docker with Traefik reverse proxy integration:
- Container name: `youtube_converter`
- External network: `traefik` (must be created separately)
- Volume mount: `./app:/home/app` for hot-reloading
- Persistent data: SQLite DB and downloads stored in container volumes
