# Backend

The FastAPI service that drives Draftr. It has two backend domains:

- `video_generator`: source ingest, scripting, narration, subtitle timing, asset selection, and FFmpeg render
- `recommendation_system`: chat library, reel retention tracking, and recommendation scoring

The live video pipeline ingests content through **Firecrawl**, generates narration scripts through **OpenAI**, narrates each script with the **ElevenLabs Narrator agent**, extracts word-level timings with **ElevenLabs Forced Alignment**, and composes the final 1080x1920 H.264 video with **FFmpeg**. Progress streams to the frontend over **SSE** at every stage.

In development the service runs entirely without external infrastructure — it uses an in-memory repository and writes rendered videos to `data/` on local disk. Switching to Supabase for production requires only adding three env vars.

## Folder layout

```text
Backend/
├── brainrot_backend/
│   ├── config.py
│   ├── container.py
│   ├── main.py
│   ├── recommendation_system/
│   │   ├── routes.py
│   │   └── service.py
│   ├── shared/
│   │   ├── models/
│   │   └── storage/
│   └── video_generator/
│       ├── integrations/
│       ├── render/
│       ├── routes/
│       ├── services/
│       └── workers/
├── scripts/
├── sql/
├── supabase/
└── tests/
```

### What goes where

- `brainrot_backend/main.py`: FastAPI app wiring and router registration
- `brainrot_backend/container.py`: dependency container and infrastructure composition
- `brainrot_backend/core/models`: shared API and domain models
- `brainrot_backend/core/storage`: in-memory and Supabase repositories/blob storage
- `brainrot_backend/video_generator`: all code required to turn source material into rendered vertical videos
- `brainrot_backend/recommendation_system`: all code required to track reel engagement and recommend follow-up generations
- `tests/`: backend test coverage, split across pipeline, integrations, subtitles, and API behavior

## Stack

| Layer | Technology |
|---|---|
| HTTP framework | FastAPI, Uvicorn, asyncio |
| Language | Python 3.12+ |
| Package manager | UV |
| Script generation | OpenAI GPT |
| TTS + alignment | ElevenLabs Narrator agent, ElevenLabs Forced Alignment API |
| Content ingestion | Firecrawl (URL scraping, PDF parsing) |
| Video render | FFmpeg (H.264 + AAC, 1080x1920) |
| Storage (prod) | Supabase Postgres + Supabase Storage |
| Storage (dev) | In-memory repository + local filesystem |
| Realtime | SSE via `EventBroker` |

## Local Setup

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) installed
- FFmpeg and FFprobe on `PATH` (`brew install ffmpeg` on macOS)
- API keys for ElevenLabs, OpenAI, and Firecrawl

### Install and run

```bash
cd Backend
uv sync
cp .env.example .env
# Fill in your keys (see Environment Variables below)
uv run uvicorn brainrot_backend.main:app --reload --port 8000
```

Visit `http://127.0.0.1:8000/health` to confirm the service is up.

On first startup the backend auto-seeds gameplay clips and subtitle fonts from `assets/` when `BRAINROT_AUTO_SEED_ASSETS=true`. You can also trigger it manually:

```bash
curl -X POST http://127.0.0.1:8000/v1/agents/bootstrap
```

### Running tests

```bash
uv run pytest
```

Tests use the in-memory backends and do not call any external APIs.

## Environment Variables

Copy `.env.example` to `.env` and fill in the values below.

### Core

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_ENVIRONMENT` | yes | `development` | `development` skips auth checks and uses local storage |
| `BRAINROT_LOG_LEVEL` | no | `INFO` | Python logging level |
| `BRAINROT_API_PREFIX` | no | `/v1` | Route prefix for all API endpoints |
| `BRAINROT_PUBLIC_BASE_URL` | no | | Externally reachable URL — required for ElevenLabs webhooks |

### OpenAI

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_OPENAI_API_KEY` | yes | | OpenAI API key, proxied through the custom LLM endpoint |
| `BRAINROT_OPENAI_MODEL` | no | `gpt-5.4-mini` | Model name passed to OpenAI |
| `BRAINROT_OPENAI_REASONING_EFFORT` | no | `low` | Reasoning effort passed to OpenAI Responses calls |
| `BRAINROT_OPENAI_BASE_URL` | no | `https://api.openai.com/v1` | OpenAI API base URL |

