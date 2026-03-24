# Website

Next.js 16 frontend for Draftr. Contains the landing page, the chat interface where users submit content and watch video generation happen live, the TikTok-style shorts feed, the about walkthrough, and thin server-side proxy routes that forward browser requests to the FastAPI backend.

## Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 16, React 19, TypeScript |
| Animations | Framer Motion 12 |
| Icons | Lucide React |
| Styling | CSS Modules |
| Fonts | DM Sans (body), Instrument Serif (display) |
| Package manager | npm |

## Local Setup

### Prerequisites

- Node.js 20+
- The backend running at `http://127.0.0.1:8000` (see `Backend/README.md`)

### Install and run

```bash
cd website
npm install
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

Open `http://localhost:3000`.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BRAINROT_BACKEND_URL` | yes | `http://127.0.0.1:8000` | Base URL of the FastAPI backend. Must be set in all deployed environments — there is no production fallback. |

## Pages

### `/` Landing page

Hero section with the tagline, a stats block, feature cards for each input mode (URL, PDF, paste), a how-it-works walkthrough, and a CTA to the chat page.

### `/chat` Chat interface

The main workspace. Users submit a URL, PDF, or raw text. A batch is created, the backend streams progress events over SSE, and the chat view renders a live log stream alongside per-item status cards. Completed videos appear inline and are saved to localStorage for the shorts gallery.

**Input modes** (via `PromptInputBox`):

| Mode | What the user provides | Backend field |
|---|---|---|
| URL | Article, website, or PDF link | `source_url` |
| File upload | PDF drag-drop or file picker | `file` (multipart) |
| Raw text | Paste notes, transcripts, or content | Sent as `source_url` with `source_kind=raw_text` |

**Batch count** — configurable from 5 to 15 videos, stored in `localStorage` under `draftr:chat-batch-count`.

**SSE events** rendered in the live log:

| Event | Displayed as |
|---|---|
| `source_ingested` | Source loaded, title shown |
| `producer_conversation_started` | Script generation started |
| `scripts_ready` | N scripts ready |
| `narrator_audio_ready` | Audio generated for item N |
| `alignment_ready` | Subtitles synced for item N |
| `render_started` | FFmpeg started for item N |
| `item_completed` | Video N ready with inline player |
| `batch_completed` | Summary of completed vs failed |
| `error` | Error message with retry hint |

**Persistence** — chat session ID is stored in `localStorage` under `draftr:chat-session-id`. Batch history and completed shorts are stored per-chat under `draftr-chat-run:{chatId}`.

### `/shorts` Shorts gallery

Left sidebar lists all chat sessions fetched from `GET /v1/chats`. Selecting a chat loads all its generated videos from `GET /v1/chats/{id}/shorts` (falls back to localStorage if the backend is unavailable). Videos are displayed in a browsable grid.

### `/about` Pipeline walkthrough

Five-section explainer with embedded video examples:
1. What Draftr is
2. How Firecrawl ingests source content
3. How the ElevenLabs Producer agent generates scripts
4. How the Narrator agent and Forced Alignment produce synced subtitles
5. How FFmpeg composes the final video

### `/video-edit` Video edit lab

Experimental workspace for entering custom narration text and picking specific gameplay and subtitle presets. Calls `POST /v1/video-edit/previews` and polls for the rendered output. Reserved for future development.

## API Proxy Routes

All browser requests go through thin Next.js server-side route handlers under `/api/brainrot/`. These proxy to the backend using `BRAINROT_BACKEND_URL` from the server environment so API keys and the backend URL are never exposed to the browser.

| Proxy route | Proxies to |
|---|---|
| `POST /api/brainrot/batches` | `POST /v1/batches` |
| `GET  /api/brainrot/batches/[batchId]` | `GET /v1/batches/{id}` |
| `GET  /api/brainrot/batches/[batchId]/events` | `GET /v1/batches/{id}/events` (SSE) |
| `GET  /api/brainrot/batches/[batchId]/items/[itemId]/video` | `GET /v1/batches/{id}/items/{id}/video` |
| `POST /api/brainrot/chats` | `POST /v1/chats` |
| `GET  /api/brainrot/chats` | `GET /v1/chats` |
| `GET  /api/brainrot/chats/[chatId]` | `GET /v1/chats/{id}` |
| `GET  /api/brainrot/chats/[chatId]/shorts` | `GET /v1/chats/{id}/shorts` |
| `POST /api/brainrot/agents/bootstrap` | `POST /v1/agents/bootstrap` |
| `GET  /api/brainrot/video-edit/options` | `GET /v1/video-edit/options` |
| `POST /api/brainrot/video-edit/previews` | `POST /v1/video-edit/previews` |
| `GET  /api/brainrot/video-edit/previews/[batchId]/video` | `GET /v1/video-edit/previews/{id}/video` |
| `GET  /api/brainrot/health` | `GET /health` |

## localStorage Schema

The frontend stores chat and batch state locally so the shorts gallery works even if the backend is restarted.

**Keys:**

| Key | Contents |
|---|---|
| `draftr:chat-session-id` | Current chat session UUID |
| `draftr:chat-batch-count` | Batch count preference (5–15) |
| `draftr-chat-run:{chatId}` | Full `ChatRunStore` object for the chat |

**`ChatRunStore` shape:**

```typescript
{
  chatId: string,
  updatedAt: string,         // ISO 8601
  batches: [
    {
      chatId, batchId, status,
      sourceLabel, sourceUrl,
      createdAt, updatedAt,
      uploadedCount, requestedCount, failedCount,
      items: [
        {
          itemId, batchId, itemIndex,
          title, sourceLabel, sourceUrl,
          status, outputUrl, previewUrl, thumbnailUrl,
          subtitleStyleLabel, subtitleAnimation, subtitleFontName,
          gameplayAssetPath, estimatedSeconds,
          narrationText, createdAt
        }
      ]
    }
  ]
}
```

## Key Components

### `PromptInputBox`

Multi-modal input dialog. Supports URL input, file drag-drop upload, and raw text paste. Returns a `PromptSendPayload` with the source content and selected mode to the chat page.

### `LiveBatchMessage`

Connects to the SSE stream at `GET /v1/batches/{id}/events`, renders a scrolling activity log with provider icons (Firecrawl, OpenAI, ElevenLabs, FFmpeg), and displays per-item status cards from `queued` through `uploaded`. Saves completed shorts to localStorage on `item_completed` events.

### `Navbar`

Glassmorphic dark navigation bar with links to Chat, Shorts, About, and a GitHub link. Collapses to a mobile menu on small screens.

## Scripts

```bash
npm run dev      # Start development server (http://localhost:3000)
npm run build    # Production build
npm run start    # Run production server
npm run lint     # Run ESLint
```

## Deployment to Railway

1. Create a Railway service with **root directory** set to `website`
2. Railway auto-detects the start command from `package.json`
3. Add one env var:

```env
BRAINROT_BACKEND_URL=https://${{Backend.RAILWAY_PUBLIC_DOMAIN}}
```

`${{Backend.RAILWAY_PUBLIC_DOMAIN}}` is a Railway reference variable — it resolves to the backend service's public domain automatically once both services are in the same project.

> The website has no fallback backend URL in production. If `BRAINROT_BACKEND_URL` is not set, all API calls will fail.
