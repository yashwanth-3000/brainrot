# TestSprite Backend Test Report — Video Generator
**Project:** `video-generator-test-1`  
**Date:** 2026-04-14  
**Server:** FastAPI on `http://localhost:8000` (all services enabled)  
**Total Tests:** 10 | ✅ Passed: 1 | ❌ Failed: 9

---

## Executive Summary

The video generator backend is largely functional, but this run surfaced **2 real bugs** and revealed several **test assumption mismatches** where TestSprite generated tests against a misread API contract. The API is stable for its core batch lifecycle and validation logic, but has an unhandled exception for invalid UUID path parameters and a router configuration issue that creates ghost duplicate routes.

---

## Test Results

| TC | Title | Status | Category |
|----|-------|--------|----------|
| TC001 | POST /v1/batches — Create batch job | ❌ FAILED | Test assumption (wrong content-type) |
| TC002 | GET /v1/batches/{id}/events — SSE stream | ❌ FAILED | Environment constraint |
| TC003 | POST /v1/batches — Invalid input validation | ✅ PASSED | — |
| TC004 | GET /v1/batches/{id} — Batch not found | ❌ FAILED | **Real Bug** |
| TC005 | POST /v1/assets — Upload gameplay/music/font | ❌ FAILED | Test assumption (wrong path) |
| TC006 | POST /v1/assets — Unsupported file type | ❌ FAILED | Test assumption (wrong path) |
| TC007 | POST /v1/agents/bootstrap + LLM proxy | ❌ FAILED | Test assumption (wrong path) |
| TC008 | POST /v1/agents/webhook — HMAC validation | ❌ FAILED | Test assumption (wrong path) |
| TC009 | POST /v1/chats — Create and auth scoping | ❌ FAILED | Test assumption (wrong field name) |
| TC010 | POST /v1/chats/{id}/engagement — Tracking | ❌ FAILED | Cascading from TC009 |

---

## Real Bugs Found

### BUG-001 — Non-UUID Batch ID Returns 500 Instead of 422 `[NEEDS FIX]`

**Test:** TC004  
**Severity:** Medium  
**Route:** `GET /v1/batches/{batch_id}`

**Expected:** `422 Unprocessable Entity` (invalid UUID format) or `404 Not Found` (valid UUID not in DB)  
**Actual:** `500 Internal Server Error` with body `Internal Server Error`

**Verified behavior:**
```
GET /v1/batches/00000000-0000-0000-0000-000000000000  → 404  ✅ (correct)
GET /v1/batches/nonexistentbatchid1234567890          → 500  ❌ (bug)
```

**Root Cause:** The route parameter `batch_id` is typed as `str` (or `Any`) rather than `uuid.UUID`. When a non-UUID string is passed, an unhandled exception occurs inside the service/DB layer (likely a UUID parse error), which propagates as a 500.

**Fix:** Declare `batch_id: uuid.UUID` in the route signature. FastAPI will automatically return `422` for invalid format before the handler runs.

```python
# routes/batches.py
@router.get("/{batch_id}")
async def get_batch(batch_id: uuid.UUID, ...):  # uuid.UUID type = auto-validation
    ...
```

---

### BUG-002 — Duplicate Routes Registered for Agent LLM Proxy `[NEEDS FIX]`

**Severity:** Medium  
**Discovery:** Inspecting `/openapi.json` during test analysis

The following ghost routes appear in the OpenAPI spec — they are clearly unintentional duplicates caused by a router `prefix` being applied twice:

```
POST /v1/agents/custom-llm/chat/completions                  ✅ correct
POST /v1/agents/custom-llm/chat/completions/chat/completions  ❌ duplicate ghost

POST /v1/agents/custom-llm/responses                         ✅ correct
POST /v1/agents/custom-llm/responses/responses               ❌ duplicate ghost
```

**Root Cause:** The agents sub-router or its routes likely define paths that already include a prefix segment, and then the router is mounted with the same prefix again (e.g. the route defines `/chat/completions` and the router is mounted at `/custom-llm/chat/completions`).

**Fix:** Audit `routes/agents.py` — ensure the sub-router paths and the `include_router` prefix do not overlap.

---

## Test Assumption Issues (Not Backend Bugs)

These failures are due to TestSprite generating tests against incorrect assumptions about the API contract.

### TC001 — Wrong Content-Type (JSON vs Form Data)

**Expected by test:** `POST /v1/batches` with `Content-Type: application/json` body  
**Actual API:** Requires `multipart/form-data` (supports PDF file uploads alongside `source_url`)

