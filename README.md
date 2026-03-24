# Draftr

Draftr turns any URL, PDF, or raw text into short-form vertical videos in **brainrot format**gameplay footage (GTA-5, Minecraft, Roblox, Subway Surfers) with karaoke-style subtitles and AI-synced narration. Drop in a research paper, news article, or study notes and get back 5-15 unique 25-30 second videos ready for TikTok, YouTube Shorts, or Instagram Reels.

The pipeline is built on two core technologies. **Firecrawl** handles all source ingestionscraping URLs, parsing PDFs, and ranking extracted content so the AI works from clean, relevant markdown. **ElevenLabs Agents** drive the creative work: a Producer agent generates 5-15 distinct narration scripts from the ingested content, and a Narrator agent converts each script to MP3 with word-level forced alignment so subtitles lock precisely to the voice. FFmpeg assembles the final video and everything streams back to the chat UI over SSE.

## Service READMEs

The root README is the system overview. Service-specific environment variables, endpoints, and deployment notes live in their own READMEs.

| Service | README |
|---|---|
| Backend API | [`Backend/README.md`](Backend/README.md) |
| Website | [`website/README.md`](website/README.md) |

## What The Platform Does

| Capability | What Happens | Technology Used |
|---|---|---|
| **Source ingestion** | URL is scraped or PDF is parsed into ranked markdown. Raw text is accepted directly. | **Firecrawl** API for scraping and PDF parsing |
| **Script generation** | 5-15 unique 80-100 word narration scripts are generated from the source content. Each script targets a 25-30 second read at 1.2x TTS speed. | **ElevenLabs Producer agent** backed by **OpenAI GPT** via custom LLM proxy |
| **Narration & alignment** | Each script is narrated to MP3, then word-level forced alignment extracts precise timestamps for karaoke subtitle sync. | **ElevenLabs Narrator agent** + **ElevenLabs Forced Alignment API** |
| **Asset selection** | Best-fit gameplay clip and music track are ranked and paired for each video. | `AssetSelector` over pre-seeded clip and music library |
| **Storage** | In development the backend writes to local disk with an in-memory repository. In production all assets and metadata go to Supabase Storage and Postgres. | **Supabase** (prod) / local FS + in-memory (dev) |

## Architecture

```
Browser (Next.js)
    │
    │  REST + SSE (via /api/brainrot proxy routes)
    ▼
FastAPI Backend
    │
    ├── POST /v1/batches ──► BatchOrchestrator
    │                            │
    │                            ├── 1. Ingest (Firecrawl)
    │                            ├── 2. Script gen (ElevenLabs Producer agent)
    │                            ├── 3. Narrate + align (ElevenLabs Narrator agent)
    │                            ├── 4. Asset selection
    │                            ├── 5. Subtitle generation (ASS + word timings)
    │                            └── 6. FFmpeg render → Supabase / local FS
    │
    ├── GET  /v1/batches/{id}/events  ──► SSE event stream
    ├── POST /v1/chats                ──► ChatService
    └── POST /v1/agents/bootstrap     ──► ElevenLabs agent init
```

## Services

### Website `website/`

A Next.js 16 app with React 19, TypeScript, and CSS Modules. It contains the marketing pages, the chat interface, the TikTok-style shorts feed, and thin server-side proxy routes that forward browser requests to the FastAPI backend.

Key pages:

- `/`Landing page with hero, feature overview, and how-it-works walkthrough
- `/chat`Main chat interface: submit sources, watch live pipeline log stream, view generated videos
- `/shorts`Browse all chat sessions and watch generated videos in a full-screen vertical feed
- `/about`Five-section visual walkthrough of the full pipeline
- `/video-edit`Experimental custom narration and asset picker

### Backend `Backend/`

A FastAPI service backed by asyncio. It owns the full pipeline from source ingestion through FFmpeg render and exposes REST endpoints plus an SSE event stream.

Core route groups:

- `POST /v1/batches`Create a batch (trigger video generation from a URL, PDF, or text)
- `GET  /v1/batches/{id}`Get batch status and all item details
- `GET  /v1/batches/{id}/events`SSE stream of live pipeline progress
- `GET  /v1/batches/{id}/items/{item_id}/video`Download or redirect to the final video file
- `POST /v1/batches/{id}/retry`Retry failed items
- `POST /v1/chats`Create a chat session
- `GET  /v1/chats`List all chats
- `GET  /v1/chats/{id}/shorts`List all generated videos for a chat
- `POST /v1/agents/bootstrap`Initialize Producer and Narrator ElevenLabs agents
- `POST /v1/video-edit/previews`Generate a custom preview video

### Pipeline`BatchOrchestrator`

The `BatchOrchestrator` in `Backend/src/brainrot_backend/workers/orchestrator.py` runs each batch through six sequential stages:

1. **Ingest**Firecrawl scrapes the URL or parses the PDF into ranked markdown
2. **Script generation**The Producer agent generates 5-15 unique 80-100 word scripts in parallel chunks
3. **Narration & alignment**For each script the Narrator agent produces an MP3, then forced alignment extracts word-level timestamps
4. **Asset selection**`AssetSelector` ranks and pairs a gameplay clip with a music track for each video
5. **Subtitle generation**`SubtitleGenerator` builds an ASS file from word timings with an animation preset (pop-in, fade, or slide)
6. **FFmpeg render**Overlays looped gameplay, sidechain-mixes music under narration, burns in subtitles, and outputs 1080x1920 H.264 MP4

SSE progress events are published at every stage so the frontend chat view updates in real time.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Framer Motion, CSS Modules |
| Backend | FastAPI, Python 3.12, asyncio, Uvicorn |
| Package management | UV (backend), npm (frontend) |
| Script generation | ElevenLabs Agents (Producer), OpenAI GPT via custom LLM proxy |
| TTS + alignment | ElevenLabs Narrator agent, ElevenLabs Forced Alignment API |
| Source ingestion | Firecrawl API |
| Video render | FFmpeg (H.264 + AAC, 1080x1920) |
| Storage (prod) | Supabase Postgres + Supabase Storage |
| Storage (dev) | In-memory repository + local filesystem |
| Realtime | SSE via `EventBroker` |
| Deployment | Railway (two separate services) |

## Local Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- [UV](https://docs.astral.sh/uv/)Python package manager
- FFmpeg installed and on `PATH`
- API keys for ElevenLabs, OpenAI, and Firecrawl (see env vars below)

### 1. Clone the repo

```bash
git clone <repo-url>
cd ideas
```

### 2. Set up the backend

```bash
cd Backend

# Install dependencies
uv sync

# Copy the env template and fill in your keys
cp .env.example .env
```

Open `.env` and set at minimum:

```env
BRAINROT_ENVIRONMENT=development

# RequiredAI and scraping
BRAINROT_OPENAI_API_KEY=sk-...
BRAINROT_FIRECRAWL_API_KEY=fc-...
BRAINROT_ELEVENLABS_API_KEY=...

# Requiredagent auth tokens (generate any random strings for local dev)
BRAINROT_ELEVENLABS_TOOL_TOKEN=local-tool-token
BRAINROT_ELEVENLABS_CUSTOM_LLM_TOKEN=local-llm-token

# Optionalleave blank to use in-memory storage (no Supabase needed locally)
BRAINROT_SUPABASE_URL=
BRAINROT_SUPABASE_SERVICE_ROLE_KEY=
```

Start the backend:

```bash
uv run uvicorn brainrot_backend.main:app --reload --port 8000
```

The API is now running at `http://127.0.0.1:8000`. Visit `http://127.0.0.1:8000/health` to verify.

> **Note:** When `BRAINROT_ENVIRONMENT=development` and no Supabase credentials are set, the backend uses an in-memory repository and writes rendered videos to `data/` on local disk. No database setup is required.

### 3. Seed assets (first run only)

Pre-loaded gameplay clips, music tracks, and subtitle fonts live in `assets/`. On first startup with `BRAINROT_AUTO_SEED_ASSETS=true` in your `.env` the backend seeds them automatically. You can also trigger seeding via the bootstrap endpoint:

```bash
curl -X POST http://127.0.0.1:8000/v1/agents/bootstrap
```

### 4. Set up the website

```bash
cd ../website

# Install dependencies
npm install

# Copy env template
cp .env.example .env.local
```