### Firecrawl

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_FIRECRAWL_API_KEY` | yes | | Firecrawl API key for URL scraping and PDF parsing |
| `BRAINROT_FIRECRAWL_BASE_URL` | no | `https://api.firecrawl.dev` | Firecrawl API base URL |
| `BRAINROT_FIRECRAWL_SCRAPE_MAX_AGE_MS` | no | `172800000` | Cache TTL for scraped content (2 days) |
| `BRAINROT_FIRECRAWL_SITE_URL_LIMIT` | no | `8` | Max URLs crawled per batch |
| `BRAINROT_FIRECRAWL_REQUEST_TIMEOUT_SECONDS` | no | `120` | HTTP timeout for scrape requests |
| `BRAINROT_FIRECRAWL_REQUEST_RETRIES` | no | `3` | Retry attempts with exponential backoff |

### ElevenLabs

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_ELEVENLABS_API_KEY` | yes | | ElevenLabs API key |
| `BRAINROT_ELEVENLABS_BASE_URL` | no | `https://api.elevenlabs.io` | ElevenLabs API base URL |
| `BRAINROT_DEFAULT_ELEVENLABS_VOICE_ID` | no | | Fallback narrator voice ID |
| `BRAINROT_ELEVENLABS_MODEL_ID` | no | `eleven_flash_v2` | TTS model |
| `BRAINROT_ELEVENLABS_TOOL_TOKEN` | yes | | Bearer token for Producer agent tool webhooks |
| `BRAINROT_ELEVENLABS_CUSTOM_LLM_TOKEN` | yes | | Bearer token for the OpenAI proxy endpoint |
| `BRAINROT_ELEVENLABS_WEBHOOK_SECRET` | no | | HMAC secret for ElevenLabs webhook signature verification |

### Agents

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_PRODUCER_MODE` | no | `direct_openai` | `direct_openai` or `elevenlabs_native` |
| `BRAINROT_PRODUCER_TIMEOUT_SECONDS` | no | `180` | Max wait time for Producer agent response |
| `BRAINROT_NARRATOR_TIMEOUT_SECONDS` | no | `120` | Max wait time for Narrator agent response |
| `BRAINROT_CONVERSATION_IDLE_SECONDS` | no | `6.0` | Idle timeout before closing an agent conversation |
| `BRAINROT_NARRATOR_MIN_SPEECH_SECONDS` | no | `20.0` | Minimum acceptable narration length |

### Script generation

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_SCRIPT_MIN_WORDS` | no | `80` | Minimum words per narration script |
| `BRAINROT_SCRIPT_MAX_WORDS` | no | `100` | Maximum words per narration script |
| `BRAINROT_SCRIPT_TARGET_MIN_SECONDS` | no | `25.0` | Target minimum duration at TTS speed |
| `BRAINROT_SCRIPT_TARGET_MAX_SECONDS` | no | `30.0` | Target maximum duration at TTS speed |
| `BRAINROT_NARRATOR_TTS_SPEED` | no | `1.2` | TTS playback speed multiplier |
| `BRAINROT_PRODUCER_CHUNK_CONCURRENCY` | no | `4` | Parallel Producer agent chunks |
| `BRAINROT_PRODUCER_SOURCE_CHAR_LIMIT` | no | `30000` | Max source characters sent to Producer |

### Rendering

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_RENDER_CONCURRENCY` | no | `4` | Parallel FFmpeg render jobs |
| `BRAINROT_FFMPEG_BIN` | no | `ffmpeg` | Path to FFmpeg binary |
| `BRAINROT_FFPROBE_BIN` | no | `ffprobe` | Path to FFprobe binary |
| `BRAINROT_ALLOWED_GAMEPLAY_GAMES_CSV` | no | `gta-5,minecraft,roblox,subway-surfers` | Allowed gameplay game tags |
| `BRAINROT_AUTO_SEED_ASSETS` | no | `true` | Auto-seed clips and fonts from `assets/` on startup |

### Supabase storage

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_STORAGE_BACKEND` | no | `auto` | Storage backend: `auto`, `supabase`, or `memory` |
| `BRAINROT_SUPABASE_URL` | no | | Supabase project API URL |
| `BRAINROT_SUPABASE_SERVICE_ROLE_KEY` | no | | Supabase service role key |
| `BRAINROT_SUPABASE_PUBLIC_URL` | no | | Public-facing blob URL for generated video links |

## API Reference

### Health

```
GET /health
Response: { "status": "ok" }
```

### Batches

**Create batch** — triggers the full video generation pipeline

