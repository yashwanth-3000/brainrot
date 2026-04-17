# TestSprite Testing for Draftr

This file is the consolidated testing record for how TestSprite was used to harden Draftr across the website, recommendation system, video generator, and full backend. The goal was never just to chase a pass rate. The goal was to use repeated TestSprite runs to expose real product bugs, verify fixes, separate infrastructure constraints from application bugs, and build confidence that the final app worked across both local and deployed environments.

The short version is this: across the 11 recorded dashboard runs, we executed 144 named TestSprite tests. That testing loop directly improved guest mode, Google auth and logout, personal-library scoping, shorts loading, sidebar stability, UUID validation, asset upload correctness, SSE behavior, recommendation coverage, and the final production-readiness of Draftr.

## What Lives In This Folder

- [`testsprite.md`](./testsprite.md) — this consolidated write-up
- [`testsprite-mcp-issues-report.md`](./testsprite-mcp-issues-report.md) — the separate issues report focused on TestSprite generator and tunnel limitations

## Where The Main Test Artifacts Live

The raw TestSprite suites and reports are still stored with the parts of the product they tested:

- [`website/testsprite_tests/`](../website/testsprite_tests/)
- [`Backend/brainrot_backend/recommendation_system/testsprite_tests/`](../Backend/brainrot_backend/recommendation_system/testsprite_tests/)
- [`Backend/brainrot_backend/video_generator/testsprite_tests/`](../Backend/brainrot_backend/video_generator/testsprite_tests/)
- [`Backend/testsprite_tests/`](../Backend/testsprite_tests/)

Other supporting project-level files:

- [`testsprite/testsprite-mcp-issues-report.md`](./testsprite-mcp-issues-report.md) — the consolidated limitations/issues report

## Testing Coverage At A Glance

### Documented run progression

| Area | Run | Result | What it told us |
|---|---|---:|---|
| Website local | Run 1 | 6/15 | The product idea worked, but navigation, guest flow, library loading, and auth state were still fragile |
| Website local | Run 2 | 8/15 | The app was improving, but the edge cases around profile access, direct library browsing, and playback were still real |
| Website local | Run 3 | 11/15 | Strong final local gate before deployed testing; core navigation, guest browse, feed movement, open-in-new-tab, and logout improved |
| Website deployed | Run 1 | 20/24 | The first deployed pass showed the product was already much stronger in production than in local dev |
| Website deployed | Run 2 | 21/24 | Guest flow, auth/logout, profile, homepage, prompt guardrails, and stepper boundaries passed in production |
| Recommendation system | Attempt 1 | effectively 0/7 | First run was left in a bad state and produced empty code / timeout-like failure |
| Recommendation system | Verified run | 5/7 | Endpoints were working; remaining failures were generator mistakes around nested `chat.id` extraction |
| Video generator | Run 1 | 1/10 | Surfaced a real UUID validation bug and multiple contract misunderstandings in generated tests |
| Video generator | Run 2 | 8/10 | After fixes and clearer contract guidance, most of the suite passed |
| Video generator | Partial retry | 0/2 | A failed short rerun confirmed the generator/test-state issues were still not fully settled yet |
| Full backend | Final suite | 13/15 | Health, batches, assets, agents, chats, engagement, recommendations, and video-edit were verified together |

## What We Improved Because Of TestSprite

### Frontend and user-flow improvements

TestSprite helped improve the parts of the app that are easiest to miss when the product mostly works during manual demos:

- guest browsing of the general library
- login-page-to-guest transition
- logout returning the UI to guest state
- shorts sidebar loading and selection behavior
- feed navigation between shorts
- opening a short in a new tab
- profile page identity and stats coverage
- homepage-to-chat and homepage-to-login CTAs
- prompt guardrails and video-count boundaries in production

The most visible frontend progression was the website local journey from `6/15` to `8/15` to `11/15`, followed by deployed runs of `20/24` and then `21/24`.

### Backend and contract improvements

TestSprite was especially useful on the backend because it pushed us below the surface level of "the API seems okay" and into route-level correctness:

- invalid UUID path params were fixed to return `422` instead of `500`
- batch creation expectations were clarified around multipart form data
- SSE testing moved away from `sseclient` assumptions and toward manual stream parsing
- asset upload paths and required fields were validated more carefully
- webhook path and signature behavior were verified
- chat creation, engagement, and recommendation routes were checked against real request/response shapes
- full-backend testing confirmed that health, batches, assets, agents, chats, recommendations, and video-edit could all coexist correctly

The strongest backend progression was the video generator moving from `1/10` to `8/10`, then the full backend finishing at `13/15`.

### Recommendation-system improvements

TestSprite also validated that the recommendation-system side of Draftr was not just a UI idea. The suite verified:

- chat creation and retrieval
- chat listing
- UUID validation for chat routes
- empty shorts responses for new chats
- engagement error handling
- recommendation responses when there is not enough data yet
- correct `404` handling for missing chats

Even the failing recommendation tests were useful, because they showed that the real weakness was not the backend route behavior. The weakness was the generated test code incorrectly using `response.json()["chat_id"]` instead of the actual nested response shape `response.json()["chat"]["id"]`.

