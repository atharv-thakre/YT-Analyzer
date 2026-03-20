# YT Analyzer

FastAPI app to analyze YouTube playlists, store metrics in PostgreSQL, compare playlists, and export reports.

## Features

- Analyze playlist videos and cache results in DB
- View playlist report page
- Compare two playlists from DB data
- List all playlists in table format
- Export playlist report to Excel

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create local env file:
   ```bash
   cp .env.example .env
   ```
   On Windows PowerShell:
   ```powershell
   Copy-Item .env.example .env
   ```
4. Fill real credentials in `.env`.
5. Start app:
   ```bash
   uvicorn app.main:app --reload
   ```

## Required Environment Variables

- `DATABASE_URL`
- `YOUTUBE_API_KEY`
- `DB_ECHO`
- `YT_API_TIMEOUT`
- `YT_API_RETRIES`
- `FRESHNESS_DEFAULT_HOURS`
- `FRESHNESS_MIN_HOURS`
- `FRESHNESS_MAX_HOURS`

Use `.env.example` as the template.

## Routes

- `GET /` → analyze page
- `GET /compare` → compare page (DB-only compare)
- `GET /playlists` → all playlists table
- `POST /analyze` → analyze playlist URL
- `GET /compare-playlists` → compare by playlist IDs
- `GET /playlist/{playlist_id}/view` → playlist details
- `GET /playlist/{playlist_id}/export` → excel download

## GitHub Shipping Checklist

- `.env` must stay local and never be committed
- Commit only `.env.example`
- Rotate credentials if they were ever pushed to a remote
- Verify `.gitignore` includes env files and generated artifacts

## License

Add your preferred license before publishing.