```
POST /v1/batches
Content-Type: multipart/form-data

Fields:
  source_url?         string   URL to scrape (article, website, or PDF)
  source_kind?        enum     article | website | pdf_url | pdf_upload
  file?               file     PDF upload (use instead of source_url)
  count               int      5–15 — number of videos to generate
  chat_id?            string   Associate batch with a chat session
  title_hint?         string   Override the auto-detected source title
  premium_audio?      bool     Use premium TTS voice (default false)

Response: BatchEnvelope
{
  "batch": { id, chat_id, source_kind, source_url, title_hint,
             requested_count, status, premium_audio, created_at, ... },
  "items": [ { id, batch_id, item_index, status, script, output_url, ... } ]
}
```

**Batch statuses:** `queued` → `ingesting` → `scripting` → `rendering` → `completed` / `partial_failed` / `failed`

**Item statuses:** `queued` → `narrating` → `selecting_assets` → `rendering` → `uploaded` / `failed`

---

**Get batch**

```
GET /v1/batches/{batch_id}
Response: BatchEnvelope
```

---

**Stream batch events (SSE)**

```
GET /v1/batches/{batch_id}/events?last_event_id=0
Content-Type: text/event-stream

Event types:
  status                  Batch status changed
  log                     Pipeline log line { stage, message, elapsed_seconds }
  source_ingested         { title, source_kind, url_count, elapsed_seconds }
  producer_conversation_started
  producer_tool_called
  scripts_ready
  narrator_conversation_started
  narrator_audio_ready
  alignment_ready
  render_started
  item_completed          { item_id, item_index, output_url }
  batch_completed         { completed_count, failed_count }
  error
  done
```

---

**Get video file**

```
GET /v1/batches/{batch_id}/items/{item_id}/video
Response: FileResponse (MP4) in dev, or RedirectResponse to Supabase URL in prod
404 if not yet rendered
```

---

**Retry failed items**

```
POST /v1/batches/{batch_id}/retry
Response: { "batch": BatchRecord, "retried_item_ids": ["uuid", ...] }
```

---

### Chats

**Create chat**

```
POST /v1/chats
Content-Type: application/json
Body (all optional): { "title": string, "source_label": string, "source_url": string }

Response: ChatEnvelope { "chat": ChatRecord }
```

**List chats** (returns only sessions with at least one exported video)

```
GET /v1/chats
Response: { "items": [ ChatRecord, ... ] }
```

**Get chat**

```
GET /v1/chats/{chat_id}
Response: ChatEnvelope
```

**Get chat shorts** (all completed videos in this chat session)

```
GET /v1/chats/{chat_id}/shorts
Response: { "chat_id": string, "chat": ChatRecord, "items": [ GeneratedAsset, ... ] }
```

---

### Assets

**Upload asset**

```
POST /v1/assets/upload
Content-Type: multipart/form-data

Fields:
  file          file     Asset file (MP4, TTF, OTF, MP3, etc.)
  kind          enum     gameplay | music | font | overlay
  tags          string   Comma-separated tags (e.g. "gta-5,gameplay")
  metadata_json string   JSON string with extra metadata

Response: { "asset": AssetRecord }
```

---

### Agents

