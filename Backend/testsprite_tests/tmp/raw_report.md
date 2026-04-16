
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** backend-full-test-1
- **Date:** 2026-04-14
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 get_health_endpoint
- **Test Code:** [TC001_get_health_endpoint.py](./TC001_get_health_endpoint.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/b682706e-9bd1-4568-8935-96be998f7225
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 post_v1_batches_create_batch
- **Test Code:** [TC002_post_v1_batches_create_batch.py](./TC002_post_v1_batches_create_batch.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/a3377c63-5dbd-4f73-9849-03927a2c737d
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 post_v1_batches_validation_errors
- **Test Code:** [TC003_post_v1_batches_validation_errors.py](./TC003_post_v1_batches_validation_errors.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/b00fa213-e965-46b2-b088-c4cffb46c234
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 get_v1_batches_uuid_validation_and_404
- **Test Code:** [TC004_get_v1_batches_uuid_validation_and_404.py](./TC004_get_v1_batches_uuid_validation_and_404.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/5792080c-3d79-4956-9600-ff4f80e0ffaa
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 get_v1_batches_sse_events
- **Test Code:** [TC005_get_v1_batches_sse_events.py](./TC005_get_v1_batches_sse_events.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/03f223af-8a5a-4415-9eee-1b3caf62455a
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006 post_v1_assets_upload
- **Test Code:** [TC006_post_v1_assets_upload.py](./TC006_post_v1_assets_upload.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/45858cef-f88d-4c7f-92fe-07ad97fc2c73
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007 post_v1_assets_upload_validation
- **Test Code:** [TC007_post_v1_assets_upload_validation.py](./TC007_post_v1_assets_upload_validation.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/10939a5d-dc2c-4281-895f-14e0186a4c96
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008 post_v1_agents_bootstrap
- **Test Code:** [TC008_post_v1_agents_bootstrap.py](./TC008_post_v1_agents_bootstrap.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/ed6da24c-c17b-41da-a569-a5454f7b0384
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC009 post_v1_agents_webhooks_elevenlabs_signature
- **Test Code:** [TC009_post_v1_agents_webhooks_elevenlabs_signature.py](./TC009_post_v1_agents_webhooks_elevenlabs_signature.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/c894ebbf-96c7-4561-af7c-232ec8d79e6c
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010 post_v1_chats_create_chat
- **Test Code:** [TC010_post_v1_chats_create_chat.py](./TC010_post_v1_chats_create_chat.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/694bc55f-51a8-46c8-9a1c-7e9b76686878
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC011 get_v1_chats_list_and_get_single
- **Test Code:** [TC011_get_v1_chats_list_and_get_single.py](./TC011_get_v1_chats_list_and_get_single.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 51, in <module>
  File "<string>", line 17, in test_get_v1_chats_list_and_get_single
AssertionError: POST /v1/chats failed with status 401

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/9eac5d04-3c32-457f-aaaa-e3412293a55c
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC012 get_v1_chats_chatid_errors
- **Test Code:** [TC012_get_v1_chats_chatid_errors.py](./TC012_get_v1_chats_chatid_errors.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/42e2186c-3f54-4178-bb64-f233c8b64e0b
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC013 post_v1_chats_engagement_and_recommendations
- **Test Code:** [TC013_post_v1_chats_engagement_and_recommendations.py](./TC013_post_v1_chats_engagement_and_recommendations.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 49, in <module>
  File "<string>", line 16, in test_post_v1_chats_engagement_and_recommendations
AssertionError: Response JSON missing or invalid 'chat_id' key

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/7ce3c1ea-ffaf-4d59-b415-0f0f4dd7405e
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC014 post_v1_chats_engagement_errors
- **Test Code:** [TC014_post_v1_chats_engagement_errors.py](./TC014_post_v1_chats_engagement_errors.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/c53b543a-4420-4800-8f57-6a5c291bdb8a
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC015 get_v1_video_edit_options
- **Test Code:** [TC015_get_v1_video_edit_options.py](./TC015_get_v1_video_edit_options.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/276dbd2f-e119-478c-98c3-d2b3f7087f03/d0603df0-ccc4-40f6-95b7-8ec610df315f
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **86.67** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---