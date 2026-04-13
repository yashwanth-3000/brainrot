from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from brainrot_backend.auth import RequestAuthContext
from brainrot_backend.core.models.api import (
    ChatEnvelope,
    ChatGeneratedAsset,
    ChatGeneratedAssetsResponse,
    ChatListResponse,
    ChatRecommendationResponse,
    RecommendationInsight,
    ReelRetentionSummary,
    ShortEngagementEnvelope,
    ShortEngagementRequest,
)
from brainrot_backend.core.models.domain import BatchRecord, ChatRecord, ScriptDraft, ShortEngagementRecord
from brainrot_backend.core.models.enums import BatchItemStatus, ChatLibraryScope
from brainrot_backend.core.storage.base import Repository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatService:
    MIN_REELS_FOR_RECOMMENDATION = 3

    def __init__(self, *, repository: Repository) -> None:
        self.repository = repository

    async def create_chat(
        self,
        *,
        auth: RequestAuthContext,
        title: str | None = None,
        source_label: str | None = None,
        source_url: str | None = None,
    ) -> ChatEnvelope:
        resolved_title = self._resolve_chat_title(
            title=title,
            source_label=source_label,
            source_url=source_url,
            fallback="Untitled chat",
        )
        chat = ChatRecord(
            title=resolved_title,
            library_scope=auth.library_scope,
            owner_user_id=auth.user_id,
            last_source_label=source_label,
            last_source_url=source_url,
        )
        chat = await self.repository.create_chat(chat)
        return ChatEnvelope(chat=chat)

    async def ensure_chat(
        self,
        chat_id: str,
        *,
        auth: RequestAuthContext,
        title: str | None = None,
        source_label: str | None = None,
        source_url: str | None = None,
        last_status: str | None = None,
    ) -> ChatRecord:
        existing = await self.repository.get_chat(chat_id)
        resolved_title = self._resolve_chat_title(
            title=title,
            source_label=source_label,
            source_url=source_url,
            fallback=existing.title if existing else "Untitled chat",
        )
        now = utc_now()
        if existing is None:
            return await self.repository.create_chat(
                ChatRecord(
                    id=chat_id,
                    title=resolved_title,
                    library_scope=auth.library_scope,
                    owner_user_id=auth.user_id,
                    updated_at=now,
                    last_source_label=source_label,
                    last_source_url=source_url,
                    last_status=last_status,
                )
            )

        self._assert_chat_access(existing, auth)
        changes: dict[str, object] = {"updated_at": now}
        if resolved_title and resolved_title != existing.title:
            changes["title"] = resolved_title
        if source_label is not None:
            changes["last_source_label"] = source_label
        if source_url is not None:
            changes["last_source_url"] = source_url
        if last_status is not None:
            changes["last_status"] = last_status
        return await self.repository.update_chat(chat_id, **changes)

    async def list_chats(self, auth: RequestAuthContext) -> ChatListResponse:
        chats = (
            await self.repository.list_chats(owner_user_id=auth.user_id)
            if auth.is_authenticated
            else await self.repository.list_chats(library_scope=ChatLibraryScope.GENERAL)
        )
        public_chats = [chat for chat in chats if chat.total_exported > 0]
        return ChatListResponse(items=public_chats)

    async def get_chat(self, chat_id: str, auth: RequestAuthContext) -> ChatEnvelope:
        chat = await self.get_accessible_chat(chat_id, auth)
        return ChatEnvelope(chat=chat)

    async def get_accessible_chat(self, chat_id: str, auth: RequestAuthContext) -> ChatRecord:
        chat = await self.repository.get_chat(chat_id)
        if chat is None:
            raise KeyError(chat_id)
        self._assert_chat_access(chat, auth)
        return chat

    async def record_short_engagement(
        self,
        chat_id: str,
        payload: ShortEngagementRequest,
        auth: RequestAuthContext,
    ) -> ShortEngagementEnvelope:
        await self.get_accessible_chat(chat_id, auth)

        item = await self.repository.get_batch_item(payload.item_id)
        if item is None:
            raise KeyError(payload.item_id)

        batch = await self.repository.get_batch(item.batch_id)
        if batch is None or batch.chat_id != chat_id:
            raise KeyError(chat_id)

        engagement = ShortEngagementRecord(
            chat_id=chat_id,
            batch_id=batch.id,
            item_id=item.id,
            viewer_id=payload.viewer_id.strip(),
            session_id=payload.session_id.strip(),
            watch_time_seconds=max(0.0, float(payload.watch_time_seconds)),
            completion_ratio=self._clamp(float(payload.completion_ratio), 0.0, 2.0),
            max_progress_seconds=max(0.0, float(payload.max_progress_seconds)),
            replay_count=max(0, int(payload.replay_count)),
            unmuted=bool(payload.unmuted),
            info_opened=bool(payload.info_opened),
            open_clicked=bool(payload.open_clicked),
            liked=bool(payload.liked),
            skipped_early=bool(payload.skipped_early),
            metadata=dict(payload.metadata),
            updated_at=utc_now(),
        )
        saved = await self.repository.upsert_short_engagement(engagement)
        return ShortEngagementEnvelope(engagement=saved)

    async def get_chat_recommendation(
        self,
        chat_id: str,
        *,
        auth: RequestAuthContext,
        session_id: str | None = None,
    ) -> ChatRecommendationResponse:
        chat = await self.get_accessible_chat(chat_id, auth)

        generated_assets = await self.list_chat_generated_assets(chat_id, auth)
        assets_by_item_id = {asset.item_id: asset for asset in generated_assets.items}
        asset_positions = {asset.item_id: index + 1 for index, asset in enumerate(generated_assets.items)}
        engagements = [
            engagement
            for engagement in await self.repository.list_short_engagements(chat_id)
            if engagement.item_id in assets_by_item_id
        ]
        if session_id:
            engagements = [
                engagement
                for engagement in engagements
                if self._matches_session_scope(engagement, session_id)
            ]

        if not engagements:
            return ChatRecommendationResponse(
                chat_id=chat_id,
                chat=chat,
                session_id=session_id,
                has_enough_data=False,
                min_reels_required=self.MIN_REELS_FOR_RECOMMENDATION,
                reels_tracked=0,
                total_sessions=0,
                total_watch_time_seconds=0.0,
                unique_viewers=0,
                high_retention_sessions=0,
                recommendation_title="Watch at least 3 reels in this session",
                recommendation_body=(
                    "Draftr starts recommending gameplay, captions, and text styles after this viewing "
                    "session has retention data from at least 3 reels."
                ),
                generation_prompt=None,
            )

        unique_viewers: set[str] = set()
        grouped_by_item_id: dict[str, list[ShortEngagementRecord]] = defaultdict(list)
        for engagement in engagements:
            grouped_by_item_id[engagement.item_id].append(engagement)

        aggregated_engagements: list[ShortEngagementRecord] = []
        retention_summary: list[ReelRetentionSummary] = []
        for item_id, item_engagements in grouped_by_item_id.items():
            asset = assets_by_item_id[item_id]
            unique_viewers.update({engagement.viewer_id for engagement in item_engagements if engagement.viewer_id})

            watch_time_seconds = round(
                sum(max(0.0, engagement.watch_time_seconds) for engagement in item_engagements),
                3,
            )
            max_progress_seconds = round(
                max(max(0.0, engagement.max_progress_seconds) for engagement in item_engagements),
                3,
            )
            completion_ratio = round(
                max(self._clamp(engagement.completion_ratio, 0.0, 2.0) for engagement in item_engagements),
                4,
            )
            replay_count = sum(max(0, int(engagement.replay_count)) for engagement in item_engagements)
            aggregated_skipped_early = (
                all(engagement.skipped_early for engagement in item_engagements)
                and completion_ratio < 0.2
            )

            sample = item_engagements[-1]
            aggregated = ShortEngagementRecord(
                id=sample.id,
                chat_id=chat_id,
                batch_id=sample.batch_id,
                item_id=item_id,
                viewer_id=sample.viewer_id,
                session_id=session_id or sample.session_id,
                watch_time_seconds=watch_time_seconds,
                completion_ratio=completion_ratio,
                max_progress_seconds=max_progress_seconds,
                replay_count=replay_count,
                unmuted=any(engagement.unmuted for engagement in item_engagements),
                info_opened=any(engagement.info_opened for engagement in item_engagements),
                open_clicked=any(engagement.open_clicked for engagement in item_engagements),
                liked=any(engagement.liked for engagement in item_engagements),
                skipped_early=aggregated_skipped_early,
                metadata=dict(sample.metadata),
                created_at=min(engagement.created_at for engagement in item_engagements),
                updated_at=max(engagement.updated_at for engagement in item_engagements),
            )
            aggregated_engagements.append(aggregated)
            retention_summary.append(
                ReelRetentionSummary(
                    reel_number=asset_positions.get(item_id, len(retention_summary) + 1),
                    item_id=item_id,
                    title=asset.script.title if asset.script is not None else f"Video {asset.item_index + 1}",
                    watch_time_seconds=watch_time_seconds,
                    max_progress_seconds=max_progress_seconds,
                    completion_ratio=completion_ratio,
                    estimated_seconds=(
                        asset.script.estimated_seconds
                        if asset.script is not None and asset.script.estimated_seconds is not None
                        else None
                    ),
                    replay_count=replay_count,
                    subtitle_style=str(asset.render_metadata.get("subtitle_style_label") or "") or None,
                    subtitle_font=str(asset.render_metadata.get("subtitle_font_name") or "") or None,
                    gameplay_label=self._gameplay_label(asset.render_metadata.get("gameplay_asset_path")),
                )
            )

        retention_summary.sort(key=lambda summary: summary.reel_number)

        scored_sessions: list[tuple[ShortEngagementRecord, ChatGeneratedAsset, float]] = []
        high_retention_sessions = 0
        for engagement in aggregated_engagements:
            asset = assets_by_item_id[engagement.item_id]
            score = self._score_engagement(engagement, asset)
            scored_sessions.append((engagement, asset, score))
            if engagement.completion_ratio >= 0.75:
                high_retention_sessions += 1

        gameplay_insights = self._build_dimension_insights(
            scored_sessions,
            key_builder=lambda _, asset: self._gameplay_family(asset.render_metadata.get("gameplay_asset_path")),
            label_builder=lambda _, asset: self._gameplay_label(asset.render_metadata.get("gameplay_asset_path")),
        )
        caption_insights = self._build_dimension_insights(
            scored_sessions,
            key_builder=lambda _, asset: self._caption_key(asset),
            label_builder=lambda _, asset: self._caption_label(asset),
        )
        text_style_insights = self._build_dimension_insights(
            scored_sessions,
            key_builder=lambda _, asset: self._text_style_key(asset.script),
            label_builder=lambda _, asset: self._text_style_label(asset.script),
        )

        winning_gameplay = gameplay_insights[0] if gameplay_insights else None
        winning_caption = caption_insights[0] if caption_insights else None
        winning_text_style = text_style_insights[0] if text_style_insights else None
        reels_tracked = len(aggregated_engagements)
        has_enough_data = reels_tracked >= self.MIN_REELS_FOR_RECOMMENDATION
        total_watch_time_seconds = round(sum(engagement.watch_time_seconds for engagement in aggregated_engagements), 3)

        recommendation_title = None
        recommendation_body = None
        generation_prompt = None
        if has_enough_data and winning_gameplay and winning_caption and winning_text_style:
            recommendation_title = f"Retention is strongest on {winning_gameplay.label} + {winning_caption.label}"
            recommendation_body = (
                f"In this chat library, viewers are staying longer on {winning_gameplay.label} gameplay, "
                f"{winning_caption.label} captions, and {winning_text_style.label} hooks. "
                "That combination is producing the healthiest watch-through and follow-up actions."
            )
            generation_prompt = (
                f"Create 5 more vertical shorts for this same chat. Lean into {winning_gameplay.label} gameplay, "
                f"{winning_caption.label} captions, and {winning_text_style.label} hooks. "
                "Stay aligned with the source topic cluster and make the new videos feel like the strongest "
                "retention winners from this library."
            )
        else:
            reels_remaining = max(0, self.MIN_REELS_FOR_RECOMMENDATION - reels_tracked)
            recommendation_title = (
                "Retention summary for this session"
                if reels_tracked > 0
                else "Watch at least 3 reels in this session"
            )
            recommendation_body = (
                f"Draftr has retention data for {reels_tracked} reel"
                f"{'' if reels_tracked == 1 else 's'} in this current viewing session. "
                f"Watch {reels_remaining} more reel{'' if reels_remaining == 1 else 's'} to unlock a stronger "
                "gameplay, caption, and hook recommendation."
                if reels_remaining > 0
                else "Draftr is waiting for enough reel-level retention data to rank gameplay, captions, and hooks."
            )

        return ChatRecommendationResponse(
            chat_id=chat_id,
            chat=chat,
            session_id=session_id,
            has_enough_data=has_enough_data,
            min_reels_required=self.MIN_REELS_FOR_RECOMMENDATION,
            reels_tracked=reels_tracked,
            total_sessions=len(engagements),
            total_watch_time_seconds=total_watch_time_seconds,
            unique_viewers=len(unique_viewers),
            high_retention_sessions=high_retention_sessions,
            recommendation_title=recommendation_title,
            recommendation_body=recommendation_body,
            generation_prompt=generation_prompt,
            top_gameplay=gameplay_insights[:3],
            top_caption_styles=caption_insights[:3],
            top_text_styles=text_style_insights[:3],
            retention_summary=retention_summary,
            winning_profile={
                "gameplay": winning_gameplay.model_dump() if winning_gameplay else None,
                "caption_style": winning_caption.model_dump() if winning_caption else None,
                "text_style": winning_text_style.model_dump() if winning_text_style else None,
            },
        )

    async def list_chat_generated_assets(
        self,
        chat_id: str,
        auth: RequestAuthContext,
    ) -> ChatGeneratedAssetsResponse:
        chat = await self.get_accessible_chat(chat_id, auth)
        batches = await self.repository.list_batches_for_chat(chat_id)
        assets: list[ChatGeneratedAsset] = []

        for batch in batches:
            items = await self.repository.get_batch_items(batch.id)
            for item in items:
                if item.status != BatchItemStatus.UPLOADED or not item.output_url:
                    continue
                assets.append(
                    ChatGeneratedAsset(
                        chat_id=chat_id,
                        batch_id=batch.id,
                        batch_status=batch.status,
                        batch_created_at=batch.created_at,
                        batch_updated_at=batch.updated_at,
                        source_url=batch.source_url,
                        title_hint=batch.title_hint,
                        item_id=item.id,
                        item_index=item.item_index,
                        item_status=item.status,
                        output_url=item.output_url,
                        render_metadata=item.render_metadata,
                        script=(
                            item.script
                            if isinstance(item.script, ScriptDraft)
                            else ScriptDraft.model_validate(item.script)
                            if item.script is not None
                            else None
                        ),
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                    )
                )

        assets.sort(key=lambda asset: (asset.batch_updated_at, asset.updated_at, -asset.item_index), reverse=True)
        return ChatGeneratedAssetsResponse(chat_id=chat_id, chat=chat, items=assets)

    async def refresh_chat_summary(self, chat_id: str) -> ChatRecord:
        chat = await self.repository.get_chat(chat_id)
        batches = await self.repository.list_batches_for_chat(chat_id)
        if not batches:
            if chat is None:
                chat = await self.repository.create_chat(ChatRecord(id=chat_id))
            return chat

        latest_batch = batches[0]
        latest_source = await self.repository.get_source_document(latest_batch.id)
        fallback_source_label = chat.last_source_label if chat is not None else None
        last_source_label = (
            latest_source.title
            if latest_source is not None and latest_source.title
            else latest_batch.title_hint or fallback_source_label or self._source_label_from_batch(latest_batch)
        )
        last_source_url = latest_batch.source_url or (chat.last_source_url if chat else None)
        title = self._resolve_chat_title(
            title=latest_batch.title_hint,
            source_label=last_source_label,
            source_url=last_source_url,
            fallback=chat.title if chat else "Untitled chat",
        )

        total_exported = 0
        total_failed = 0
        cover_batch_id: str | None = None
        cover_item_id: str | None = None
        cover_output_url: str | None = None
        cover_thumbnail_url: str | None = None

        for batch in batches:
            items = await self.repository.get_batch_items(batch.id)
            uploaded = [item for item in items if item.status == BatchItemStatus.UPLOADED and item.output_url]
            failed = [item for item in items if item.status == BatchItemStatus.FAILED]
            total_exported += len(uploaded)
            total_failed += len(failed)
            if cover_item_id is None and uploaded:
                cover_item = sorted(
                    uploaded,
                    key=lambda item: (item.updated_at, -item.item_index),
                    reverse=True,
                )[0]
                cover_batch_id = batch.id
                cover_item_id = cover_item.id
                cover_output_url = cover_item.output_url
                cover_thumbnail_url = str(cover_item.render_metadata.get("thumbnail_url") or "") or None

        metadata = dict(chat.metadata) if chat is not None else {}
        if cover_thumbnail_url:
            metadata["cover_thumbnail_url"] = cover_thumbnail_url
        else:
            metadata.pop("cover_thumbnail_url", None)

        changes = {
            "title": title,
            "updated_at": latest_batch.updated_at,
            "last_source_label": last_source_label,
            "last_source_url": last_source_url,
            "total_runs": len(batches),
            "total_exported": total_exported,
            "total_failed": total_failed,
            "last_status": latest_batch.status.value if hasattr(latest_batch.status, "value") else str(latest_batch.status),
            "cover_batch_id": cover_batch_id,
            "cover_item_id": cover_item_id,
            "cover_output_url": cover_output_url,
            "metadata": metadata,
        }

        if chat is None:
            created_at = min(batch.created_at for batch in batches)
            chat = await self.repository.create_chat(
                ChatRecord(
                    id=chat_id,
                    created_at=created_at,
                    **changes,
                )
            )
            return chat

        return await self.repository.update_chat(chat_id, **changes)

    async def sync_existing_chats(self) -> None:
        chats = await self.repository.list_chats()
        for chat in chats:
            await self.refresh_chat_summary(chat.id)

    def _assert_chat_access(self, chat: ChatRecord, auth: RequestAuthContext) -> None:
        if auth.is_authenticated:
            if chat.library_scope != ChatLibraryScope.USER or chat.owner_user_id != auth.user_id:
                raise PermissionError("This chat belongs to a different user library.")
            return

        if chat.library_scope != ChatLibraryScope.GENERAL:
            raise PermissionError("Sign in with Google to access this chat.")

    def _build_dimension_insights(
        self,
        sessions: list[tuple[ShortEngagementRecord, ChatGeneratedAsset, float]],
        *,
        key_builder,
        label_builder,
    ) -> list[RecommendationInsight]:
        buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "label": None,
                "sample_size": 0,
                "score_total": 0.0,
                "completion_total": 0.0,
                "watch_total": 0.0,
                "positive_sessions": 0,
            }
        )

        for engagement, asset, score in sessions:
            key = key_builder(engagement, asset)
            label = label_builder(engagement, asset)
            if not key or not label:
                continue
            bucket = buckets[key]
            bucket["label"] = label
            bucket["sample_size"] += 1
            bucket["score_total"] += score
            bucket["completion_total"] += self._clamp(engagement.completion_ratio, 0.0, 2.0)
            bucket["watch_total"] += max(0.0, engagement.watch_time_seconds)
            if any(
                (
                    engagement.unmuted,
                    engagement.info_opened,
                    engagement.open_clicked,
                    engagement.liked,
                    engagement.replay_count > 0,
                )
            ):
                bucket["positive_sessions"] += 1

        insights: list[RecommendationInsight] = []
        for key, bucket in buckets.items():
            sample_size = int(bucket["sample_size"])
            if sample_size <= 0:
                continue
            average_score = bucket["score_total"] / sample_size
            sample_bonus = min(0.12, sample_size * 0.02)
            insights.append(
                RecommendationInsight(
                    key=key,
                    label=str(bucket["label"]),
                    score=round(average_score + sample_bonus, 4),
                    sample_size=sample_size,
                    avg_completion_ratio=round(bucket["completion_total"] / sample_size, 4),
                    avg_watch_time_seconds=round(bucket["watch_total"] / sample_size, 4),
                    positive_action_rate=round(bucket["positive_sessions"] / sample_size, 4),
                )
            )

        insights.sort(
            key=lambda insight: (
                insight.score,
                insight.avg_completion_ratio,
                insight.positive_action_rate,
                insight.sample_size,
            ),
            reverse=True,
        )
        return insights

    def _score_engagement(
        self,
        engagement: ShortEngagementRecord,
        asset: ChatGeneratedAsset,
    ) -> float:
        estimated_seconds = float(
            asset.script.estimated_seconds
            if asset.script is not None and asset.script.estimated_seconds is not None
            else max(engagement.max_progress_seconds, 1.0)
        )
        watch_share = self._clamp(engagement.watch_time_seconds / max(estimated_seconds, 1.0), 0.0, 1.5)
        completion = self._clamp(engagement.completion_ratio, 0.0, 1.5)

        score = completion * 0.65 + min(watch_share, 1.0) * 0.35
        if completion >= 0.9 or watch_share >= 0.9:
            score += 0.15
        if engagement.replay_count > 0:
            score += min(0.12, engagement.replay_count * 0.04)
        if engagement.unmuted:
            score += 0.06
        if engagement.info_opened:
            score += 0.04
        if engagement.open_clicked:
            score += 0.08
        if engagement.liked:
            score += 0.10
        if engagement.skipped_early:
            score -= 0.25
        return round(score, 4)

    def _caption_key(self, asset: ChatGeneratedAsset) -> str:
        style = str(asset.render_metadata.get("subtitle_style_label") or "Unknown captions").strip()
        font = str(asset.render_metadata.get("subtitle_font_name") or "").strip()
        parts = [style.casefold().replace(" ", "-")]
        if font:
            parts.append(font.casefold().replace(" ", "-"))
        return "::".join(parts)

    def _caption_label(self, asset: ChatGeneratedAsset) -> str:
        style = str(asset.render_metadata.get("subtitle_style_label") or "Unknown captions").strip()
        font = str(asset.render_metadata.get("subtitle_font_name") or "").strip()
        return f"{style} · {font}" if font else style

    def _gameplay_family(self, gameplay_path: object) -> str:
        path = str(gameplay_path or "").strip()
        if not path:
            return "unknown"
        normalized = path.replace("\\", "/").strip("/")
        parts = normalized.split("/")
        if len(parts) >= 2 and parts[0] == "gameplay":
            return parts[1].casefold()
        return parts[0].casefold() if parts else "unknown"

    def _gameplay_label(self, gameplay_path: object) -> str:
        family = self._gameplay_family(gameplay_path)
        if family == "gta-5":
            return "GTA 5"
        if family == "subway-surfers":
            return "Subway Surfers"
        if family == "unknown":
            return "Mixed gameplay"
        return family.replace("-", " ").title()

    def _text_style_key(self, script: ScriptDraft | None) -> str:
        return self._detect_text_style(script)[0]

    def _text_style_label(self, script: ScriptDraft | None) -> str:
        return self._detect_text_style(script)[1]

    def _detect_text_style(self, script: ScriptDraft | None) -> tuple[str, str]:
        if script is None:
            return ("explainer", "explainer")

        combined = " ".join(
            part
            for part in (
                script.title,
                script.hook,
                script.narration_text[:220],
            )
            if part
        ).casefold()

        warning_terms = ("danger", "hidden", "mistake", "risk", "warning", "problem", "threat", "don't", "dont")
        workflow_terms = ("how to", "step", "build", "turn", "deploy", "setup", "workflow", "from", "into")
        listicle_terms = ("reasons", "ways", "signs", "tips", "lessons", "mistakes", "things")
        feature_terms = ("feature", "tool", "agent", "pipeline", "system", "library", "engine")

        if any(term in combined for term in warning_terms):
            return ("warning", "warning-style")
        if any(term in combined for term in workflow_terms):
            return ("workflow", "workflow-led")
        if any(term in combined for term in listicle_terms):
            return ("listicle", "listicle")
        if any(term in combined for term in feature_terms):
            return ("feature_led", "feature-led")
        return ("explainer", "explainer")

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _matches_session_scope(self, engagement: ShortEngagementRecord, session_id: str) -> bool:
        page_session_id = str(engagement.metadata.get("page_session_id") or "").strip()
        if page_session_id:
            return page_session_id == session_id
        if engagement.session_id == session_id:
            return True
        return engagement.session_id.startswith(f"{session_id}:")

    def _source_label_from_batch(self, batch: BatchRecord) -> str | None:
        if batch.source_url:
            parsed = urlparse(batch.source_url)
            if parsed.netloc:
                return parsed.netloc
            return batch.source_url
        return batch.title_hint

    def _resolve_chat_title(
        self,
        *,
        title: str | None,
        source_label: str | None,
        source_url: str | None,
        fallback: str,
    ) -> str:
        for candidate in (title, source_label):
            if candidate and candidate.strip():
                return candidate.strip()
        if source_url:
            parsed = urlparse(source_url)
            if parsed.netloc:
                return parsed.netloc
            if source_url.strip():
                return source_url.strip()
        return fallback