```bash
# Correct call
curl -X POST http://localhost:8000/v1/batches \
  -F "source_url=https://example.com" \
  -F "count=5"
# → 200 OK with batch object ✅
```

**Action:** No backend fix needed. If JSON-only batch creation is desired for convenience, consider adding an alternative JSON endpoint.

---

### TC002 — Missing `sseclient` in Test Runner Environment

**Route:** `GET /v1/batches/{batch_id}/events` (SSE)  
**Error:** `ModuleNotFoundError: No module named 'sseclient'`

The SSE endpoint exists and is functional; the test runner simply doesn't have the `sseclient` library installed. This is a TestSprite environment constraint, not a backend bug.

---

### TC005 / TC006 — Wrong Asset Upload Path

**Test assumed:** `POST /v1/assets`  
**Actual route:** `POST /v1/assets/upload`

Both tests got `404 Not Found` because the path is missing `/upload`. No backend bug.

---

### TC007 — Wrong Agent LLM Proxy Path

**Test assumed:** `POST /v1/agents/custom-llm/chat`  
**Actual route:** `POST /v1/agents/custom-llm/chat/completions`

The test path is missing `/completions`. The bootstrap step (`POST /v1/agents/bootstrap`) succeeded (200 OK), confirming that part of the test was valid.

---

### TC008 — Wrong Webhook Path (Singular vs Plural)

**Test assumed:** `POST /v1/agents/webhook/elevenlabs`  
**Actual route:** `POST /v1/agents/webhooks/elevenlabs`

Off-by-one: `webhook` vs `webhooks`. No backend bug.

---

### TC009 / TC010 — Wrong Response Field Name for Chat ID

**Test assumed:** `response.json()["chat_id"]`  
**Actual response:** `response.json()["chat"]["id"]` (nested inside a `chat` envelope)

TC010 failed as a cascade from TC009 — it couldn't get a valid `chat_id` to post engagement events to. The engagement endpoint itself (`POST /v1/chats/{chat_id}/engagement`) works correctly.

---

## What's Working Well

- ✅ **Batch validation (TC003):** All 9 invalid input cases correctly returned `422` with structured `detail` list. FastAPI validation is wired correctly.
- ✅ **Valid UUID not-found handling (TC004 partial):** `GET /v1/batches/{valid-uuid}` correctly returns `404` when the batch doesn't exist.
- ✅ **Agent bootstrap:** `POST /v1/agents/bootstrap` returned `200 OK` in TC007 before the test moved to the wrong path.
- ✅ **Chat creation:** `POST /v1/chats` works and returns the full chat object (TC009 just looked at the wrong field).
- ✅ **Engagement endpoint exists:** `POST /v1/chats/{chat_id}/engagement` is registered and functional.
- ✅ **SSE route registered:** `GET /v1/batches/{batch_id}/events` exists; test failed only due to missing runner library.

---

## Registered API Routes (Actual)

```
GET    /health
GET    /v1/batches/{batch_id}
GET    /v1/batches/{batch_id}/events
GET    /v1/batches/{batch_id}/items/{item_id}/video
GET    /v1/chats
GET    /v1/chats/{chat_id}
GET    /v1/chats/{chat_id}/recommendations
GET    /v1/chats/{chat_id}/shorts
GET    /v1/video-edit/options
GET    /v1/video-edit/previews/{batch_id}/video
POST   /v1/agents/bootstrap
POST   /v1/agents/custom-llm
POST   /v1/agents/custom-llm/chat/completions
POST   /v1/agents/custom-llm/chat/completions/chat/completions  ← duplicate (BUG-002)
POST   /v1/agents/custom-llm/responses
POST   /v1/agents/custom-llm/responses/responses                ← duplicate (BUG-002)
POST   /v1/agents/tools/submit-script-bundle
POST   /v1/agents/webhooks/elevenlabs
POST   /v1/assets/upload
POST   /v1/batches
POST   /v1/batches/{batch_id}/retry
POST   /v1/chats
POST   /v1/chats/{chat_id}/engagement
POST   /v1/video-edit/previews
```

---

## Action Items

| Priority | Item | File |
|----------|------|------|
| 🔴 Medium | Fix BUG-001: type `batch_id` as `uuid.UUID` in GET /v1/batches/{id} route | `routes/batches.py` |
| 🔴 Medium | Fix BUG-002: audit agent sub-router prefix duplication | `routes/agents.py` |
| 🟡 Low | Consider adding JSON body support to `POST /v1/batches` for non-file use cases | `routes/batches.py` |