**Bootstrap ElevenLabs agents** (creates Producer and Narrator agents if they don't exist)

```
POST /v1/agents/bootstrap
Response: { "agents": [ AgentConfigRecord, ... ], "tool_ids": [ string, ... ] }
```

**Custom LLM proxy** (ElevenLabs forwards here to call OpenAI)

```
POST /v1/agents/custom-llm
POST /v1/agents/custom-llm/chat/completions
POST /v1/agents/custom-llm/responses
Authorization: Bearer {BRAINROT_ELEVENLABS_CUSTOM_LLM_TOKEN}

Proxies the request to OpenAI and streams the response back.
```

**Script bundle webhook** (called by the Producer agent via ElevenLabs tool)

```
POST /v1/agents/tools/submit-script-bundle
Authorization: Bearer {BRAINROT_ELEVENLABS_TOOL_TOKEN}

Body: {
  "batch_id": string,
  "scripts": [ ScriptDraft, ... ],
  "source_brief": { ... }
}
Response: { "status": "ok" }
```

**ElevenLabs webhook** (signature-verified event receiver)

```
POST /v1/agents/webhooks/elevenlabs
Headers: elevenlabs-signature: hmac_sha256(body, BRAINROT_ELEVENLABS_WEBHOOK_SECRET)
Response: { "status": "ok", "event_type": string }
```

---

### Video Edit

**Get available presets**

```
GET /v1/video-edit/options
Response: {
  "gameplay_assets": [ AssetRecord, ... ],
  "subtitle_presets": [
    { "id": "karaoke_sweep",       "label": "Karaoke Sweep",        "font_name": "Montserrat ExtraBold" },
    { "id": "single_word_pop",     "label": "Single Word Pop",      "font_name": "Komika Axis" },
    { "id": "single_word_pop_bebas","label": "Single Word Pop",     "font_name": "Bebas Neue" },
    { "id": "single_word_pop_anton","label": "Single Word Pop",     "font_name": "Anton" },
    { "id": "single_word_pop_lilita","label": "Single Word Pop",    "font_name": "Lilita One" }
  ]
}
```

**Create preview**

```
POST /v1/video-edit/previews
Content-Type: application/json

Body: {
  "title": string,
  "narration_text": string,   // 50–200 words
  "gameplay_asset_id": uuid,
  "subtitle_preset_id": string,
  "premium_audio": bool,
  "music_asset_id": uuid | null
}
Response: { "batch": BatchRecord, "item": BatchItemRecord }
```

**Get preview video**

```
GET /v1/video-edit/previews/{batch_id}/video
Response: FileResponse or RedirectResponse — 404 if not ready
```

---

## Pipeline

The `BatchOrchestrator` in `src/brainrot_backend/workers/orchestrator.py` runs each batch through six stages:

1. **Ingest** — Firecrawl scrapes the URL or parses the PDF. Raw text is wrapped directly. Output is clean ranked markdown.

2. **Script generation** — Source content is chunked and sent to the ElevenLabs Producer agent. The agent calls `submit-script-bundle` with 5-15 `ScriptDraft` objects. Each script is 80-100 words targeting a 25-30 second read at 1.2x TTS speed. A QA loop retries generic or too-short scripts up to 3 times.

3. **Narration** — For each script, the ElevenLabs Narrator agent generates an MP3. The ElevenLabs Forced Alignment API then extracts per-word timestamps so subtitles sync precisely to the voice.

4. **Asset selection** — `AssetSelector` ranks gameplay clips and music tracks by matching their tags to the script's `gameplay_tags` and `music_tags`. Subtitle presets are rotated across items to avoid visual repetition.

5. **Subtitle generation** — `SubtitleGenerator` builds an ASS (Advanced SubStation Alpha) subtitle file from the word timings. Five presets are available, each with its own font and animation style (karaoke sweep or per-word pop).

6. **FFmpeg render** — Gameplay is looped to the narration duration, music is sidechain-compressed at 10:1 ratio so it ducks under the voice, subtitles are burned in, and the output is encoded as 1080x1920 H.264 MP4.

## Database Schema

The Supabase/Postgres schema is in `sql/schema.sql`. Run it in the Supabase SQL editor to create all tables before first use in production.

Key tables:

| Table | Purpose |
|---|---|
| `chats` | Chat session records with cover image and export counts |
| `batches` | Video generation job records |
| `batch_items` | Individual video records within a batch |
| `batch_events` | Append-only event log powering the SSE stream |
| `source_documents` | Ingested and cleaned markdown content |
| `assets` | Gameplay clips, music tracks, fonts, and overlays |
| `agent_configs` | ElevenLabs Producer and Narrator agent registrations |
| `agent_conversations` | Per-item ElevenLabs conversation transcripts and audio refs |
| `alignment_jobs` | Word-timing records for subtitle sync |

## Deployment to Railway

1. Create a new Railway service with **root directory** set to `Backend`
2. Add all required env vars from `.env.example` in the Railway dashboard
3. Set `BRAINROT_PUBLIC_BASE_URL` to the Railway public domain so ElevenLabs webhooks can reach the service
4. Set `BRAINROT_ENVIRONMENT=production`
5. Railway auto-detects the start command from `pyproject.toml`

For Supabase, create a project, run `sql/schema.sql` in the SQL editor, and add:

```env
BRAINROT_STORAGE_BACKEND=supabase
BRAINROT_SUPABASE_URL=https://<project>.supabase.co
BRAINROT_SUPABASE_SERVICE_ROLE_KEY=...
BRAINROT_SUPABASE_PUBLIC_URL=https://<project>.supabase.co/storage/v1/object/public
```
