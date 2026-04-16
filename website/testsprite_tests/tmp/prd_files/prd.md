# Draftr — Product Requirements Document

## Product Overview

Draftr is a web application that converts any content (URLs, PDFs, raw text) into short-form "brainrot" style videos. Users paste a link or upload a file, and the backend AI pipeline (CrewAI + OpenAI + ElevenLabs + FFmpeg) automatically produces TikTok-style vertical video shorts with gameplay overlays, narration, and subtitles.

## User Personas

- **Guest User**: Tries the product without signing in. Generates into the shared general library. Can browse the general library of shorts.
- **Authenticated User**: Signs in with Google. Generates into their own personal library. Has a profile page with stats and history.

## Core Features

### 1. Authentication — Google OAuth + Guest Mode

**Goal**: Allow users to either sign in with Google (via Supabase) for a personal library, or skip login entirely for a shared guest experience.

**Acceptance Criteria**:
- The `/login` page shows a "Login with Google" button and a "Continue as guest" button.
- Clicking "Login with Google" initiates a Supabase Google OAuth flow.
- On successful OAuth callback (`/auth/callback`), the user is redirected to their intended destination.
- If OAuth fails, the user is redirected to `/login?auth=error` with a visible error message.
- Clicking "Continue as guest" sets guest mode in localStorage and redirects to the app.
- If the user is already authenticated, the login page shows their name and options to continue or open profile.
- The navbar shows the user's avatar and name when authenticated, and a "Login" link when not.
- Authenticated users can sign out from the profile page.

### 2. AI Chat — Video Generation

**Goal**: Users submit a URL or PDF, and the backend generates a batch of brainrot short videos.

**Acceptance Criteria**:
- The `/chat` page shows a centered prompt input with placeholder text.
- Users can type or paste a URL into the prompt box.
- Users can upload a PDF via the file attachment option.
- The batch count stepper (5–15 videos) is visible and functional.
- Submitting a prompt creates a chat session and a generation batch via the API.
- The assistant message shows live progress of the generation pipeline.
- If the backend is unavailable, an error message is displayed in the conversation.
- The guest library label is shown when not authenticated.
- An auth error banner is shown if the user arrived via a failed login redirect.

### 3. Shorts Library — Video Feed

**Goal**: Users browse generated short videos in a TikTok-style vertical feed, organized by chat session.

**Acceptance Criteria**:
- The `/shorts` page loads the list of chats in the left sidebar.
- Clicking a chat loads its short videos into the main feed.
- The feed shows one video at a time in a 9:16 card.
- Videos auto-play when active and pause when inactive.
- Users can scroll/swipe to navigate between shorts.
- Click on the video card toggles play/pause.
- The mute button toggles audio on/off.
- The like button toggles the liked state.
- The info button opens a metadata panel showing title, source, duration, style, etc.
- The open button opens the video in a new browser tab.
- If no shorts exist for a chat, an empty state with a link to chat is shown.
- The recommendation/insights sidebar can be toggled open/closed and resized.

### 4. User Profile

**Goal**: Authenticated users can see their account stats, recent chats, and manage their session.

**Acceptance Criteria**:
- The `/profile` page shows the user's avatar, name, email, and member-since date.
- Stats cards show: saved shorts count, generation runs, active chats, failed runs.
- Recent activity shows the last 4 chats with title, source, and exported count.
- A "Log out" button is visible and functional.
- A "Open your library" button links to `/shorts`.
- Guest users see an upsell message and a "Login" button.
- Guest users see a "Browse general library" link to `/shorts`.

### 5. Navigation — Navbar

**Goal**: Persistent navigation bar accessible across all pages.

**Acceptance Criteria**:
- The navbar shows the Draftr logo/wordmark.
- Navigation links to Chat, Shorts, and About are present.
- When authenticated, the user's avatar or initials and display name are shown.
- When not authenticated, a "Login" link is shown.
- Clicking the avatar links to `/profile`.

### 6. Home Page — Marketing

**Goal**: Landing page that communicates the product value and drives users to generate their first video.

**Acceptance Criteria**:
- The home page (`/`) shows a hero headline and description.
- A "Generate your first video" CTA button links to `/chat`.
- A "See how it works" button links to `/about`.
- Stats (avg generation time, speed vs reading, modes) are visible.
- Feature cards and comparison rows are visible.
- A phone mockup with a demo video is shown.

## Non-Functional Requirements

- **Performance**: Pages should load and become interactive within 3 seconds on localhost.
- **Responsive**: The UI must be usable on desktop viewport (1280px+).
- **Error Handling**: All API errors must be surfaced to the user with a readable message.
- **Accessibility**: Interactive buttons must have accessible labels.
- **Auth Persistence**: Auth state must persist across page refreshes via Supabase session cookies.
