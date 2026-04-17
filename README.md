# Draftr

Draftr turns written source material into fully rendered short-form videos.

It takes a URL, a PDF, or raw pasted text, ingests the content, plans coverage across the source, writes multiple short scripts, generates narration, times subtitles, renders vertical MP4s, stores the final outputs in a browsable library, and then uses reel-style retention signals to recommend what kinds of shorts should come next.

Users can try the product immediately in guest mode, or sign in with Google through Supabase Auth and generate into their own personal library. That means the same app now supports both a low-friction demo experience and a real account-based workflow.

I built this after running into the same pattern over and over: useful information lives in articles, docs, and PDFs, but the format people actually spend time consuming is short-form video. The manual path from one to the other is slow and repetitive. Draftr was designed to collapse that into one product flow that can both generate the first batch and learn from what viewers actually keep watching.

To make sure the system behaved reliably, I used TestSprite to test the website flows, deployed flows, recommendation system, authentication flow, and backend generation APIs. That repeated testing loop helped catch playback issues, response-shape bugs, auth edge cases, and state problems while the product was still changing quickly.

## Demo

- Live Demo: [draftr-website.vercel.app](https://draftr-website.vercel.app)
- Demo Video: [youtu.be/66YCp-HzBOg](https://youtu.be/66YCp-HzBOg)

## Repository Overview

This repository includes:

- a unified FastAPI backend in [`Backend/`](Backend/)
- a full Next.js website in [`website/`](website/)
- local render assets and working data in [`assets/`](assets/) and [`data/`](data/)

Inside [`Backend/`](Backend/), the main pieces are:

- [`brainrot_backend/video_generator/`](Backend/brainrot_backend/video_generator/) for ingestion, planning, script generation, narration, subtitles, and rendering
- [`brainrot_backend/recommendation_system/`](Backend/brainrot_backend/recommendation_system/) for chat libraries, reel-level engagement tracking, and follow-up recommendations
- [`brainrot_backend/core/`](Backend/brainrot_backend/core/) for shared models and storage abstractions
- [`supabase/`](Backend/supabase/) for schema and migration-related backend persistence work

The website and backend now work together as one product: the frontend handles the landing page, login, chat workspace, profile, about page, and library views, while the backend ingests content, generates the shorts, stores the outputs, scopes library data between guests and authenticated users, and powers the recommendation system that decides what kind of shorts should come next.

## What Draftr Is

Draftr is a short-form video generation system for turning dense written material into something more watchable.

At the product level, that means:

- a user submits source content
- the system plans multiple distinct short ideas from that source
- each short is written, narrated, subtitled, rendered, and stored
- the final outputs are available in the app library
- viewer retention signals shape what kinds of shorts the system recommends generating next

The goal is not just to summarize text. The goal is to produce a format people will actually finish watching, then learn from that viewing behavior to recommend more useful shorts in the same direction.

## How Draftr Works

Draftr uses a staged generation pipeline:

1. At the input step, the user submits a URL, a PDF, or raw text.
2. The backend normalizes that source into clean text or markdown.
3. CrewAI splits the content into meaningful sections and plans slot coverage across the source.
4. OpenAI writes one short per slot using local section context and pacing constraints.
5. The backend runs QA and repair passes for overlap, stale phrasing, and weak grounding.
6. ElevenLabs generates narration audio and timing data.
7. The subtitle system turns those timings into ASS subtitle tracks.
8. FFmpeg composes the final 1080x1920 video.
9. Supabase stores metadata and media for production library access.
10. The recommendation system watches reel-level engagement and learns which gameplay, caption, and hook combinations should be generated more often.

That is why the current system behaves differently from a one-prompt summarizer. It is designed as a pipeline, not just a single text-generation step.

## How We Tested Using TestSprite

We used TestSprite as a repeated product-feedback loop, not as one final QA step at the end.

### Testing footprint

- `11` recorded dashboard runs
- `144` named TestSprite tests across those runs

### Run progression

| Area | Progression |
|---|---|
| Website local | `6/15 -> 8/15 -> 11/15` |
| Website deployed | `20/24 -> 21/24` |
| Recommendation system | `0/7 -> 5/7` |
| Video generator | `1/10 -> 8/10 -> 0/2` |
| Full backend | `13/15` |

### What improved because of it

- guest mode and Google auth/logout flows
- personal-library scoping between guests and signed-in users
- shorts loading and sidebar reliability
- open-in-new-tab behavior for generated shorts
- UUID validation and API contract correctness
- asset upload validation and SSE handling
- recommendation coverage across chat, engagement, and follow-up generation

### Where the test data lives

- [`website/testsprite_tests/`](website/testsprite_tests/)
- [`Backend/brainrot_backend/recommendation_system/testsprite_tests/`](Backend/brainrot_backend/recommendation_system/testsprite_tests/)
- [`Backend/brainrot_backend/video_generator/testsprite_tests/`](Backend/brainrot_backend/video_generator/testsprite_tests/)
- [`Backend/testsprite_tests/`](Backend/testsprite_tests/)
- [`testsprite/testsprite.md`](testsprite/testsprite.md)
- [`testsprite/testsprite-mcp-issues-report.md`](testsprite/testsprite-mcp-issues-report.md)

## Why This Project Exists

A lot of good information gets trapped in formats most people do not finish consuming.

The usual manual workflow looks like this:

- read the article or PDF
- decide what is actually worth turning into a short
- split the material into multiple hooks
- write each script by hand
- record narration
- build subtitles
- edit the final video
- upload and organize the outputs

That is slow, repetitive, and hard to repeat consistently.

Draftr exists to turn that repeated workflow into a reusable product flow. Instead of rebuilding the same content pipeline by hand for every source, the user drops in the source material once and lets the system generate multiple finished shorts from it.

## Example User Flow

A practical user flow for this project looks like this:

1. A user opens the website and either logs in or continues in guest mode.
2. The user submits an article URL, a PDF, or raw pasted text in the chat workspace.
3. The backend ingests the source and turns it into structured text.
4. CrewAI plans coverage so the batch spreads across different sections of the source.
5. OpenAI writes multiple short scripts from those planned slots.
6. The backend runs QA and repair passes before narration and rendering.
7. The final videos are stored and shown in the library.
8. If the user is signed in, those videos belong to that user. If not, they remain in the general library flow.
9. As people watch those shorts, Draftr tracks retention signals and starts recommending more of the combinations that are actually working.

That changes the workflow from "manually turn one source into one edited video" to "submit a source once and get a batch of library-ready shorts."

## Why This Beats The Manual Short-Video Workflow

For this project's use case, a structured generation pipeline is better than doing every step manually because it preserves the important parts of the workflow:

- the source stays grounded in the original material
- multiple sections can be covered in one pass
- each slot can aim at a different angle family
- narration, subtitles, and rendering are part of the same pipeline
- the outputs are stored and reusable inside the product library
- guest access and signed-in access can coexist in the same app
- the recommendation system can learn from retention instead of guessing blindly what to generate next

This is especially useful for educational, technical, or launch-oriented content, where the hard part is usually not finding information. The hard part is packaging it into a format people will actually consume.

## Guest Mode And Personal Libraries

The product now supports two library modes:

- guest mode, where users can skip login and still use the generator
- authenticated mode, where users sign in and generate into their own library

That matters because the app is no longer only a local prototype. It now supports:

- Supabase Auth for account identity
- Google login for the main auth flow
- email/password login for testing and support workflows
- user-scoped history and saved shorts
- a profile page with usage and account details

So the important shift is not just "the app has login now." The important shift is that Draftr now has both a general library experience and a user-specific library experience in the same product.

## How The Recommendation System Works

The recommendation system is meant to feel closer to a reels feed than a static file browser.

When someone watches generated shorts inside a chat library, Draftr does not just count views and stop there. It records reel-level engagement signals such as:

- watch time
- completion ratio
- how far the viewer actually reached in the video
- replay count
- whether the viewer unmuted
- whether they opened the info panel
- whether they clicked through
- whether they liked the short
- whether they skipped early

That data is grouped per short and scored to understand which combinations are actually holding attention. So the system is learning from behavior, not from guesses.

Instead of only asking "which video got views?", the system asks things like:

- which gameplay family kept people watching longer
- which caption style had better retention
- which hook or text style got stronger completion and follow-up actions

Right now, the backend ranks three recommendation dimensions:

- gameplay style
- caption style
- text or hook style

After Draftr has enough viewing data from at least three reels in a session, it produces a winning profile and a follow-up generation prompt. In other words, it starts learning what kind of shorts this viewer or this library is responding to, then recommends making more of those exact combinations.

So the product behavior is intentionally similar to how reels products learn from retention, except the goal is different. Instead of optimizing for random brain-rot consumption, Draftr is trying to learn which educational, technical, or useful short-form videos keep attention best, then generate more of that.

The important product idea is this: you still get the addictive, swipeable, reels-style feedback loop, but instead of being pushed toward empty content, the system is pushing toward videos where you can actually learn something.

## Built-In AI Tools Vs This Project

There are already many tools that can summarize an article, rewrite a paragraph, or generate a short script from a prompt.

Those tools are good for isolated text-generation tasks.

Draftr is stronger for **source-to-short-form-video generation** because it does not stop at a single piece of text output. It starts from real source material and carries that material through an end-to-end pipeline:

- ingestion
- section planning
- script writing
- QA and repair
- narration
- subtitles
- rendering
- storage
- retention-driven recommendation

That makes it stronger for this specific use case because it can:

- generate multiple shorts from one source instead of one summary
- spread coverage across different parts of the material
- reduce repetitive hooks and stale phrasing across a batch
- produce finished vertical videos instead of only script drafts
- keep outputs organized inside the product library

So the correct comparison is not "better than every AI writing tool in all cases." The correct claim is:

**For turning written source material into a library of finished short-form videos, this project is more complete and more productized than a generic prompt-only generator.**

## How The Website And Backend Work Together

Both sides of the repository now support the same product story.

The website supports:

- the public landing page
- login and guest entry
- the live generation chat flow
- shorts browsing
- profile and usage views
- the about page with product walkthrough videos

The backend supports:

- source ingestion
- planning and generation
- narration and rendering
- storage and playback
- auth-aware chat and library queries
- recommendation-system endpoints

For this project, the important point is simple: the frontend is no longer a demo shell. It is the actual product interface for the backend generation system.

## Why The Output Shape Matters

This repository does not just generate text. It generates a reusable product output shape:

- a chat record
- a batch record
- one or more rendered video items
- narration and subtitle metadata
- stored media URLs
- library-facing metadata for the frontend

That makes the output practical to view, replay, filter, and organize inside the app, instead of treating each generation as a disposable one-off response.

## Main Repository Components

### 1. Unified Backend

The primary backend lives in [`Backend/`](Backend/).

It contains the current production logic for:

- video generation
- recommendation and library APIs
- auth resolution
- storage and playback
- Supabase integration

This is the active backend and the one to treat as the main server.

It is also where the recommendation system lives. That service stores reel-level engagement, summarizes retention across a chat library, and generates follow-up guidance about which gameplay, captions, and hook styles are actually winning.

### 2. Website

[`website/`](website/) is the Next.js frontend for the project.

It now includes:

- the marketing site and product narrative
- login and guest mode entry
- backend-connected generation flows
- library and profile pages
- reels-style recommendation surfaces through the shorts experience
- the live deployed demo experience

### 3. Assets And Local Data

[`assets/`](assets/) and [`data/`](data/) hold the local media pieces and working directories used during rendering and development.

They are useful for:

- gameplay footage
- fonts and subtitle assets
- intermediate render outputs
- final local MP4s in development

## Generated Output Shape

The generated output is designed around the idea of a stored batch of finished shorts.

A typical local output flow looks like:

```text
data/
└── final-renders/
    └── some-batch/
        ├── short-1.mp4
        ├── short-2.mp4
        ├── short-3.mp4
        └── ...
```

In production, the same generation is represented through:

- chat records
- batch records
- rendered item records
- Supabase-hosted media URLs

Important notes:

- each batch can contain multiple videos
- the library experience depends on stored metadata, not only raw files
- authenticated users see their own generated items
- guest flows use the general library path

The reason this structure matters is that Draftr is built as a reusable content workflow, not as a one-off render script.

## Script Generation And Rendering Flow

The generation pipeline is:

1. Source input arrives from the website.
2. The backend ingests and normalizes the source.
3. CrewAI plans sections and slot coverage.
4. OpenAI writes one short script per slot.
5. Backend QA repairs weak or repetitive outputs.
6. ElevenLabs creates narration audio and timing data.
7. The subtitle renderer builds timed ASS tracks.
8. FFmpeg renders the final short-form videos.
9. Storage and library records are updated for playback in the app.

The main backend logic lives in:

- [`Backend/brainrot_backend/main.py`](Backend/brainrot_backend/main.py)
- [`Backend/brainrot_backend/container.py`](Backend/brainrot_backend/container.py)
- [`Backend/brainrot_backend/video_generator/`](Backend/brainrot_backend/video_generator/)
- [`Backend/brainrot_backend/recommendation_system/`](Backend/brainrot_backend/recommendation_system/)

## Repository Structure

```text
.
├── README.md
├── Backend/
│   ├── brainrot_backend/
│   ├── supabase/
│   ├── tests/
│   ├── testsprite_tests/
│   └── README.md
├── website/
│   ├── src/
│   ├── public/
│   ├── testsprite_tests/
│   └── README.md
├── testsprite/
│   ├── testsprite.md
│   └── testsprite-mcp-issues-report.md
├── assets/
└── data/
```

## Quick Start

### Backend

```bash
cd Backend
cp .env.example .env
uv sync
uv run uvicorn brainrot_backend.main:app --reload --port 8000
```

Then open:

- `http://127.0.0.1:8000/health`

### Website

```bash
cd website
cp .env.example .env.local
npm install
npm run dev
```

Then open:

- `http://127.0.0.1:3000`

## Which README To Read Next

If you want the active backend details, read:

- [`Backend/README.md`](Backend/README.md)

If you want the frontend app details, read:

- [`website/README.md`](website/README.md)

## Summary

This repository is best understood as a **source-to-short-form-video generation product**.

It turns written material into rendered vertical videos, supports both guest and authenticated library flows, and combines ingestion, planning, writing, narration, subtitles, rendering, storage, and testing into one end-to-end system.
