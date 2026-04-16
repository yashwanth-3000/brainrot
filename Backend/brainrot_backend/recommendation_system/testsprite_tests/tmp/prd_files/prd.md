# Brainrot Backend — Product Requirements Document

## Overview
A FastAPI Python backend that converts URLs, websites, and PDFs into short-form vertical videos (brainrot-style gameplay reels). It handles the full pipeline: content ingestion, AI script production, TTS narration, subtitle rendering, FFmpeg video compositing, and engagement-based recommendation analytics.

## API Base URL
`/v1` (configurable via `BRAINROT_API_PREFIX`)

---

## Feature 1: Video Generator

### 1.1 Batch Creation
- `POST /v1/batches` — Create a new video generation batch
- Request body: `source_url` (string, required), `count` (int, 5-15), `chat_id` (optional UUID), `agent_config_id` (optional), `producer_config_id` (optional), `narrator_config_id` (optional), `premium_audio` (bool), `upload_pdf` (file, optional)
- Response: batch record with `batch_id`, `status`, `requested_count`, `items[]`
- The batch is processed asynchronously; a `BatchOrchestrator` task runs ingestion → scripting → narration → render → upload
- Auth: bearer token (user-scoped) or no token (general library)

### 1.2 Batch Status & Streaming
- `GET /v1/batches/{batch_id}` — Get batch status and item list
- `GET /v1/batches/{batch_id}/events` — SSE stream of real-time batch progress events (ingest, scripts_ready, render, upload, done)
- `GET /v1/batches/{batch_id}/items/{item_id}/video` — Stream the rendered MP4 video (proxied from blob storage or served from local disk)

### 1.3 Retry Failed Items
- `POST /v1/batches/{batch_id}/retry` — Re-run only the failed items in an existing batch

### 1.4 Asset Management
- `POST /v1/assets` — Upload a gameplay clip, music track, or font file
- Assets are tagged and stored in blob storage; AssetSelector picks them by tag overlap for each script

### 1.5 Agent Management (ElevenLabs)
- `POST /v1/agents/bootstrap` — Create/update ElevenLabs producer + narrator agents with current settings
- `POST /v1/agents/custom-llm/chat` and `POST /v1/agents/custom-llm/responses` — Proxy LLM calls from ElevenLabs agents to OpenAI
- `POST /v1/agents/webhook/elevenlabs` — Receive script bundle from ElevenLabs producer agent
- `POST /v1/agents/tool-result` — Submit tool results from agent conversations

### 1.6 Video Edit Preview
- `GET /v1/video-edit/options` — List available subtitle presets and gameplay assets for preview
- `POST /v1/video-edit/previews` — Create a preview render with custom subtitle/gameplay/narration settings
- `GET /v1/video-edit/previews/{preview_id}/video` — Download the preview MP4

### 1.7 Pipeline Processing
- **Ingestion**: FirecrawlClient fetches content from URL/site/PDF → produces markdown source document
- **Scripting**: CrewAIProducerFlow (direct_openai mode) or ElevenLabs agent (elevenlabs_native) → GeneratedBundle of ScriptDrafts
- **Narration**: AgentService.narrate_item → WAV audio + word-level timing via ElevenLabs TTS or agent
- **Subtitles**: SubtitlePreset selection + ASS file generation (karaoke or single-word-pop animation)
- **Render**: FFmpegRenderer composites gameplay + narration + optional music + subtitles → 1080×1920 MP4
- **Upload**: output MP4 uploaded to blob storage; output_url stored on BatchItem

---

## Feature 2: Recommendation System

### 2.1 Chat Management
- `POST /v1/chats` — Create a new chat session (groups related batches)
- `GET /v1/chats` — List chats for the authenticated user (or general library for guests)
- `GET /v1/chats/{chat_id}` — Get a single chat with cover metadata and export summary

### 2.2 Shorts Library
- `GET /v1/chats/{chat_id}/shorts` — List all generated short videos for a chat, with render metadata (subtitle style, font, gameplay, thumbnail)

### 2.3 Engagement Tracking
- `POST /v1/chats/{chat_id}/engagement` — Submit viewer engagement event:
  - Fields: `batch_id`, `item_id`, `viewer_id`, `session_id`, `watch_time_seconds`, `completion_ratio`, `max_progress_seconds`, `replay_count`, `unmuted`, `info_opened`, `open_clicked`, `liked`, `skipped_early`, `metadata`
  - Deduplication: one submission per (batch_id, item_id, viewer_id, session_id)

### 2.4 Recommendations
- `GET /v1/chats/{chat_id}/recommendations?session_id=` — Retention-based recommendations:
  - Returns: top gameplay assets, caption styles, text styles by completion ratio and watch time
  - Requires minimum tracked reels to produce strong recommendation (configurable threshold)
  - Session-scoped: only considers engagement from the provided session_id

---

## Feature 3: Health & Auth

### 3.1 Health Check
- `GET /health` — Returns `{"status": "ok"}`

### 3.2 Authentication
- Bearer JWT (Supabase): scopes requests to authenticated user's library
- No token (guest mode): scopes to general shared library
- Invalid token: 401 Unauthorized

---

## Non-Functional Requirements

- **Concurrency**: `render_concurrency` parallel FFmpeg jobs per batch
- **Resilience**: batch producer retries up to 3 times; items can be individually retried
- **Observability**: SSE event stream for live progress; structured log events per item
- **Portability**: local blob/DB storage (tests), Supabase (production)
- **Security**: asset allowlist (allowed_gameplay_games_csv), auth on batch creation, ownership validation
