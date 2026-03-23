# Brainrot Backend

Standalone FastAPI backend for converting websites, blogs, and papers into short-form 9:16 gameplay reels with synced narration, karaoke subtitles, music, and FFmpeg rendering.

## Stack

- FastAPI for the HTTP API and SSE streams
- ElevenLabs Agents for source analysis, angle planning, script generation, QA, and voice narration
- OpenAI Responses proxied through ElevenLabs Custom LLM for the producer agent
- Firecrawl for website and PDF ingestion
- ElevenLabs Forced Alignment for subtitle timings
- Supabase for persistence and blob storage
- FFmpeg for reel composition

## Run

```bash
cd Backend
uv sync
uv run uvicorn brainrot_backend.main:app --reload
```

## Environment

Copy `.env.example` to `.env` and fill in the provider keys you want to use.

The backend expects these ElevenLabs agent bootstrap settings before `POST /v1/agents/bootstrap` will work:

- `BRAINROT_ELEVENLABS_API_KEY`
- `BRAINROT_ELEVENLABS_TOOL_TOKEN`
- `BRAINROT_ELEVENLABS_CUSTOM_LLM_TOKEN`
- `BRAINROT_DEFAULT_ELEVENLABS_VOICE_ID`
- `BRAINROT_PUBLIC_BASE_URL` or a request-accessible base URL
- `BRAINROT_OPENAI_API_KEY`

The app prefers Supabase when `BRAINROT_SUPABASE_URL` and `BRAINROT_SUPABASE_SERVICE_ROLE_KEY` are set. Otherwise it falls back to local in-memory metadata and local filesystem storage under `Backend/data/`, which keeps development and tests runnable before the real infrastructure is wired.

## API

- `POST /v1/assets/upload`
- `POST /v1/agents/bootstrap`
- `POST /v1/agents/custom-llm/responses`
- `POST /v1/agents/tools/submit-script-bundle`
- `POST /v1/agents/webhooks/elevenlabs`
- `POST /v1/batches`
- `GET /v1/batches/{batch_id}`
- `GET /v1/batches/{batch_id}/events`
- `POST /v1/batches/{batch_id}/retry`

## Schema

The expected Supabase/Postgres schema is in `sql/schema.sql`.
