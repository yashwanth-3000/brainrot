"""End-to-end verification of the CrewAI producer fix against the real Devpost source.

This uses the actual content from
https://ai-agentic-hackathon.devpost.com/ - the page that caused the
'primary fact cluster overlaps with another slot' repair loop in production.
"""
from __future__ import annotations

import sys

from brainrot_backend.config import Settings
from brainrot_backend.core.models.domain import SourceBrief
from brainrot_backend.video_generator.producer_crewai.flow import CrewAIProducerFlow
from brainrot_backend.video_generator.producer_crewai.models import CrewAIScriptPayload
from brainrot_backend.video_generator.producer_crewai.sectioning import build_coverage_plan

REAL_DEVPOST_MARKDOWN = """
Agentic AI Hackathon Powered by Microsoft - Shekunj Presents Agentic AI Hackathon Powered by Microsoft In Collaboration with JIT Borawan.

Deadline: Apr 20, 2026 at 12:00pm IST. 38 participants registered. Prize pool of 50,000 INR in cash plus goodies worth 1,00,000. Team size 2 to 4 members. Students only.

Agentic AI is the flagship 30-hour offline hackathon by Shekunj. This is not just about ideas - it is about building real, working products under pressure. Participants collaborate, innovate, and deliver solutions in a high-energy, continuous sprint.

Registration Deadline: 20th April 2026. PPT Submission Deadline: 20th April 2026, 11:59 PM. Grand Hackathon: 2nd to 3rd May 2026. Venue: JIT Borawan, Khargone.

Shortlisted teams will participate in a 30-hour offline build sprint at JIT Borawan. Teams will develop and present a fully working prototype of their AI Agentic solution. Mentorship support will be available throughout the hackathon to guide technical and product development.

Participants will have access to high-speed internet, power backup, and a dedicated workspace. Continuous evaluation and interaction with mentors and judges will take place during the event. Final product demonstrations and presentations will be conducted at the end of the hackathon.

Final Projects Will Be Evaluated On: Innovation and Originality (25%), Technical Execution (25%), Real-World Impact and Feasibility (20%), Problem-Solution Fit (15%), and Presentation and Demo (15%).

1st Place: 25,000 INR cash plus Trophy plus Certificate of Excellence plus Microsoft and Shekunj Goodies. 2nd Place: 15,000 INR cash plus Trophy. 3rd Place: 10,000 INR cash plus Trophy.

Challenge 1: Accessibility and Content Conversion Agent. Build an AI agent that converts content formats and assists users with disabilities in real time using GitHub Copilot to build vision and speech pipelines, generate assistive UI, integrate accessibility APIs, and optimize real-time systems.

Challenge 2: AI Study Companion for Competitive Exams. Build an intelligent learning agent that personalizes learning, generates tests, and adapts based on performance using GitHub Copilot to build quiz engines, generate evaluation logic, create adaptive learning systems, and develop tracking dashboards.

Challenge 3: Healthcare Assistant Agent. Build a multilingual AI system that performs symptom-based triage, suggests next steps, locates healthcare facilities, and maintains patient history using GitHub Copilot to generate chatbot workflows, build triage logic systems, integrate healthcare and maps APIs, and enable multilingual capabilities.

Challenge 4: Cyber Safety and Fraud Detection Agent. Build a system that identifies suspicious messages and provides preventive guidance using GitHub Copilot to build anomaly detection systems, generate classifiers, create browser and email safety tools, and develop alert systems.

Challenge 5: Mental Wellness Support Agent. Create an AI agent that detects emotional patterns and provides coping strategies with safe escalation support using GitHub Copilot to build conversational AI, generate sentiment models, create journaling systems, and develop escalation workflows.

Challenge 6: Smart Agriculture Advisory Agent. Create an AI system that provides crop recommendations, irrigation planning, pest detection insights, and market timing advice using GitHub Copilot to build data pipelines, generate prediction models, create dashboards, and integrate weather and market APIs.

Mandatory Requirements: Valid College ID, Government-issued Photo ID. Teams with female members will receive exciting extra benefits and a competitive edge. Buses will be available by organizer from Indore to JIT Borawan for participants.

Judge: Saurav Raghuvanshi, Digital Cloud Solution Architect at Microsoft.
"""


def _key(text: str) -> str:
    return " ".join(text.casefold().split()).strip().rstrip(".")


