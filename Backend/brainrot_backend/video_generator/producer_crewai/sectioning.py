from __future__ import annotations

import math
import re
from collections import Counter

from brainrot_backend.video_generator.producer_crewai.models import (
    ArticleSection,
    CoveragePlan,
    CoverageSlotPlan,
    SectionCluster,
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
ENTITY_RE = re.compile(r"\b(?:[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+){0,3}|[A-Z]{2,}(?:\s+[A-Z]{2,})*)\b")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")

NOISE_LINE_HINTS = (
    "tap to unmute",
    "watch on",
    "subscribers",
    "youtube",
    "alt text",
    "claimcode=",
    "ibb.co/",
)
GENERIC_HEADING_HINTS = (
    "devpost",
    "overview",
    "project story",
    "built with",
    "updates",
    "what's next",
    "what’s next",
    "keep reading",
    "author",
    "about the author",
    "read more",
)
SECTION_PRIORITY_HINTS = {
    "how does": 2.8,
    "workflow": 2.6,
    "request lifecycle": 2.8,
    "architecture": 3.0,
    "components": 2.2,
    "thinking mode": 2.6,
    "use my voice": 2.8,
    "edit mode": 2.8,
    "x tab": 2.2,
    "instagram tab": 2.2,
    "linkedin tab": 2.2,
}

ANGLE_PROFILES = (
    {
        "id": "workflow",
        "semantic_objective": "workflow",
        "hook_direction": "process-first",
        "audience_frame": "builders",
        "visual_mood": "systematic",
        "music_mood": "driving",
    },
    {
        "id": "hidden-detail",
        "semantic_objective": "hidden detail",
        "hook_direction": "detail-first",
        "audience_frame": "curious viewers",
        "visual_mood": "focused",
        "music_mood": "tense",
    },
    {
        "id": "proof",
        "semantic_objective": "proof",
        "hook_direction": "evidence-first",
        "audience_frame": "skeptics",
        "visual_mood": "clean",
        "music_mood": "confident",
    },
    {
        "id": "risk",
        "semantic_objective": "risk",
        "hook_direction": "warning-first",
        "audience_frame": "operators",
        "visual_mood": "urgent",
        "music_mood": "dark",
    },
    {
        "id": "speed-win",
        "semantic_objective": "speed win",
        "hook_direction": "speed-first",
        "audience_frame": "busy creators",
        "visual_mood": "fast",
        "music_mood": "punchy",
    },
    {
        "id": "comparison",
        "semantic_objective": "comparison",
        "hook_direction": "contrast-first",
        "audience_frame": "evaluators",
        "visual_mood": "sharp",
        "music_mood": "steady",
    },
    {
        "id": "creator-takeaway",
        "semantic_objective": "creator takeaway",
        "hook_direction": "takeaway-first",
        "audience_frame": "creators",
        "visual_mood": "practical",
        "music_mood": "uplifting",
    },
    {
        "id": "architecture",
        "semantic_objective": "architecture",
        "hook_direction": "system-first",
        "audience_frame": "technical viewers",
        "visual_mood": "technical",
        "music_mood": "measured",
    },
    {
        "id": "implementation",
        "semantic_objective": "implementation",
        "hook_direction": "execution-first",
        "audience_frame": "makers",
        "visual_mood": "hands-on",
        "music_mood": "focused",
    },
    {
        "id": "use-case",
        "semantic_objective": "use case",
        "hook_direction": "scenario-first",
        "audience_frame": "end users",
        "visual_mood": "human",
        "music_mood": "warm",
    },
    {
        "id": "output-quality",
        "semantic_objective": "output quality",
        "hook_direction": "result-first",
        "audience_frame": "quality seekers",
        "visual_mood": "premium",
        "music_mood": "cinematic",
    },
    {
        "id": "failure-mode",
        "semantic_objective": "failure mode",
        "hook_direction": "failure-first",
        "audience_frame": "pragmatic viewers",
        "visual_mood": "cautionary",
        "music_mood": "tense",
    },
    {
        "id": "adoption-signal",
        "semantic_objective": "adoption signal",
        "hook_direction": "signal-first",
        "audience_frame": "trend watchers",
        "visual_mood": "social",
        "music_mood": "confident",
    },
    {
        "id": "differentiation",
        "semantic_objective": "differentiation",
        "hook_direction": "difference-first",
        "audience_frame": "buyers",
        "visual_mood": "bold",
        "music_mood": "decisive",
    },
    {
        "id": "retention-hook",
        "semantic_objective": "retention hook",
        "hook_direction": "payoff-first",
        "audience_frame": "short-form viewers",
        "visual_mood": "sticky",
        "music_mood": "high-energy",
    },
)


def build_coverage_plan(*, title: str, markdown: str, requested_count: int) -> CoveragePlan:
    normalized_requested = max(5, requested_count)
    sections = _extract_sections(title=title, markdown=_clean_markdown_for_sectioning(markdown))
    sections = _ensure_minimum_sections(sections, normalized_requested)
    sections = _finalize_sections(sections)
    clusters = _cluster_sections(sections, normalized_requested)

    planned_count = max(5, min(10, len(sections)))
    fallback_flags: list[str] = []
    if len(sections) < normalized_requested:
        fallback_flags.append("reused_sections")
    if len({cluster.section_ids[0] for cluster in clusters if cluster.section_ids}) < min(len(clusters), len(sections)):
        fallback_flags.append("cluster_reuse")

    slots: list[CoverageSlotPlan] = []
    used_facts: set[str] = set()
    used_angle_families: set[str] = set()
    all_section_ids = [section.section_id for section in sections]
    for index, cluster in enumerate(clusters):
        profile = _select_angle_profile(cluster=cluster, index=index, used_angle_families=used_angle_families)
        used_angle_families.add(profile["id"])
        cluster_facts = [fact for fact in cluster.facts if fact.casefold() not in used_facts]
        if cluster_facts:
            used_facts.add(cluster_facts[0].casefold())
        slots.append(
            CoverageSlotPlan(
                slot_index=index,
                slot_id=f"slot-{index + 1}",
                angle_family=profile["id"],
                semantic_objective=profile["semantic_objective"],
                hook_direction=profile["hook_direction"],
                audience_frame=profile["audience_frame"],
                visual_mood=profile["visual_mood"],
                music_mood=profile["music_mood"],
                cluster=cluster,
                forbidden_overlap_section_ids=[section_id for section_id in all_section_ids if section_id not in cluster.section_ids],
                forbidden_overlap_facts=[fact for fact in used_facts if fact not in {entry.casefold() for entry in cluster.facts}],
            )
        )

    return CoveragePlan(
        requested_count=requested_count,
        planned_count=planned_count,
        actual_count=len(slots),
        section_count=len(sections),
        sections=sections,
        slots=slots,
        fallback_flags=fallback_flags,
    )


def build_source_brief_metadata(plan: CoveragePlan) -> dict[str, object]:
    used_section_ids = [slot.cluster.section_ids[0] for slot in plan.slots if slot.cluster.section_ids]
    used_sections = {section_id for section_id in used_section_ids}
    unused_sections = [
        {"section_id": section.section_id, "heading": section.heading}
        for section in plan.sections
        if section.section_id not in used_sections
    ]
    return {
        "requested_count": plan.requested_count,
        "planned_count": plan.planned_count,
        "actual_count": plan.actual_count,
        "section_count": plan.section_count,
        "coverage_plan": [
            {
                "slot_id": slot.slot_id,
                "slot_index": slot.slot_index,
                "angle_family": slot.angle_family,
                "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                "section_ids": slot.cluster.section_ids,
            }
            for slot in plan.slots
        ],
        "used_sections": used_section_ids,
        "unused_sections": unused_sections,
        "fallback_flags": plan.fallback_flags,
    }


def _extract_sections(*, title: str, markdown: str) -> list[ArticleSection]:
    lines = markdown.splitlines()
    sections: list[ArticleSection] = []
    current_heading = title.strip() or "Overview"
    current_level = 1
    current_lines: list[str] = []
    body_start_line = 1
    position = 0

    def flush(end_line: int) -> None:
        nonlocal position, current_lines, body_start_line
        body = "\n".join(line.rstrip() for line in current_lines).strip()
        if not body:
            return
        position += 1
        sections.append(
            ArticleSection(
                section_id=f"section-{position}",
                heading=current_heading,
                heading_level=current_level,
                position=position,
                section_summary=_summarize_text(body),
                facts=_extract_facts(body),
                entities=_extract_entities(current_heading, body),
                source_span={"start_line": body_start_line, "end_line": max(body_start_line, end_line)},
                priority_score=_score_section(current_heading, current_level, body),
                raw_markdown=body,
            )
        )

    for line_number, raw_line in enumerate(lines, start=1):
        heading_match = HEADING_RE.match(raw_line.strip())
        if heading_match:
            flush(line_number - 1)
            current_level = len(heading_match.group(1))
            current_heading = heading_match.group(2).strip() or current_heading
            current_lines = []
            body_start_line = line_number + 1
            continue
        current_lines.append(raw_line)
    flush(len(lines))

    if not sections:
        sections.append(
            ArticleSection(
                section_id="section-1",
                heading=title.strip() or "Overview",
                heading_level=1,
                position=1,
                section_summary=_summarize_text(markdown),
                facts=_extract_facts(markdown),
                entities=_extract_entities(title, markdown),
                source_span={"start_line": 1, "end_line": len(lines) or 1},
                priority_score=_score_section(title, 1, markdown),
                raw_markdown=markdown.strip(),
            )
        )
    return sections


def _ensure_minimum_sections(sections: list[ArticleSection], target_count: int) -> list[ArticleSection]:
    expanded = list(sections)
    while len(expanded) < target_count:
        split_index = _find_best_split_candidate(expanded)
        if split_index is None:
            break
        target = expanded.pop(split_index)
        pieces = _split_section(target)
        expanded[split_index:split_index] = pieces
    return expanded


def _finalize_sections(sections: list[ArticleSection]) -> list[ArticleSection]:
    finalized: list[ArticleSection] = []
    for index, section in enumerate(sections, start=1):
        finalized.append(
            section.model_copy(
                update={
                    "section_id": f"section-{index}",
                    "position": index,
                }
            )
        )
    return finalized


def _cluster_sections(sections: list[ArticleSection], requested_count: int) -> list[SectionCluster]:
    if not sections:
        return []
    selected_sections = _select_sections_for_slots(sections, requested_count)
    clusters: list[SectionCluster] = []
    selected_ids = {section.section_id for section in selected_sections}
    for index, section in enumerate(selected_sections):
        chunk = [section]
        if _section_is_sparse(section):
            neighbor = _best_neighbor(section=section, sections=sections, selected_ids=selected_ids)
            if neighbor is not None:
                chunk.append(neighbor)
                chunk = sorted(chunk, key=lambda item: item.position)
        combined_markdown = "\n\n".join(f"## {section.heading}\n{section.raw_markdown}" for section in chunk)
        combined_facts = _unique_list(fact for section in chunk for fact in section.facts)
        combined_entities = _unique_list(entity for section in chunk for entity in section.entities)
        clusters.append(
            SectionCluster(
                cluster_id=f"cluster-{index + 1}",
                position=index + 1,
                section_ids=[section.section_id for section in chunk],
                headings=[section.heading for section in chunk],
                section_summary=_summarize_text(combined_markdown),
                facts=combined_facts[:8],
                entities=combined_entities[:10],
                source_span={
                    "start_line": chunk[0].source_span.get("start_line", 1),
                    "end_line": chunk[-1].source_span.get("end_line", chunk[0].source_span.get("end_line", 1)),
                },
                priority_score=round(sum(section.priority_score for section in chunk) / max(len(chunk), 1), 2),
                raw_markdown=combined_markdown.strip(),
            )
        )
    return clusters


def _select_sections_for_slots(sections: list[ArticleSection], requested_count: int) -> list[ArticleSection]:
    if len(sections) <= requested_count:
        return sections

    candidate_sections = sections
    non_boilerplate_sections = [section for section in sections if not _section_is_boilerplate(section)]
    if len(non_boilerplate_sections) >= requested_count:
        candidate_sections = non_boilerplate_sections

    total = len(candidate_sections)
    selected: list[ArticleSection] = []
    selected_ids: set[str] = set()

    for index in range(requested_count):
        start = round(index * total / requested_count)
        end = round((index + 1) * total / requested_count)
        window = candidate_sections[start:end] or [candidate_sections[min(start, total - 1)]]
        best = max(window, key=_section_pick_score)
        if best.section_id not in selected_ids:
            selected.append(best)
            selected_ids.add(best.section_id)

    if len(selected) < requested_count:
        for section in sorted(candidate_sections, key=_section_pick_score, reverse=True):
            if section.section_id in selected_ids:
                continue
            selected.append(section)
            selected_ids.add(section.section_id)
            if len(selected) == requested_count:
                break

    return sorted(selected[:requested_count], key=lambda section: section.position)


def _section_pick_score(section: ArticleSection) -> float:
    heading = section.heading.casefold()
    score = section.priority_score
    if any(hint in heading for hint in GENERIC_HEADING_HINTS):
        score -= 5.0
    if heading.startswith("what is "):
        score -= 1.8
    for hint, bonus in SECTION_PRIORITY_HINTS.items():
        if hint in heading:
            score += bonus
    token_count = len(TOKEN_RE.findall(section.raw_markdown))
    if token_count < 45:
        score -= 1.0
    return score


def _section_is_boilerplate(section: ArticleSection) -> bool:
    heading = section.heading.casefold()
    return any(hint in heading for hint in GENERIC_HEADING_HINTS)


def _section_is_sparse(section: ArticleSection) -> bool:
    return len(section.facts) < 2 or len(TOKEN_RE.findall(section.raw_markdown)) < 60


def _best_neighbor(
    *,
    section: ArticleSection,
    sections: list[ArticleSection],
    selected_ids: set[str],
) -> ArticleSection | None:
    candidates = [
        candidate
        for candidate in sections
        if candidate.section_id not in selected_ids and abs(candidate.position - section.position) == 1
    ]
    if not candidates:
        return None
    return max(candidates, key=_section_pick_score)


def _select_angle_profile(
    *,
    cluster: SectionCluster,
    index: int,
    used_angle_families: set[str],
) -> dict[str, str]:
    preferred = _preferred_angle_families(cluster)
    for angle_family in preferred:
        if angle_family in used_angle_families:
            continue
        profile = next((item for item in ANGLE_PROFILES if item["id"] == angle_family), None)
        if profile is not None:
            return profile
    for profile in ANGLE_PROFILES:
        if profile["id"] not in used_angle_families:
            return profile
    return ANGLE_PROFILES[index % len(ANGLE_PROFILES)]


def _preferred_angle_families(cluster: SectionCluster) -> list[str]:
    heading_blob = " ".join(cluster.headings).casefold()
    summary_blob = cluster.section_summary.casefold()
    combined = f"{heading_blob} {summary_blob}"
    if any(hint in combined for hint in ("architecture", "components", "backend", "sandbox", "models", "request lifecycle")):
        return ["architecture", "implementation", "workflow", "risk"]
    if any(hint in combined for hint in ("thinking mode", "use my voice", "personal writing style")):
        return ["differentiation", "proof", "output-quality", "creator-takeaway"]
    if any(hint in combined for hint in ("x tab", "instagram", "linkedin", "character limit", "preview")):
        return ["use-case", "workflow", "comparison", "hidden-detail"]
    if "edit mode" in combined or "delta" in combined:
        return ["speed-win", "workflow", "creator-takeaway", "output-quality"]
    if any(hint in combined for hint in ("how does", "workflow", "generate", "platform-ready")):
        return ["workflow", "speed-win", "use-case", "creator-takeaway"]
    if any(hint in combined for hint in ("risk", "fails", "safe", "secure")):
        return ["risk", "failure-mode", "architecture", "implementation"]
    return ["hidden-detail", "proof", "workflow", "comparison"]


def _find_best_split_candidate(sections: list[ArticleSection]) -> int | None:
    best_index: int | None = None
    best_score = -1
    for index, section in enumerate(sections):
        paragraphs = _paragraphs(section.raw_markdown)
        if len(paragraphs) < 2:
            continue
        score = len(section.raw_markdown)
        if score > best_score:
            best_score = score
            best_index = index
    return best_index


def _split_section(section: ArticleSection) -> list[ArticleSection]:
    paragraphs = _paragraphs(section.raw_markdown)
    if len(paragraphs) < 2:
        return [section]
    midpoint = math.ceil(len(paragraphs) / 2)
    chunks = [paragraphs[:midpoint], paragraphs[midpoint:]]
    split_sections: list[ArticleSection] = []
    start_line = section.source_span.get("start_line", 1)
    line_cursor = start_line
    for index, chunk in enumerate(chunks, start=1):
        body = "\n\n".join(chunk).strip()
        if not body:
            continue
        line_count = max(body.count("\n") + 1, 1)
        heading = section.heading if index == 1 else f"{section.heading}: detail {index}"
        split_sections.append(
            ArticleSection(
                section_id=f"{section.section_id}-{index}",
                heading=heading,
                heading_level=section.heading_level,
                position=section.position,
                section_summary=_summarize_text(body),
                facts=_extract_facts(body),
                entities=_extract_entities(heading, body),
                source_span={"start_line": line_cursor, "end_line": line_cursor + line_count - 1},
                priority_score=_score_section(heading, section.heading_level, body),
                raw_markdown=body,
            )
        )
        line_cursor += line_count
    return split_sections or [section]


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _summarize_text(text: str, *, sentence_count: int = 2) -> str:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return ""
    sentences = [sentence.strip() for sentence in SENTENCE_RE.split(cleaned) if sentence.strip()]
    return " ".join(sentences[:sentence_count]) if sentences else cleaned[:240]


def _extract_facts(text: str) -> list[str]:
    candidates: list[str] = []
    for paragraph in _paragraphs(text):
        line = " ".join(paragraph.split()).strip()
        if not line:
            continue
        if _line_is_noise(line):
            continue
        if line.startswith(("-", "*", "•")):
            candidates.append(line.lstrip("-*• ").rstrip("."))
            continue
        sentence = SENTENCE_RE.split(line)[0].strip()
        if len(sentence) < 18:
            continue
        if _line_is_noise(sentence):
            continue
        if any(char.isdigit() for char in sentence) or "'" in sentence or '"' in sentence or ":" in sentence:
            candidates.append(sentence.rstrip("."))
        elif len(candidates) < 6:
            candidates.append(sentence.rstrip("."))
    return _unique_list(candidates)[:6]


def _extract_entities(heading: str, text: str) -> list[str]:
    candidates = ENTITY_RE.findall(f"{heading}\n{text}")
    return _unique_list(candidate.strip() for candidate in candidates if len(candidate.strip()) > 1)[:10]


def _score_section(heading: str, heading_level: int, body: str) -> float:
    token_count = len(TOKEN_RE.findall(body))
    fact_bonus = min(len(_extract_facts(body)) * 1.4, 6.0)
    entity_bonus = min(len(_extract_entities(heading, body)) * 0.6, 3.0)
    heading_bonus = max(0.5, 3.5 - (heading_level * 0.35))
    density_bonus = min(token_count / 80.0, 4.0)
    return round(heading_bonus + fact_bonus + entity_bonus + density_bonus, 2)


def _unique_list(values) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(str(value).split()).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered


def dominant_terms(text: str, *, limit: int = 12) -> list[str]:
    counts = Counter(token.casefold() for token in TOKEN_RE.findall(text) if len(token) >= 4)
    return [token for token, _ in counts.most_common(limit)]


def _clean_markdown_for_sectioning(markdown: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = MARKDOWN_IMAGE_RE.sub("", raw_line)
        line = MARKDOWN_LINK_RE.sub(lambda match: match.group(1), line)
        normalized = " ".join(line.split()).strip()
        if not normalized:
            cleaned_lines.append("")
            continue
        if _line_is_noise(normalized):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _line_is_noise(text: str) -> bool:
    normalized = " ".join(text.split()).strip().casefold()
    if not normalized:
        return True
    if any(hint in normalized for hint in NOISE_LINE_HINTS):
        return True
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return True
    if normalized.startswith("[") and "](" in normalized:
        return True
    if normalized.count("/") >= 4 and len(TOKEN_RE.findall(normalized)) < 6:
        return True
    if normalized.startswith("![](") or normalized.startswith("![alt text]"):
        return True
    return False