## What TestSprite Caught That Was Truly Wrong In The Product

These were real product or backend issues, not just testing artifacts:

- invalid non-UUID batch/chat/item IDs returning `500` instead of `422`
- guest-flow regressions when continuing from `/login` into the general library
- intermittent shorts sidebar loading problems in local runs
- a like button state change that did not give strong enough visual feedback
- some navigation and discoverability gaps around profile access and guest state transitions

## What Looked Broken But Was Not Actually A Product Bug

TestSprite also helped us avoid wasting time on the wrong fixes.

### Tunnel and infrastructure constraints

- MP4 playback through the tunnel proxy could leave videos stuck loading even when the live product worked
- the first tunnel probe often returned a temporary `503` before automatically succeeding on retry

### Generator-code limitations

- nested chat envelopes were sometimes flattened into a fake `chat_id` top-level lookup
- unavailable libraries like `sseclient` were imported in generated code
- wrong API paths were generated for assets and agent routes
- JSON content type was used for endpoints that actually require form-data
- fake auth headers were injected into tests that were not meant to be auth tests
- a bad local config state once produced an effectively broken `0/7` recommendation run with empty generated code

That distinction mattered a lot. TestSprite was valuable not only because it found bugs, but because it also told us which failures were ours to fix and which ones belonged to the testing environment or code generator.

## What TestSprite Did Especially Well For This Project

TestSprite was strong for Draftr in four specific ways:

1. It gave us a consistent way to test real user journeys instead of only isolated functions.
2. It exposed API contract problems and assumption mismatches very quickly.
3. It made rerun-driven improvement obvious by giving us concrete pass-rate movement after fixes.
4. It gave us confidence to move from local validation to deployed validation without relying only on intuition.

For a hackathon-style product that was still evolving fast, that mattered a lot. It turned testing into a feedback loop instead of a final checkbox.

## Honest Limitations We Ran Into With TestSprite

TestSprite helped the product a lot, but it was not frictionless.

The biggest repeated limitation was generated code inconsistency around nested response shapes like `chat.id`. Even with explicit instructions, some tests still generated `response.json()["chat_id"]` and failed for the wrong reason. The second major limitation was media testing through the tunnel for MP4-heavy flows. And the third was the lack of a way to provide exact test code when the intended assertion was already known.

That is why we kept a separate issues report alongside this file. The product clearly improved because of TestSprite, but the testing process also surfaced areas where the TestSprite workflow itself can become more reliable for advanced teams.

## File-By-File Suite Map

### Website

- Main suite folder: [`website/testsprite_tests/`](../website/testsprite_tests/)
- Key reports:
  - [`testsprite-mcp-test-report-3.md`](../website/testsprite_tests/testsprite-mcp-test-report-3.md) — local website run 3 (`11/15`)
  - [`testsprite-mcp-test-report-deployed-2.md`](../website/testsprite_tests/testsprite-mcp-test-report-deployed-2.md) — deployed website run (`21/24`)
- Note: the earlier local `6/15` and `8/15` runs are preserved in the project summary and hackathon script, even though only the later local report is stored as a standalone markdown report in the repo

### Recommendation system

- Suite folder: [`Backend/brainrot_backend/recommendation_system/testsprite_tests/`](../Backend/brainrot_backend/recommendation_system/testsprite_tests/)
- Key report:
  - [`testsprite-mcp-test-report-recommendation-system-1.md`](../Backend/brainrot_backend/recommendation_system/testsprite_tests/testsprite-mcp-test-report-recommendation-system-1.md) — verified recommendation run (`5/7`)
- Supporting evidence for the broken first attempt lives in:
  - [`testsprite/testsprite-mcp-issues-report.md`](./testsprite-mcp-issues-report.md)

### Video generator

- Suite folder: [`Backend/brainrot_backend/video_generator/testsprite_tests/`](../Backend/brainrot_backend/video_generator/testsprite_tests/)
- Key reports:
  - [`testsprite-mcp-test-report-video-generator-1.md`](../Backend/brainrot_backend/video_generator/testsprite_tests/testsprite-mcp-test-report-video-generator-1.md) — first run (`1/10`)
  - [`testsprite-mcp-test-report-video-generator-2.md`](../Backend/brainrot_backend/video_generator/testsprite_tests/testsprite-mcp-test-report-video-generator-2.md) — post-fix run (`8/10`)

### Full backend

- Suite folder: [`Backend/testsprite_tests/`](../Backend/testsprite_tests/)
- Key report:
  - [`testsprite-mcp-test-report-full-backend-1.md`](../Backend/testsprite_tests/testsprite-mcp-test-report-full-backend-1.md) — consolidated backend run (`13/15`)

## Final Takeaway

TestSprite did not just help us prove that Draftr worked. It helped us make Draftr work better.

It forced the product through repeated website, recommendation, video-generator, and backend checks; it revealed genuine bugs; it highlighted contract mismatches; it pushed us to retest after fixes; and it gave us a much clearer boundary between product issues and testing-environment issues. That is why TestSprite ended up being part of the build process, not just something we ran after the app already looked finished.