`.env.local` only needs one line for local development:

```env
BRAINROT_BACKEND_URL=http://127.0.0.1:8000
```

Start the dev server:

```bash
npm run dev
```

The website is now running at `http://localhost:3000`.

### 5. Generate your first video

1. Open `http://localhost:3000`
2. Click **Start** on the landing page or go to `/chat`
3. Paste a URL (e.g. a Wikipedia article), upload a PDF, or type/paste raw text
4. Hit **Generate**the pipeline runs and streams progress events live
5. When rendering finishes the video appears inline. Go to `/shorts` to browse all generated videos in a full-screen feed.

### Running tests

```bash
cd Backend
uv run pytest
```

Tests use in-memory backends and do not require any external API keys.

## Deployment

Both services deploy to [Railway](https://railway.app) from the same repo with separate root directory settings.

### Backend service

- **Root directory:** `Backend`
- **Start command:** auto-detected from `pyproject.toml`
- Add all env vars from `.env.example` in the Railway dashboard

### Website service

- **Root directory:** `website`
- **Start command:** auto-detected from `package.json`
- Add one env var:
  ```
  BRAINROT_BACKEND_URL=https://${{Backend.RAILWAY_PUBLIC_DOMAIN}}
  ```

Railway's `${{Backend.RAILWAY_PUBLIC_DOMAIN}}` reference wires the website to the backend service automatically once both are in the same project.

### Production storage

For production, create a [Supabase](https://supabase.com) project and run `Backend/sql/schema.sql` in the SQL editor to create all tables. Then add the Supabase env vars to your Railway backend service:

```env
BRAINROT_SUPABASE_URL=https://<project>.supabase.co
BRAINROT_SUPABASE_SERVICE_ROLE_KEY=...
BRAINROT_SUPABASE_PUBLIC_URL=https://<project>.supabase.co/storage/v1/object/public
```

## Environment Variables

### Backend (`Backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_ENVIRONMENT` | yes | `development` | `development` or `production` |
| `BRAINROT_OPENAI_API_KEY` | yes || OpenAI API key (used via ElevenLabs custom LLM proxy) |
| `BRAINROT_OPENAI_MODEL` | no | `gpt-5` | OpenAI model name |
| `BRAINROT_FIRECRAWL_API_KEY` | yes || Firecrawl API key for URL scraping and PDF parsing |
| `BRAINROT_ELEVENLABS_API_KEY` | yes || ElevenLabs API key |
| `BRAINROT_ELEVENLABS_TOOL_TOKEN` | yes || Auth token for ElevenLabs agent tool webhooks |
| `BRAINROT_ELEVENLABS_CUSTOM_LLM_TOKEN` | yes || Auth token for the OpenAI proxy endpoint |
| `BRAINROT_ELEVENLABS_WEBHOOK_SECRET` | no || Signature secret for ElevenLabs webhook verification |
| `BRAINROT_DEFAULT_ELEVENLABS_VOICE_ID` | no || Default narrator voice ID |
| `BRAINROT_SUPABASE_URL` | no || Supabase project URL (omit to use in-memory storage) |
| `BRAINROT_SUPABASE_SERVICE_ROLE_KEY` | no || Supabase service role key |
| `BRAINROT_SUPABASE_PUBLIC_URL` | no || Supabase public storage URL for video links |
| `BRAINROT_RENDER_CONCURRENCY` | no | `4` | Number of parallel FFmpeg render jobs |
| `BRAINROT_PRODUCER_CHUNK_CONCURRENCY` | no | `4` | Number of parallel script generation chunks |
| `BRAINROT_SCRIPT_MIN_WORDS` | no | `80` | Minimum words per narration script |
| `BRAINROT_SCRIPT_MAX_WORDS` | no | `100` | Maximum words per narration script |
| `BRAINROT_NARRATOR_TTS_SPEED` | no | `1.2` | TTS playback speed (targets 25-30 sec per script) |
| `BRAINROT_AUTO_SEED_ASSETS` | no | `true` | Auto-seed gameplay clips and music on startup |

### Website (`website/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_BACKEND_URL` | yes | `http://127.0.0.1:8000` | Base URL of the FastAPI backend |
