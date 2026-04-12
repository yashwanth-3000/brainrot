from __future__ import annotations

from brainrot_backend.video_generator.producer_crewai.models import CoverageSlotPlan


def writer_system_prompt() -> str:
    return (
        "You write one short-form vertical video script at a time. "
        "Stay tightly grounded in the provided article section cluster. "
        "Do not drift into other sections unless the prompt explicitly allows it. "
        "Write with specificity, not ad copy. Avoid rhetorical-question intros, avoid generic feature hype, "
        "and avoid making every script sound like a product intro. "
        "Do not use canned lead-ins like 'Start with this detail', 'Watch this part first', "
        "'The strongest signal', 'The fastest win here', or 'Creators should steal this first'. "
        "The first sentence must lead with a concrete workflow step, constraint, component, failure mode, or proof point "
        "from the assigned section, not with generic praise about the product. "
        "Return only the requested structured fields."
    )


def repair_system_prompt() -> str:
    return (
        "You repair one short-form vertical video script at a time. "
        "Your job is to keep the assigned section coverage, fix validation issues, and make the hook meaningfully "
        "distinct from other slots. Preserve factual grounding. Do not repair with canned lead-ins like "
        "'Start with this detail', 'Watch this part first', 'The strongest signal', or 'The fastest win here'. "
        "Return only the structured fields."
    )


def build_writer_task_prompt(*, slot: CoverageSlotPlan, source_title: str, canonical_summary: str, section_count: int) -> str:
    cluster = slot.cluster
    cluster_headings = ", ".join(cluster.headings)
    cluster_facts = "\n".join(f"- {fact}" for fact in cluster.facts[:8]) or "- No explicit facts extracted"
    forbidden_sections = ", ".join(slot.forbidden_overlap_section_ids[:8]) or "none"
    forbidden_facts = "\n".join(f"- {fact}" for fact in slot.forbidden_overlap_facts[:6]) or "- none"
    return (
        f"Source title: {source_title}\n"
        f"Global source summary: {canonical_summary}\n"
        f"Article section count: {section_count}\n\n"
        f"You are writing slot {slot.slot_index + 1}.\n"
        f"Assigned semantic angle family: {slot.angle_family}\n"
        f"Assigned semantic objective: {slot.semantic_objective}\n"
        f"Assigned audience frame: {slot.audience_frame}\n"
        f"Assigned hook direction: {slot.hook_direction}\n"
        f"Assigned visual mood: {slot.visual_mood}\n"
        f"Assigned music mood: {slot.music_mood}\n"
        f"Assigned section ids: {', '.join(cluster.section_ids)}\n"
        f"Assigned section headings: {cluster_headings}\n"
        f"Assigned section summary: {cluster.section_summary}\n\n"
        f"Facts to use from this section cluster:\n{cluster_facts}\n\n"
        f"Do not overlap with these other article sections unless absolutely necessary: {forbidden_sections}\n"
        f"Do not center the hook on these already-used fact patterns:\n{forbidden_facts}\n\n"
        f"Cluster source markdown:\n{cluster.raw_markdown}\n\n"
        "Hard requirements:\n"
        "- Return one script only.\n"
        "- Keep narration_text between 80 and 100 words.\n"
        "- Keep narration_text at least 500 characters.\n"
        "- Use at least two concrete facts from the assigned section cluster in source_facts_used.\n"
        "- The hook must be grounded in those same facts.\n"
        "- The opening sentence must not restate the title or the hook.\n"
        "- Avoid starting with the product name unless this slot absolutely requires it.\n"
        "- Cover this part of the article, not the whole product pitch.\n"
        "- Make the semantic angle feel distinct from other slots by leaning into the assigned objective.\n"
        "- The opening sentence must mention a concrete step, limit, component, or proof point from this section cluster.\n"
        "- Bad openings: 'Transform your workflow', 'Content Hub is a game-changing tool', 'This innovative add-on'.\n"
        "- Good openings: 'The X tab enforces a 280-character limit before it writes', "
        "'Thinking Mode pauses to reason before generation starts', "
        "'Edit Mode treats changes as deltas instead of full rewrites'.\n"
        "- Keep caption_text short and human.\n"
        "- visual_beats should describe 3 or 4 fast scene beats.\n"
        "- gameplay_tags and music_tags should stay broad and production-friendly.\n"
    )


def build_repair_task_prompt(
    *,
    slot: CoverageSlotPlan,
    source_title: str,
    canonical_summary: str,
    current_script_json: str,
    validation_feedback: str,
) -> str:
    cluster = slot.cluster
    return (
        f"Source title: {source_title}\n"
        f"Global source summary: {canonical_summary}\n"
        f"Repair slot: {slot.slot_index + 1}\n"
        f"Assigned semantic angle family: {slot.angle_family}\n"
        f"Assigned semantic objective: {slot.semantic_objective}\n"
        f"Assigned section headings: {', '.join(cluster.headings)}\n"
        f"Assigned section summary: {cluster.section_summary}\n"
        f"Assigned section facts:\n" + "\n".join(f"- {fact}" for fact in cluster.facts[:8]) + "\n\n"
        f"Current script JSON:\n{current_script_json}\n\n"
        f"Validation feedback:\n{validation_feedback}\n\n"
        "Rewrite only this slot so it stays anchored to the assigned section cluster, fixes the validation problems, "
        "and stays meaningfully different in semantic angle from the other slots. "
        "Do not fall back to generic product-marketing phrasing during repair. "
        "Return one repaired structured script only."
    )
