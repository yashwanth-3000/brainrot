# Backend

The FastAPI backend that powers Draftr. It owns two product domains:

- `video_generator`: ingest, section planning, script writing, narration, subtitle timing, asset selection, and FFmpeg rendering
- `recommendation_system`: chats, library views, engagement tracking, and follow-up recommendations

By default, the current pipeline is:

1. Firecrawl ingests a URL or PDF into markdown
2. CrewAI sections the source and builds slot coverage
3. OpenAI writes one short per slot
4. Backend QA repairs weak or repetitive scripts
5. ElevenLabs generates TTS audio plus timing data
6. FFmpeg renders the final vertical MP4
7. Supabase stores metadata and assets in production

## Folder layout

```text
Backend/
├── brainrot_backend/
│   ├── auth.py
│   ├── config.py
│   ├── container.py
│   ├── core/
│   │   ├── models/
│   │   └── storage/
│   ├── recommendation_system/
│   └── video_generator/
├── scripts/
├── supabase/
└── tests/
```

### Important modules

- `brainrot_backend/main.py`: app startup, router registration, health endpoint
- `brainrot_backend/container.py`: service composition and storage/auth wiring
- `brainrot_backend/auth.py`: Supabase bearer-token resolution and guest/user scope handling
- `brainrot_backend/core/models`: API and domain models
- `brainrot_backend/core/storage`: memory and Supabase repository/blob implementations
- `brainrot_backend/video_generator`: ingestion, script generation, narration, rendering, video proxying
- `brainrot_backend/recommendation_system`: chats, engagement, recommendation APIs

## Stack

| Layer | Technology |
|---|---|
| HTTP | FastAPI, Uvicorn, asyncio |
| Python | 3.12 |
| Package manager | uv |
| Ingestion | Firecrawl |
| Script planning | CrewAI |
| Script writing | OpenAI |
| Narration | ElevenLabs |
| Rendering | FFmpeg |
| Persistence | Supabase or in-memory/local FS |
| Realtime | SSE |

## Local setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- FFmpeg and FFprobe on `PATH`
- OpenAI, Firecrawl, and ElevenLabs credentials for full pipeline runs

### Install and run

```bash
cd Backend
uv sync
cp .env.example .env
uv run uvicorn brainrot_backend.main:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### Local storage behavior

- If Supabase vars are not set and `BRAINROT_STORAGE_BACKEND=auto`, the backend runs in **memory/local disk** mode.
- If `BRAINROT_STORAGE_BACKEND=supabase`, startup will fail unless the required Supabase credentials are present.

## Environment variables

Copy `.env.example` to `.env`. The most important settings are:

### Core

| Variable | Default | Purpose |
|---|---|---|
| `BRAINROT_ENVIRONMENT` | `development` | Development skips production auth assumptions |
| `BRAINROT_LOG_LEVEL` | `INFO` | Logging level |
| `BRAINROT_API_PREFIX` | `/v1` | API prefix |
| `BRAINROT_PUBLIC_BASE_URL` | empty | Public backend URL for callbacks/webhooks |

### OpenAI + CrewAI

| Variable | Default | Purpose |
|---|---|---|
| `BRAINROT_OPENAI_API_KEY` | empty | Required for OpenAI calls |
| `BRAINROT_OPENAI_MODEL` | `gpt-5.4-mini` | Default model |
| `BRAINROT_OPENAI_REASONING_EFFORT` | `low` | Responses reasoning effort |
| `BRAINROT_PRODUCER_MODE` | `direct_openai` | `direct_openai` or `elevenlabs_native` |
| `BRAINROT_PRODUCER_SOURCE_CHAR_LIMIT` | `30000` | Source size sent into script generation |

### Firecrawl

| Variable | Default | Purpose |
|---|---|---|
| `BRAINROT_FIRECRAWL_API_KEY` | empty | Required for scraping |
| `BRAINROT_FIRECRAWL_BASE_URL` | `https://api.firecrawl.dev` | Firecrawl API base |
| `BRAINROT_FIRECRAWL_SITE_URL_LIMIT` | `8` | Max URLs for site crawl coverage |

### ElevenLabs

| Variable | Default | Purpose |
|---|---|---|
| `BRAINROT_ELEVENLABS_API_KEY` | empty | Required for TTS / agent use |
| `BRAINROT_DEFAULT_ELEVENLABS_VOICE_ID` | empty | Fallback TTS voice |
| `BRAINROT_ELEVENLABS_TOOL_TOKEN` | empty | Tool webhook auth token |
| `BRAINROT_ELEVENLABS_CUSTOM_LLM_TOKEN` | empty | Custom LLM proxy auth token |
| `BRAINROT_NARRATION_MODE` | `elevenlabs_tts` | `elevenlabs_tts` or `elevenlabs_agent` |

