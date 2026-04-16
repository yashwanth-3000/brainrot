# TestSprite MCP — Issues Encountered During Testing

**Project:** Drafter (Frontend + Backend)  
**Date:** 2026-04-14  
**Test Suites Run:** 4 (Frontend deployed, Video Generator, Recommendation System, Full Backend)

This report retains all listed items as valid TestSprite/MCP issues or workflow limitations encountered during testing, including Issues 4, 5, 6, and 8.

---

## 1. Code Generation Ignores Explicit Response Shape Instructions

**Severity:** High — causes consistent test failures  
**Affected Runs:** Video Generator (TC009, TC010), Recommendation System (TC001, TC004), Full Backend (TC013)

TestSprite's code generator ignores explicit `additionalInstruction` about nested JSON response shapes. Despite instructions like:

> "The response is NESTED: `{"chat": {"id": "uuid"}}`. Use `response.json()['chat']['id']`. DO NOT use `response.json()['chat_id']` — THAT KEY DOES NOT EXIST."

TestSprite still generates:

```python
chat_id = response.json()["chat_id"]  # WRONG — key doesn't exist
```

**Evidence of inconsistency:** In the same run, some tests correctly generated `response.json()["chat"]["id"]` (TC003, TC006 in recommendation system) while others in the same batch used the wrong `response.json()["chat_id"]` (TC001, TC004). The instructions were identical for all tests.

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

## 6. Test Execution Produces Empty Code (Timeout/Silent Failure)

**Severity:** High — entire run wasted  
**Affected Run:** Recommendation System test-1 (first attempt, all 7 tests)

All 7 tests returned with `"code": ""` (empty string) and `"testError": "Test execution failed or timed out"`. The tests were created on the TestSprite platform but no code was ever generated. Timestamps show tests were marked failed within 200ms of creation — far too fast for actual code generation.

```json
{
  "code": "",
  "testStatus": "FAILED",
  "testError": "Test execution failed or timed out",
  "created": "2026-04-14T05:38:33.589Z",
  "modified": "2026-04-14T05:38:33.780Z"
}
```

The tunnel was established successfully and the probe passed. Credits were available (342 remaining). No error in `mcp.log` indicated a cause.

**Workaround:** Cleared `test_results.json`, `raw_report.md`, and `mcp.log` from `tmp/`, then re-ran. The second attempt worked normally and generated code for all 7 tests.

---

## 7. Tunnel Probe Returns 503 on First Attempt

**Severity:** Low — auto-recovers  
**Affected Runs:** Every single run

Every test execution shows this warning on the first tunnel probe:

```
[WARN] Tunnel probe attempt 1 failed: Tunnel returned 503: Tunnel client is not connected to the server — retrying in 3s...
```

The second probe always succeeds. This adds ~3 seconds of unnecessary delay to every run but does not cause failures.

---

## 8. No Way to Provide Exact Test Code

**Severity:** Medium

TestSprite generates test code from descriptions. There is no mechanism to provide exact test code to run. When the code generator makes mistakes (wrong paths, wrong field names, wrong content types), the only recourse is to make the description more explicit and re-run — consuming credits and time.

For the chat `response.json()["chat"]["id"]` issue, we ran 5 separate attempts across 3 test suites and the code generator still produced incorrect code ~40% of the time, despite identical and extremely explicit instructions.

---

## Generated Test Reports

| Report | Location | Result |
|--------|----------|--------|
| Frontend (Deployed) | `website/testsprite_tests/testsprite-mcp-test-report-deployed-2.md` | 21/24 passed (87.5%) |
| Video Generator (Run 1) | `Backend/brainrot_backend/video_generator/testsprite_tests/testsprite-mcp-test-report-video-generator-1.md` | 1/10 passed (10%) — pre-fix |
| Video Generator (Run 2) | `Backend/brainrot_backend/video_generator/testsprite_tests/testsprite-mcp-test-report-video-generator-2.md` | 8/10 passed (80%) — post-fix |
| Recommendation System | `Backend/brainrot_backend/recommendation_system/testsprite_tests/testsprite-mcp-test-report-recommendation-system-1.md` | 5/7 passed (71%) |
| Full Backend | `Backend/testsprite_tests/testsprite-mcp-test-report-full-backend-1.md` | 13/15 passed (86%) |

---

## Issues Summary

| Issue | Severity | Workaround Available | Credits Wasted |
|-------|----------|---------------------|----------------|
| Ignores nested response shape instructions | High | No reliable workaround | ~50+ |
| Uses unavailable libraries (sseclient) | Medium | Yes — explicit instruction | ~10 |
| Invents fake auth tokens | Medium | Likely — not re-tested | ~10 |
| Wrong API paths | High | Yes — exact paths in description | ~40 |
| Wrong content-type (JSON vs form-data) | High | Yes — explicit instruction | ~10 |
| Empty code / silent timeout | High | Retry after clearing tmp/ | ~7 |
| Tunnel 503 on first probe | Low | Auto-recovers | 0 |
| No exact test code mechanism | Medium | N/A | N/A |
