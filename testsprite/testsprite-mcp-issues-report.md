# TestSprite MCP — Issues Encountered During Testing

**Project:** Drafter (Frontend + Backend)  
**Date:** 2026-04-14  
**Test Suites Run:** 4 (Frontend deployed, Video Generator, Recommendation System, Full Backend)

This report summarizes the confirmed TestSprite and MCP issues encountered while testing Draftr across the frontend and backend suites. The goal is to clearly separate real product bugs from tooling-related failures so future runs are easier to interpret and less likely to waste time or credits.

Each issue listed below was observed during actual test execution and had a concrete effect on results, such as false failures, broken generated test code, or extra reruns. Where a workaround was found, it is included so the next round of testing can be more reliable.

---

## 1. Code Generation Ignores Explicit Response Shape Instructions

**Severity:** High — causes consistent test failures  
**Affected Runs:** Video Generator ([TC009](../Backend/brainrot_backend/video_generator/testsprite_tests/TC009_post_v1_chats_create_and_list.py), [TC010](../Backend/brainrot_backend/video_generator/testsprite_tests/TC010_post_v1_chats_chatid_engagement_tracking.py)), Recommendation System ([TC001](../Backend/brainrot_backend/recommendation_system/testsprite_tests/TC001_post_v1_chats_create_and_get_chat.py), [TC004](../Backend/brainrot_backend/recommendation_system/testsprite_tests/TC004_post_v1_chats_chatid_engagement_valid.py)), Full Backend ([TC013](../Backend/testsprite_tests/TC013_post_v1_chats_engagement_and_recommendations.py))

TestSprite's code generator ignores explicit `additionalInstruction` about nested JSON response shapes. Despite instructions like:

> "The response is NESTED: `{"chat": {"id": "uuid"}}`. Use `response.json()['chat']['id']`. DO NOT use `response.json()['chat_id']` — THAT KEY DOES NOT EXIST."

TestSprite still generates:

```python
chat_id = response.json()["chat_id"]  # WRONG — key doesn't exist
```

**Evidence of inconsistency:** In the same run, some tests correctly generated `response.json()["chat"]["id"]` ([TC003](../Backend/brainrot_backend/recommendation_system/testsprite_tests/TC003_get_v1_chats_chatid_shorts_empty.py), [TC006](../Backend/brainrot_backend/recommendation_system/testsprite_tests/TC006_get_v1_chats_chatid_recommendations_insufficient_data.py) in recommendation system) while others in the same batch used the wrong `response.json()["chat_id"]` ([TC001](../Backend/brainrot_backend/recommendation_system/testsprite_tests/TC001_post_v1_chats_create_and_get_chat.py), [TC004](../Backend/brainrot_backend/recommendation_system/testsprite_tests/TC004_post_v1_chats_chatid_engagement_valid.py)). The instructions were identical for all tests.

**Impact:** 5+ tests failed across 3 separate runs purely due to this. The backend API was verified correct in every case — the failing test's own error message printed the actual response showing `{"chat": {"id": "..."}}`.

**Workaround:** None found. Repeating the instruction in both the test plan description AND `additionalInstruction` did not resolve it. Re-running the same tests sometimes produced correct code, sometimes not.

---

## 2. Code Generation Uses Unavailable Libraries

**Severity:** Medium  
**Affected Run:** Video Generator test-1 (TC002)

TestSprite generated test code that imports `sseclient`:

```python
import sseclient
```

This library is not installed in TestSprite's remote Lambda test runner, causing:

```
ModuleNotFoundError: No module named 'sseclient'
```

**Workaround:** Explicitly state in `additionalInstruction`: "DO NOT import sseclient. Parse SSE manually with `response.iter_lines()`." This worked in subsequent runs — TC002 passed in video-generator-test-2 and full-backend-test-1.

---

## 3. Code Generation Invents Authentication Tokens

**Severity:** Medium  
**Affected Run:** Full Backend (TC011)

TestSprite generated code with a hardcoded fake Bearer token:

```python
BEARER_TOKEN = "Bearer testtoken123"
headers = {"Authorization": BEARER_TOKEN}
```

The test description did not request auth testing. The backend's Supabase auth service rejected this fake token with 401. The same chat creation without the auth header (TC010, same run) passed.

**Impact:** 1 test failure in the full backend run. The test code was otherwise correct (used proper nested `chat["id"]` extraction).

**Workaround:** Explicitly state "DO NOT add Authorization headers unless the test description specifically asks for auth testing." Not tested in a follow-up run.

---

## 4. Code Generation Uses Wrong API Paths

**Severity:** High — causes 404 failures  
**Affected Run:** Video Generator test-1 (TC005, TC006, TC007, TC008)

TestSprite generated incorrect API paths despite the OpenAPI spec and PRD being available:

| Test | Generated Path | Actual Path | Difference |
|------|---------------|-------------|------------|
| TC005, TC006 | `POST /v1/assets` | `POST /v1/assets/upload` | Missing `/upload` |
| TC007 | `POST /v1/agents/custom-llm/chat` | `POST /v1/agents/custom-llm/chat/completions` | Missing `/completions` |
| TC008 | `POST /v1/agents/webhook/elevenlabs` | `POST /v1/agents/webhooks/elevenlabs` | `webhook` → `webhooks` (singular vs plural) |

All 4 returned `404 Not Found` because the paths don't exist.

**Workaround:** Specify exact paths in both the test plan description AND `additionalInstruction`. This resolved all path issues in subsequent runs.

---

## 5. Code Generation Uses Wrong Content-Type

**Severity:** High  
**Affected Run:** Video Generator test-1 (TC001)

TestSprite generated a JSON POST for an endpoint that requires `multipart/form-data`:

```python
# Generated (wrong)
requests.post(url, headers={"Content-Type": "application/json"}, json=payload)

# Correct
requests.post(url, data={"source_url": "...", "count": "5"})
```

The endpoint uses FastAPI `Form(...)` parameters, not a JSON body. Sending JSON caused all form fields to be missing → 422.

**Workaround:** Explicitly state "Uses multipart/form-data (NOT JSON). Use `requests.post(url, data={...})`" in the test description. Resolved in subsequent runs.

---

## Issues Summary

| Issue | Severity | Workaround Available | Credits Wasted |
|-------|----------|---------------------|----------------|
| Ignores nested response shape instructions | High | No reliable workaround | ~50+ |
| Uses unavailable libraries (sseclient) | Medium | Yes — explicit instruction | ~10 |
| Invents fake auth tokens | Medium | Likely — not re-tested | ~10 |
| Wrong API paths | High | Yes — exact paths in description | ~40 |
| Wrong content-type (JSON vs form-data) | High | Yes — explicit instruction | ~10 |