### Storage + auth

| Variable | Default | Purpose |
|---|---|---|
| `BRAINROT_STORAGE_BACKEND` | `auto` | `auto`, `memory`, or `supabase` |
| `BRAINROT_SUPABASE_URL` | empty | Supabase project URL |
| `BRAINROT_SUPABASE_SERVICE_ROLE_KEY` | empty | Backend service-role key |
| `BRAINROT_SUPABASE_PUBLIC_URL` | empty | Public bucket base URL |

### Rendering

| Variable | Default | Purpose |
|---|---|---|
| `BRAINROT_RENDER_CONCURRENCY` | `4` | Parallel render jobs |
| `BRAINROT_FFMPEG_BIN` | `ffmpeg` | FFmpeg executable |
| `BRAINROT_FFPROBE_BIN` | `ffprobe` | FFprobe executable |

## API overview

### Health

```http
GET /health
```

### Batches

```http
POST /v1/batches
GET /v1/batches/{batch_id}
GET /v1/batches/{batch_id}/events
GET /v1/batches/{batch_id}/items/{item_id}/video
POST /v1/batches/{batch_id}/retry
```

Notes:

- `POST /v1/batches` expects `multipart/form-data`
- `/events` is the SSE stream used by the website chat UI
- `/items/{item_id}/video` now proxies remote video content instead of relying on browser redirects, which keeps playback working better in auth-aware and tunneled environments

### Chats and recommendations

```http
POST /v1/chats
GET /v1/chats
GET /v1/chats/{chat_id}
GET /v1/chats/{chat_id}/shorts
POST /v1/chats/{chat_id}/engagement
GET /v1/chats/{chat_id}/recommendations
```

Library behavior:

- guest requests see the **general library**
- authenticated requests see **only that user’s library**

### Assets and agents

```http
POST /v1/assets/upload
POST /v1/agents/bootstrap
POST /v1/agents/webhooks/elevenlabs
POST /v1/agents/custom-llm
POST /v1/agents/custom-llm/chat/completions
POST /v1/agents/custom-llm/responses
```

### Video edit

```http
GET /v1/video-edit/options
POST /v1/video-edit/previews
GET /v1/video-edit/previews/{batch_id}/video
```

## Pipeline behavior

### Video generation

1. Ingest source with Firecrawl or direct text wrapping
2. Build section coverage with CrewAI
3. Write scripts with OpenAI
4. Run backend QA and repair passes
5. Generate narration and timing data with ElevenLabs
6. Select gameplay/music assets
7. Generate ASS subtitles
8. Render 1080x1920 MP4 with FFmpeg
9. Save output and emit completion events

### Event stream

The frontend consumes `/v1/batches/{batch_id}/events` and renders provider-stage updates such as:

- ingest started / completed
- slot planning started / completed
- script generation pass started
- QA started / repaired / failed / completed
- narration started / completed
- render started / uploaded

## Testing

### Python tests

```bash
cd Backend
uv run pytest
```

### TestSprite artifacts

Backend TestSprite runs are stored under:

- `Backend/testsprite_tests/`
- `brainrot_backend/video_generator/testsprite_tests/`
- `brainrot_backend/recommendation_system/testsprite_tests/`

## Deployment

The current production backend runs on **Railway**.

### Railway

Recommended envs:

```env
BRAINROT_ENVIRONMENT=production
BRAINROT_STORAGE_BACKEND=supabase
BRAINROT_PUBLIC_BASE_URL=https://backend-production-<id>.up.railway.app
BRAINROT_SUPABASE_URL=https://<project-ref>.supabase.co
BRAINROT_SUPABASE_SERVICE_ROLE_KEY=...
BRAINROT_SUPABASE_PUBLIC_URL=https://<project-ref>.supabase.co
```

### Supabase

Before first production use:

1. Create a Supabase project
2. Apply the schema from `supabase/` / SQL files you are using for the current deployment
3. Enable Google auth if the website uses Google sign-in
4. Add the service-role and public URL envs to Railway

## Notes

- `uuid.UUID` route typing is used for validation on key path params
- production playback is designed to work through same-origin proxy routes instead of direct remote redirects
- auth-aware storage and chat scoping are now part of the backend contract, not just frontend filtering