def main() -> int:
    plan = build_coverage_plan(
        title="Agentic AI Hackathon Powered by Microsoft",
        markdown=REAL_DEVPOST_MARKDOWN,
        requested_count=5,
    )

    print("=" * 70)
    print("PHASE 1  coverage plan built from real Devpost source")
    print("=" * 70)
    print(f"Sections extracted: {plan.section_count}")
    print(f"Slots planned:      {len(plan.slots)}")
    print(f"Fallback flags:     {plan.fallback_flags}")
    print()

    for slot in plan.slots:
        heading = slot.cluster.headings[0] if slot.cluster.headings else "(no heading)"
        print(f"  slot {slot.slot_index + 1}  angle={slot.angle_family:18s}  heading={heading[:55]!r}")
        anchor = slot.anchor_fact or "(empty)"
        print(f"            anchor = {anchor[:110]}")
        print(f"            forbidden anchors from prior slots: {len(slot.forbidden_overlap_facts)}")
    print()

    anchor_keys = [_key(slot.anchor_fact) for slot in plan.slots]
    angle_families = [slot.angle_family for slot in plan.slots]
    headings = [slot.cluster.headings[0] for slot in plan.slots if slot.cluster.headings]

    plan_checks = {
        "unique anchor facts": len(set(anchor_keys)) == len(anchor_keys),
        "unique angle families": len(set(angle_families)) == len(angle_families),
        "unique primary headings": len(set(headings)) == len(headings),
        "every slot has non-empty anchor": all(anchor_keys),
    }
    for label, passed in plan_checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")

    if not all(plan_checks.values()):
        print("\nplanner failed, aborting"); return 1

    print()
    print("=" * 70)
    print("PHASE 2  adversarial cross-slot coordinator check")
    print("=" * 70)
    print("Simulating the exact failure: every writer returns payloads that all")
    print("collide on the same 'primary fact' that used to trigger the loop.")
    print()

    settings = Settings()
    flow = CrewAIProducerFlow(settings=settings)

    source_brief = SourceBrief(
        canonical_title="Agentic AI Hackathon Powered by Microsoft",
        summary="A 30-hour offline hackathon by Shekunj with Microsoft and JIT Borawan.",
        facts=[fact for slot in plan.slots for fact in slot.cluster.facts][:10],
        entities=["Microsoft", "Shekunj", "JIT Borawan", "Azure"],
        tone="specific, fast, grounded",
        do_not_drift=["Keep each script tied to its assigned article section."],
        source_urls=["https://ai-agentic-hackathon.devpost.com"],
    )

    collision_fact = (
        plan.slots[0].cluster.facts[0]
        if plan.slots[0].cluster.facts
        else plan.slots[0].anchor_fact
    )

    payloads: dict[str, CrewAIScriptPayload] = {}
    for slot in plan.slots:
        payloads[slot.slot_id] = CrewAIScriptPayload(
            title="Agentic hackathon overview",
            hook="Build agentic apps with Microsoft",
            narration_text=(
                "Agentic apps need planning, tool use, and grounded retrieval. "
                + ("word " * 85)
            ),
            caption_text="agentic hackathon",
            visual_beats=["beat 1", "beat 2", "beat 3"],
            music_tags=["driving"],
            gameplay_tags=["systematic"],
            source_facts_used=[
                collision_fact,
                "Winners split a 50,000 INR prize pool",
            ],
            qa_notes=[],
        )

    flow._enforce_cross_slot_uniqueness(
        payloads=payloads,
        coverage_plan=plan,
        source_brief=source_brief,
    )

    resolved_primary = [
        _key(payloads[slot.slot_id].source_facts_used[0]) for slot in plan.slots
    ]
    resolved_titles = [payloads[slot.slot_id].title for slot in plan.slots]
    resolved_hooks = [payloads[slot.slot_id].hook for slot in plan.slots]

    for slot in plan.slots:
        p = payloads[slot.slot_id]
        print(f"  slot {slot.slot_index + 1} after coordinator:")
        print(f"    title  = {p.title[:80]}")
        print(f"    hook   = {p.hook[:80]}")
        print(f"    facts0 = {p.source_facts_used[0][:100]}")
    print()

    coordinator_checks = {
        "unique primary facts after coordinator": len(set(resolved_primary)) == len(resolved_primary),
        "unique titles after coordinator": len({t.casefold() for t in resolved_titles}) == len(resolved_titles),
        "unique hooks after coordinator": len({h.casefold() for h in resolved_hooks}) == len(resolved_hooks),
    }
    for label, passed in coordinator_checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")

    issues = flow._validate_slot_payloads(
        payloads=payloads,
        coverage_plan=plan,
        source_brief=source_brief,
    )
    overlap_problems = [
        f"slot {issue.slot_index + 1}: {problem}"
        for issue in issues
        for problem in issue.problems
        if "overlaps with another slot" in problem
    ]
    print()
    print(f"  overlap problems reported by validator: {len(overlap_problems)}")
    for op in overlap_problems:
        print(f"    - {op}")
    coordinator_checks["validator finds zero overlap problems"] = not overlap_problems
    print()
    print(f"  [{'PASS' if not overlap_problems else 'FAIL'}] validator finds zero overlap problems")

    all_passed = all(plan_checks.values()) and all(coordinator_checks.values())
    print()
    print("=" * 70)
    print(f"OVERALL: {'PASS - repair loop cannot trigger for this source' if all_passed else 'FAIL'}")
    print("=" * 70)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
