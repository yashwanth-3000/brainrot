from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import time
from collections import Counter
from pathlib import Path
from contextlib import suppress

from brainrot_backend.config import Settings
from brainrot_backend.video_generator.integrations.firecrawl import FirecrawlClient
from brainrot_backend.shared.models.domain import AssetRecord, BatchItemRecord, BatchRecord, GeneratedBundle, ScriptDraft
from brainrot_backend.shared.models.enums import AssetKind, BatchEventType, BatchItemStatus, BatchStatus
from brainrot_backend.video_generator.render.assets import AssetSelector
from brainrot_backend.video_generator.render.ffmpeg import FFmpegRenderer
from brainrot_backend.video_generator.render.subtitles import SubtitlePreset, build_subtitle_track, subtitle_presets
from brainrot_backend.video_generator.services.agents import AgentService
from brainrot_backend.video_generator.services.assets import filter_allowed_gameplay_assets
from brainrot_backend.recommendation_system.service import ChatService
from brainrot_backend.video_generator.services.events import EventBroker
from brainrot_backend.shared.storage.base import BlobStore, Repository

logger = logging.getLogger(__name__)


class BatchOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: Repository,
        blob_store: BlobStore,
        events: EventBroker,
        firecrawl: FirecrawlClient,
        agent_service: AgentService,
        chat_service: ChatService,
        asset_selector: AssetSelector,
        renderer: FFmpegRenderer,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.blob_store = blob_store
        self.events = events
        self.firecrawl = firecrawl
        self.agent_service = agent_service
        self.chat_service = chat_service
        self.asset_selector = asset_selector
        self.renderer = renderer
        self._font_assets_by_key: dict[str, AssetRecord] | None = None

    async def run_batch(self, batch_id: str, *, retry_failed_only: bool = False) -> None:
        batch = await self.repository.get_batch(batch_id)
        if batch is None:
            raise RuntimeError(f"Batch {batch_id} not found.")

        logger.info("Starting batch %s (count=%d, retry_only=%s)", batch_id, batch.requested_count, retry_failed_only)
        try:
            source = await self.repository.get_source_document(batch_id)
            if source is None:
                batch = await self._set_batch_status(batch_id, BatchStatus.INGESTING)
                ingest_started_at = time.perf_counter()
                logger.info("Ingesting source for batch %s (url=%s, kind=%s)", batch_id, batch.source_url, batch.source_kind)
                await self._publish_log(
                    batch_id,
                    stage="ingest",
                    message="Starting source ingestion.",
                    source_url=batch.source_url,
                    source_kind=batch.source_kind.value,
                    elapsed_seconds=0.0,
                )
                source = await self.firecrawl.ingest(
                    source_url=batch.source_url,
                    source_kind=batch.source_kind,
                    uploaded_file_path=batch.metadata.get("uploaded_file_path"),
                    progress_callback=lambda payload: self._publish_log(batch_id, **payload),
                )
                ingest_elapsed_seconds = round(time.perf_counter() - ingest_started_at, 1)
                await self.repository.add_source_document(batch_id, source)
                await self.events.publish(
                    batch_id,
                    BatchEventType.SOURCE_INGESTED,
                    {
                        "title": source.title,
                        "source_kind": source.source_kind.value,
                        "url_count": len(source.normalized_urls),
                        "elapsed_seconds": ingest_elapsed_seconds,
                    },
                )
                await self._publish_log(
                    batch_id,
                    stage="ingest",
                    message=f"Source ingestion completed for {source.title}.",
                    source_title=source.title,
                    url_count=len(source.normalized_urls),
                    elapsed_seconds=ingest_elapsed_seconds,
                )
                logger.info("Source ingested for batch %s: %s (%d chars)", batch_id, source.title, len(source.markdown))

            candidates = await self.repository.list_assets()
            gameplay_assets = filter_allowed_gameplay_assets(self.settings, candidates)
            music_assets = [asset for asset in candidates if asset.kind == AssetKind.MUSIC]

            if not gameplay_assets:
                raise RuntimeError(
                    "No gameplay assets are available. Upload gameplay clips via POST /v1/assets/upload "
                    "or enable auto_seed_assets in config."
                )

            if not music_assets:
                logger.warning("No music assets available. Videos will be rendered without background music.")

            logger.info(
                "Rendering batch %s: %d items, %d gameplay assets, %d music assets",
                batch_id, batch.requested_count, len(gameplay_assets), len(music_assets),
            )

            items = await self.repository.get_batch_items(batch_id)
            render_semaphore = asyncio.Semaphore(self.settings.render_concurrency)
            producer_semaphore = asyncio.Semaphore(max(1, self.settings.producer_chunk_concurrency))
            planning_lock = asyncio.Lock()
            render_tasks: list[asyncio.Task[None]] = []
            accepted_scripts: list[ScriptDraft] = []
            accepted_title_keys: set[str] = set()
            accepted_hook_keys: set[str] = set()
            merged_angles = []
            merged_source_brief = None
            used_gameplay_ids: set[str] = set()
            used_music_ids: set[str] = set()
            subtitle_state = {
                "used_counts": Counter(),
                "last_preset_id": None,
                "target_count": max(
                    1,
                    len(
                        [
                            item
                            for item in items
                            if not retry_failed_only or item.status == BatchItemStatus.FAILED
                        ]
                    ),
                ),
                "quota_counts": {},
            }
            render_status_promoted = False
            producer_started_at = time.perf_counter()

            async def launch_item(item: BatchItemRecord, script: ScriptDraft) -> None:
                nonlocal batch, render_status_promoted
                queued_item = await self.repository.update_batch_item(
                    item.id,
                    script=script,
                    status=BatchItemStatus.QUEUED,
                    error=None,
                )
                async with planning_lock:
                    gameplay = self.asset_selector.choose_gameplay(
                        script,
                        gameplay_assets,
                        used_asset_ids=used_gameplay_ids,
                    )
                    used_gameplay_ids.add(gameplay.id)
                    music = None
                    if music_assets:
                        music = self.asset_selector.choose_music(
                            script,
                            music_assets,
                            used_asset_ids=used_music_ids,
                        )
                        used_music_ids.add(music.id)
                    subtitle_preset = self._choose_subtitle_preset(
                        queued_item,
                        script,
                        gameplay,
                        subtitle_state=subtitle_state,
                    )

                if not render_status_promoted:
                    batch = await self._set_batch_status(batch_id, BatchStatus.RENDERING)
                    render_status_promoted = True
                render_tasks.append(
                    asyncio.create_task(
                        self._render_item_with_guard(
                            render_semaphore,
                            batch=batch,
                            item=queued_item,
                            gameplay=gameplay,
                            music=music,
                            subtitle_preset=subtitle_preset,
                        )
                    )
                )

            async def accept_bundle_scripts(
                chunk_items: list[BatchItemRecord],
                bundle: GeneratedBundle,
                *,
                producer_label: str,
            ) -> list[BatchItemRecord]:
                nonlocal merged_source_brief
                if merged_source_brief is None:
                    merged_source_brief = bundle.source_brief
                merged_angles.extend(bundle.angles)
                unresolved: list[BatchItemRecord] = []
                accepted_now = 0
                bundle_scripts = list(bundle.scripts)
                if len(bundle_scripts) < len(chunk_items):
                    unresolved.extend(chunk_items[len(bundle_scripts):])

                for item, script in zip(chunk_items, bundle_scripts, strict=False):
                    title_key = script.title.strip().casefold()
                    hook_key = script.hook.strip().casefold()
                    if title_key in accepted_title_keys or hook_key in accepted_hook_keys:
                        diversified = self._diversify_script_identity(
                            script,
                            source_facts=merged_source_brief.facts if merged_source_brief is not None else bundle.source_brief.facts,
                            item_index=item.item_index,
                        )
                        diversified_title_key = diversified.title.strip().casefold()
                        diversified_hook_key = diversified.hook.strip().casefold()
                        if diversified_title_key in accepted_title_keys or diversified_hook_key in accepted_hook_keys:
                            unresolved.append(item)
                            continue
                        script = diversified
                        title_key = diversified_title_key
                        hook_key = diversified_hook_key

                    accepted_title_keys.add(title_key)
                    accepted_hook_keys.add(hook_key)
                    accepted_scripts.append(script)
                    accepted_now += 1
                    await launch_item(item, script)

                if accepted_now:
                    await self._publish_log(
                        batch_id,
                        stage="producer",
                        message=f"Accepted {accepted_now} scripts from {producer_label}. Starting video generation immediately.",
                        source=producer_label,
                        accepted_count=accepted_now,
                        total_script_count=len(accepted_scripts),
                        elapsed_seconds=round(time.perf_counter() - producer_started_at, 1),
                    )
                return unresolved

            async def produce_chunk(chunk_items: list[BatchItemRecord], chunk_index: int, depth: int = 0) -> None:
                if not chunk_items:
                    return
                if len(chunk_items) == 1:
                    producer_label = f"item {chunk_items[0].item_index + 1}"
                else:
                    producer_label = f"slice {chunk_index}"
                if depth > 0:
                    producer_label = f"{producer_label} · split {depth}"
                chunk_count = len(chunk_items)

                async with producer_semaphore:
                    try:
                        bundle = await self.agent_service.run_producer(
                            batch_id=batch_id,
                            source=source,
                            requested_count=chunk_count,
                            requested_config_id=batch.producer_agent_config_id,
                            use_cached_bundle=False,
                            persist_bundle=False,
                            emit_ready_events=False,
                            producer_label=producer_label,
                        )
                    except Exception as exc:
                        if chunk_count > 1:
                            midpoint = max(1, chunk_count // 2)
                            left = chunk_items[:midpoint]
                            right = chunk_items[midpoint:]
                            await self._publish_log(
                                batch_id,
                                stage="producer",
                                message=f"{producer_label} failed for {chunk_count} scripts. Splitting the slice and continuing.",
                                source=producer_label,
                                error=str(exc),
                                elapsed_seconds=round(time.perf_counter() - producer_started_at, 1),
                            )
                            await asyncio.gather(
                                produce_chunk(left, chunk_index, depth + 1),
                                produce_chunk(right, chunk_index + 100 + depth, depth + 1),
                            )
                            return

                        item = chunk_items[0]
                        await self.repository.update_batch_item(
                            item.id,
                            status=BatchItemStatus.FAILED,
                            error=str(exc),
                        )
                        await self.events.publish(
                            batch_id,
                            BatchEventType.ERROR,
                            {"item_id": item.id, "item_index": item.item_index, "message": str(exc)},
                        )
                        return

                unresolved = await accept_bundle_scripts(chunk_items, bundle, producer_label=producer_label)
                if unresolved:
                    if len(unresolved) == 1 and len(chunk_items) == 1:
                        item = unresolved[0]
                        await self.repository.update_batch_item(
                            item.id,
                            status=BatchItemStatus.FAILED,
                            error="Producer returned a duplicate script that could not be diversified.",
                        )
                        return

                    await self._publish_log(
                        batch_id,
                        stage="producer",
                        message=f"{len(unresolved)} scripts from {producer_label} still need regeneration. Retrying just those slots.",
                        source=producer_label,
                        elapsed_seconds=round(time.perf_counter() - producer_started_at, 1),
                    )
                    await produce_chunk(unresolved, chunk_index + 200 + depth, depth + 1)

            existing_ready_items = [
                item
                for item in items
                if (not retry_failed_only or item.status == BatchItemStatus.FAILED) and item.script is not None
            ]
            if existing_ready_items:
                for item in sorted(existing_ready_items, key=lambda candidate: candidate.item_index):
                    script = item.script if isinstance(item.script, ScriptDraft) else ScriptDraft.model_validate(item.script)
                    accepted_scripts.append(script)
                    accepted_title_keys.add(script.title.strip().casefold())
                    accepted_hook_keys.add(script.hook.strip().casefold())
                    await launch_item(item, script)

            missing_items = [
                item
                for item in items
                if not retry_failed_only and item.script is None
            ]
            if missing_items and not render_status_promoted:
                batch = await self._set_batch_status(batch_id, BatchStatus.SCRIPTING)
                chunk_size = max(1, self.settings.producer_chunk_size)
                chunks = [
                    missing_items[index: index + chunk_size]
                    for index in range(0, len(missing_items), chunk_size)
                ]
                await asyncio.gather(
                    *[
                        produce_chunk(chunk, chunk_index + 1)
                        for chunk_index, chunk in enumerate(chunks)
                    ]
                )

            if accepted_scripts and merged_source_brief is not None:
                await self.repository.save_generated_bundle(
                    batch_id,
                    GeneratedBundle(
                        source_brief=merged_source_brief,
                        angles=merged_angles,
                        scripts=accepted_scripts,
                    ),
                )
                batch_metadata = dict((await self.repository.get_batch(batch_id)).metadata)
                batch_metadata["producer_metrics"] = {
                    "mode": self.settings.producer_mode,
                    "chunk_size": self.settings.producer_chunk_size,
                    "chunk_count": max(1, (len(missing_items) + max(1, self.settings.producer_chunk_size) - 1) // max(1, self.settings.producer_chunk_size)),
                    "script_count": len(accepted_scripts),
                    "elapsed_seconds": round(time.perf_counter() - producer_started_at, 2),
                }
                await self.repository.update_batch(batch_id, metadata=batch_metadata)
                await self.events.publish(
                    batch_id,
                    BatchEventType.SCRIPTS_READY,
                    {
                        "script_count": len(accepted_scripts),
                        "angle_count": len(merged_angles),
                        **batch_metadata["producer_metrics"],
                    },
                )

            if render_tasks:
                await asyncio.gather(*render_tasks)
            await self._finalize_batch(batch_id)
        except Exception as exc:
            logger.error("Batch %s failed: %s", batch_id, exc, exc_info=True)
            await self.repository.update_batch(
                batch_id,
                status=BatchStatus.FAILED,
                error=str(exc),
            )
            await self.events.publish(batch_id, BatchEventType.ERROR, {"message": str(exc)})
            raise

    async def run_preview(
        self,
        batch_id: str,
        *,
        item_id: str,
        gameplay_asset_id: str,
        subtitle_preset_id: str,
        music_asset_id: str | None = None,
    ) -> None:
        batch = await self.repository.get_batch(batch_id)
        item = await self.repository.get_batch_item(item_id)
        if batch is None or item is None:
            raise RuntimeError(f"Preview batch {batch_id} is not available.")

        gameplay_assets = filter_allowed_gameplay_assets(
            self.settings,
            await self.repository.list_assets(AssetKind.GAMEPLAY),
        )
        music_assets = await self.repository.list_assets(AssetKind.MUSIC)
        gameplay = next((asset for asset in gameplay_assets if asset.id == gameplay_asset_id), None)
        if gameplay is None:
            raise RuntimeError(f"Gameplay asset {gameplay_asset_id} was not found.")

        music = None
        if music_asset_id:
            music = next((asset for asset in music_assets if asset.id == music_asset_id), None)
            if music is None:
                raise RuntimeError(f"Music asset {music_asset_id} was not found.")

        subtitle_preset = self._subtitle_preset_by_id(subtitle_preset_id)
        batch = await self._set_batch_status(batch_id, BatchStatus.RENDERING)
        semaphore = asyncio.Semaphore(1)
        await self._render_item_with_guard(
            semaphore,
            batch=batch,
            item=item,
            gameplay=gameplay,
            music=music,
            subtitle_preset=subtitle_preset,
        )
        await self._finalize_batch(batch_id)

    async def _render_item_with_guard(
        self,
        semaphore: asyncio.Semaphore,
        *,
        batch: BatchRecord,
        item: BatchItemRecord,
        gameplay,
        music,
        subtitle_preset: SubtitlePreset,
    ) -> None:
        async with semaphore:
            try:
                await self._render_item(batch, item, gameplay, music, subtitle_preset)
            except Exception as exc:
                logger.error(
                    "Item %s (index=%d) failed: %s", item.id, item.item_index, exc, exc_info=True,
                )
                await self.repository.update_batch_item(item.id, status=BatchItemStatus.FAILED, error=str(exc))
                await self.events.publish(
                    batch.id,
                    BatchEventType.ERROR,
                    {"item_id": item.id, "item_index": item.item_index, "message": str(exc)},
                )

    async def _render_item(
        self,
        batch: BatchRecord,
        item: BatchItemRecord,
        gameplay,
        music,
        subtitle_preset: SubtitlePreset,
    ) -> None:
        script = item.script if isinstance(item.script, ScriptDraft) else ScriptDraft.model_validate(item.script)
        logger.info("Rendering item %s (index=%d): %s", item.id, item.item_index, script.title)

        await self.repository.update_batch_item(item.id, status=BatchItemStatus.NARRATING, error=None)
        artifact = await self.agent_service.narrate_item(
            batch_id=batch.id,
            batch_item_id=item.id,
            script=script,
            premium_audio=batch.premium_audio,
            requested_config_id=batch.narrator_agent_config_id,
        )
        await self.repository.update_batch_item(item.id, status=BatchItemStatus.SELECTING_ASSETS)
        await self._publish_log(
            batch.id,
            stage="assets",
            message=f"Staging assets for item {item.id}.",
            item_id=item.id,
            item_index=item.item_index,
            elapsed_seconds=0.0,
        )

        item_dir = self.settings.temp_dir / batch.id / item.id
        item_dir.mkdir(parents=True, exist_ok=True)

        narration_path = item_dir / f"narration.{artifact.format}"
        narration_path.write_bytes(artifact.audio_bytes)
        subtitle_track = build_subtitle_track(
            artifact.word_timings,
            item_dir / "subtitles.ass",
            preset=subtitle_preset,
        )
        subtitle_font_dir = await self._stage_subtitle_font(item_dir, subtitle_track.preset)

        await self.blob_store.upload_bytes(
            self.settings.subtitle_bucket,
            f"{batch.id}/{item.id}/subtitles.ass",
            subtitle_track.path.read_bytes(),
            content_type="text/plain",
        )

        gameplay_path = await self.blob_store.materialize(
            gameplay.bucket,
            gameplay.path,
            item_dir / f"gameplay-{Path(gameplay.path).name}",
        )
        music_path: Path | None = None
        if music is not None:
            music_path = await self.blob_store.materialize(
                music.bucket,
                music.path,
                item_dir / f"music-{Path(music.path).name}",
            )

        logger.info(
            "Selected assets for item %s: gameplay=%s music=%s subtitle=%s/%s",
            item.id,
            gameplay.path,
            music.path if music else "none",
            subtitle_track.preset.id,
            subtitle_track.preset.font_name,
        )

        await self.repository.update_batch_item(item.id, status=BatchItemStatus.RENDERING)
        render_started_at = time.perf_counter()
        await self._publish_log(
            batch.id,
            stage="render",
            message=f"Render started for item {item.id}.",
            item_id=item.id,
            item_index=item.item_index,
            gameplay_asset_path=gameplay.path,
            subtitle_style_label=subtitle_track.preset.label,
            elapsed_seconds=0.0,
        )
        await self.events.publish(
            batch.id,
            BatchEventType.RENDER_STARTED,
            {
                "item_id": item.id,
                "item_index": item.item_index,
                "gameplay_asset_path": gameplay.path,
                "music_asset_path": music.path if music else None,
                "subtitle_style_id": subtitle_track.preset.id,
                "subtitle_style_label": subtitle_track.preset.label,
                "subtitle_animation": subtitle_track.preset.animation,
                "subtitle_font_name": subtitle_track.preset.font_name,
            },
        )

        output_path = await self._await_with_render_heartbeat(
            self.renderer.render(
                gameplay_path=gameplay_path,
                music_path=music_path,
                narration_path=narration_path,
                subtitle_path=subtitle_track.path,
                fonts_dir=subtitle_font_dir,
                output_path=item_dir / "final.mp4",
            ),
            batch_id=batch.id,
            item_id=item.id,
            item_index=item.item_index,
            started_at=render_started_at,
        )
        await self._publish_log(
            batch.id,
            stage="render",
            message=f"Render completed for item {item.id}. Uploading final video.",
            item_id=item.id,
            item_index=item.item_index,
            elapsed_seconds=round(time.perf_counter() - render_started_at, 1),
        )
        thumbnail_public_url: str | None = None
        thumbnail_path = item_dir / "thumbnail.jpg"
        try:
            await self._generate_thumbnail(output_path=output_path, thumbnail_path=thumbnail_path)
            thumbnail_public_url = await self.blob_store.upload_bytes(
                self.settings.final_render_bucket,
                f"{batch.id}/{item.id}.jpg",
                thumbnail_path.read_bytes(),
                content_type="image/jpeg",
            )
        except Exception as exc:  # pragma: no cover - best-effort thumbnailing
            logger.warning("Thumbnail generation failed for item %s: %s", item.id, exc)

        public_url = await self.blob_store.upload_bytes(
            self.settings.final_render_bucket,
            f"{batch.id}/{item.id}.mp4",
            output_path.read_bytes(),
            content_type="video/mp4",
        )
        await self.repository.update_batch_item(
            item.id,
            status=BatchItemStatus.UPLOADED,
            narration_conversation_id=artifact.conversation_id,
            output_url=public_url,
            render_metadata={
                "conversation_id": artifact.conversation_id,
                "gameplay_asset_id": gameplay.id,
                "gameplay_asset_path": gameplay.path,
                "gameplay_source_path": gameplay.metadata.get("source_path"),
                "music_asset_id": music.id if music else None,
                "music_asset_path": music.path if music else None,
                "subtitle_word_count": len(artifact.word_timings),
                "subtitle_style_id": subtitle_track.preset.id,
                "subtitle_style_label": subtitle_track.preset.label,
                "subtitle_animation": subtitle_track.preset.animation,
                "subtitle_font_name": subtitle_track.preset.font_name,
                "subtitle_font_file": subtitle_track.preset.font_path.name,
                "subtitle_font_source_path": str(subtitle_track.preset.font_path),
                "thumbnail_url": thumbnail_public_url,
            },
        )
        await self.events.publish(
            batch.id,
            BatchEventType.ITEM_COMPLETED,
            {
                "item_id": item.id,
                "item_index": item.item_index,
                "output_url": public_url,
            },
        )
        logger.info("Item %s completed: %s", item.id, public_url)

        self._cleanup_temp(item_dir)

    async def _generate_thumbnail(self, *, output_path: Path, thumbnail_path: Path) -> Path:
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.settings.ffmpeg_bin,
            "-y",
            "-ss", "0.35",
            "-i", str(output_path),
            "-frames:v", "1",
            "-vf", "scale=270:480:force_original_aspect_ratio=increase,crop=270:480",
            "-q:v", "2",
            str(thumbnail_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            error_text = stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"FFmpeg thumbnail extraction failed: {error_text[-500:]}")
        return thumbnail_path

    def _plan_assets(
        self,
        items: list[BatchItemRecord],
        gameplay_assets: list[AssetRecord],
        music_assets: list[AssetRecord],
    ) -> dict[str, tuple[AssetRecord, AssetRecord | None]]:
        used_gameplay_ids: set[str] = set()
        used_music_ids: set[str] = set()
        planned: dict[str, tuple[AssetRecord, AssetRecord | None]] = {}
        for item in items:
            script = item.script if isinstance(item.script, ScriptDraft) else ScriptDraft.model_validate(item.script)
            gameplay = self.asset_selector.choose_gameplay(
                script,
                gameplay_assets,
                used_asset_ids=used_gameplay_ids,
            )
            used_gameplay_ids.add(gameplay.id)
            music = None
            if music_assets:
                music = self.asset_selector.choose_music(
                    script,
                    music_assets,
                    used_asset_ids=used_music_ids,
                )
                used_music_ids.add(music.id)
            planned[item.id] = (gameplay, music)
        return planned

    def _plan_subtitle_presets(
        self,
        items: list[BatchItemRecord],
        planned_assets: dict[str, tuple[AssetRecord, AssetRecord | None]],
    ) -> dict[str, SubtitlePreset]:
        presets = list(subtitle_presets(self.settings.assets_dir / "fonts"))
        if not presets:
            raise RuntimeError("No subtitle presets are configured.")

        subtitle_state: dict[str, object] = {
            "used_counts": Counter(),
            "last_preset_id": None,
            "target_count": max(1, len(items)),
            "quota_counts": self._build_subtitle_quota_map(presets, max(1, len(items))),
        }
        planned: dict[str, SubtitlePreset] = {}

        for item in sorted(items, key=lambda candidate: candidate.item_index):
            script = item.script if isinstance(item.script, ScriptDraft) else ScriptDraft.model_validate(item.script)
            gameplay = planned_assets[item.id][0]
            choice = self._choose_subtitle_preset(
                item,
                script,
                gameplay,
                subtitle_state=subtitle_state,
            )
            planned[item.id] = choice

        return planned

    def _subtitle_preset_by_id(self, preset_id: str) -> SubtitlePreset:
        presets = {preset.id: preset for preset in subtitle_presets(self.settings.assets_dir / "fonts")}
        try:
            return presets[preset_id]
        except KeyError as exc:
            raise RuntimeError(f"Subtitle preset {preset_id} is not configured.") from exc

    def _choose_subtitle_preset(
        self,
        item: BatchItemRecord,
        script: ScriptDraft,
        gameplay: AssetRecord,
        *,
        subtitle_state: dict[str, object],
    ) -> SubtitlePreset:
        presets = list(subtitle_presets(self.settings.assets_dir / "fonts"))
        if not presets:
            raise RuntimeError("No subtitle presets are configured.")

        used_counts: Counter[str] = subtitle_state["used_counts"]  # type: ignore[assignment]
        last_preset_id = subtitle_state["last_preset_id"]
        quota_counts = subtitle_state.get("quota_counts")
        if not quota_counts:
            quota_counts = self._build_subtitle_quota_map(presets, int(subtitle_state["target_count"]))
            subtitle_state["quota_counts"] = quota_counts

        ranked = self._rank_subtitle_presets(script, gameplay, presets)
        candidates = [
            preset
            for preset in ranked
            if used_counts[preset.id] < quota_counts.get(preset.id, 0)
        ]
        if not candidates:
            candidates = ranked

        non_repeating = [preset for preset in candidates if preset.id != last_preset_id]
        if non_repeating:
            candidates = non_repeating

        remaining_quota = {
            preset.id: max(0, quota_counts.get(preset.id, 0) - used_counts[preset.id])
            for preset in candidates
        }
        highest_remaining_quota = max(remaining_quota.values(), default=0)
        if highest_remaining_quota > 0:
            choice = next(
                preset for preset in candidates if remaining_quota[preset.id] == highest_remaining_quota
            )
        else:
            lowest_count = min(used_counts[preset.id] for preset in candidates)
            choice = next(preset for preset in candidates if used_counts[preset.id] == lowest_count)
        used_counts[choice.id] += 1
        subtitle_state["last_preset_id"] = choice.id
        return choice

    @staticmethod
    def _build_subtitle_quota_map(
        presets: list[SubtitlePreset],
        target_count: int,
    ) -> dict[str, int]:
        if not presets or target_count <= 0:
            return {}

        total_weight = sum(max(0, preset.selection_weight) for preset in presets)
        if total_weight <= 0:
            base_count = max(1, target_count // len(presets))
            return {preset.id: base_count for preset in presets}

        raw_counts = [
            target_count * max(0, preset.selection_weight) / total_weight
            for preset in presets
        ]
        floor_counts = [int(raw) for raw in raw_counts]
        remaining = target_count - sum(floor_counts)

        allocation_order = sorted(
            range(len(presets)),
            key=lambda index: (
                raw_counts[index] - floor_counts[index],
                presets[index].selection_weight,
                -index,
            ),
            reverse=True,
        )
        for index in allocation_order[:remaining]:
            floor_counts[index] += 1

        return {
            preset.id: count
            for preset, count in zip(presets, floor_counts, strict=False)
        }

    @staticmethod
    def _diversify_script_identity(
        script: ScriptDraft,
        *,
        source_facts: list[str],
        item_index: int,
    ) -> ScriptDraft:
        if not source_facts:
            return script

        fact = source_facts[item_index % len(source_facts)].strip().rstrip(".")
        shortened_fact = fact
        for separator in (".", ";", " - ", " — ", ":"):
            if separator in shortened_fact:
                shortened_fact = shortened_fact.split(separator, 1)[0].strip()
                break
        words = shortened_fact.split()
        if len(words) > 9:
            shortened_fact = " ".join(words[:9]).strip()

        title = shortened_fact.title() if shortened_fact.islower() else shortened_fact
        hook = fact if fact else script.hook
        source_facts_used = list(script.source_facts_used)
        if fact and fact not in source_facts_used:
            source_facts_used = [fact, *source_facts_used][: max(2, len(source_facts_used) + 1)]

        return script.model_copy(
            update={
                "title": title or script.title,
                "hook": hook or script.hook,
                "source_facts_used": source_facts_used or script.source_facts_used,
            }
        )

    def _rank_subtitle_presets(
        self,
        script: ScriptDraft,
        gameplay: AssetRecord,
        presets: list[SubtitlePreset],
    ) -> list[SubtitlePreset]:
        context_tags = {
            tag.lower()
            for tag in [
                *script.gameplay_tags,
                *script.music_tags,
                *gameplay.tags,
                *self._tokenize_context(gameplay.path),
                *self._tokenize_context(str(gameplay.metadata.get("source_path", ""))),
                *self._tokenize_context(" ".join(script.visual_beats)),
            ]
            if tag
        }
        scored: list[tuple[int, int, SubtitlePreset]] = []
        for preset in presets:
            overlap = len(context_tags.intersection({tag.lower() for tag in preset.preferred_tags}))
            seed = self._stable_subtitle_seed(script, gameplay, preset)
            scored.append((overlap, seed, preset))
        ranked = sorted(scored, key=lambda item: (-item[0], item[1], item[2].id))
        return [preset for _, _, preset in ranked]

    @staticmethod
    def _tokenize_context(value: str) -> list[str]:
        lowered = value.lower()
        for marker in ("-", "_", "/", ".", ","):
            lowered = lowered.replace(marker, " ")
        return [token for token in lowered.split() if token]

    @staticmethod
    def _stable_subtitle_seed(
        script: ScriptDraft,
        gameplay: AssetRecord,
        preset: SubtitlePreset,
    ) -> int:
        payload = "|".join(
            [
                script.title,
                script.hook,
                gameplay.path,
                preset.id,
            ]
        ).encode("utf-8")
        return int(hashlib.sha256(payload).hexdigest()[:8], 16)

    async def _stage_subtitle_font(self, item_dir: Path, preset: SubtitlePreset) -> Path | None:
        font_dir = item_dir / "fonts"
        font_dir.mkdir(parents=True, exist_ok=True)
        destination = font_dir / preset.font_path.name
        if preset.font_path.exists():
            shutil.copy2(preset.font_path, destination)
            return font_dir

        font_asset = await self._find_subtitle_font_asset(preset)
        if font_asset is None:
            raise RuntimeError(f"Subtitle font is missing: {preset.font_path}")
        await self.blob_store.materialize(font_asset.bucket, font_asset.path, destination)
        return font_dir

    async def _find_subtitle_font_asset(self, preset: SubtitlePreset) -> AssetRecord | None:
        font_assets = await self._font_asset_index()
        relative_source_path = None
        with suppress(ValueError):
            relative_source_path = str(preset.font_path.relative_to(self.settings.project_root))
        candidate_keys = [
            preset.font_path.name.lower(),
            str(preset.font_path).lower(),
        ]
        if relative_source_path:
            candidate_keys.append(relative_source_path.lower())
        for key in candidate_keys:
            asset = font_assets.get(key)
            if asset is not None:
                return asset
        return None

    async def _font_asset_index(self) -> dict[str, AssetRecord]:
        if self._font_assets_by_key is not None:
            return self._font_assets_by_key

        index: dict[str, AssetRecord] = {}
        for asset in await self.repository.list_assets(AssetKind.FONT):
            keys = {Path(asset.path).name.lower(), asset.path.lower()}
            filename = asset.metadata.get("filename")
            if isinstance(filename, str) and filename:
                keys.add(filename.lower())
            source_path = asset.metadata.get("source_path")
            if isinstance(source_path, str) and source_path:
                keys.add(source_path.lower())
                keys.add(Path(source_path).name.lower())
            for key in keys:
                index.setdefault(key, asset)
        self._font_assets_by_key = index
        return index

    async def _set_batch_status(self, batch_id: str, status: BatchStatus) -> BatchRecord:
        batch = await self.repository.update_batch(batch_id, status=status, error=None)
        await self.events.publish(batch_id, BatchEventType.STATUS, {"status": status.value})
        return batch

    async def _publish_log(
        self,
        batch_id: str,
        *,
        stage: str,
        message: str,
        **payload: object,
    ) -> None:
        normalized_payload = {
            "stage": stage,
            "message": message,
            **payload,
        }
        elapsed = normalized_payload.get("elapsed_seconds")
        if isinstance(elapsed, float):
            normalized_payload["elapsed_seconds"] = round(elapsed, 1)
        await self.events.publish(batch_id, BatchEventType.LOG, normalized_payload)

    async def _await_with_render_heartbeat(
        self,
        awaitable,
        *,
        batch_id: str,
        item_id: str,
        item_index: int,
        started_at: float,
    ):
        task = asyncio.create_task(awaitable)
        heartbeat_count = 0
        try:
            while True:
                try:
                    return await asyncio.wait_for(
                        asyncio.shield(task),
                        timeout=self.settings.progress_heartbeat_seconds,
                    )
                except TimeoutError:
                    heartbeat_count += 1
                    await self._publish_log(
                        batch_id,
                        stage="render",
                        message=f"FFmpeg still rendering item {item_id}.",
                        item_id=item_id,
                        item_index=item_index,
                        heartbeat=heartbeat_count,
                        elapsed_seconds=round(time.perf_counter() - started_at, 1),
                    )
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    async def _finalize_batch(self, batch_id: str) -> None:
        batch = await self.repository.get_batch(batch_id)
        items = await self.repository.get_batch_items(batch_id)
        uploaded = [item for item in items if item.status == BatchItemStatus.UPLOADED]
        failed = [item for item in items if item.status == BatchItemStatus.FAILED]
        if uploaded and failed:
            status = BatchStatus.PARTIAL_FAILED
        elif failed and not uploaded:
            status = BatchStatus.FAILED
        else:
            status = BatchStatus.COMPLETED
        await self.repository.update_batch(batch_id, status=status)
        logger.info(
            "Batch %s finalized: %s (uploaded=%d, failed=%d)",
            batch_id, status.value, len(uploaded), len(failed),
        )

        output_dir = self.settings.data_dir / self.settings.final_render_bucket / batch_id
        if output_dir.exists():
            videos = list(output_dir.glob("*.mp4"))
            logger.info("Exported %d videos to %s", len(videos), output_dir)
            for v in videos:
                logger.info("  -> %s (%.1f MB)", v.name, v.stat().st_size / 1024 / 1024)

        await self.events.publish(
            batch_id,
            BatchEventType.BATCH_COMPLETED,
            {
                "status": status.value,
                "uploaded_count": len(uploaded),
                "failed_count": len(failed),
            },
        )
        await self.events.publish(
            batch_id,
            BatchEventType.DONE,
            {
                "status": status.value,
                "uploaded_count": len(uploaded),
                "failed_count": len(failed),
            },
        )
        if batch is not None and batch.chat_id:
            await self.chat_service.refresh_chat_summary(batch.chat_id)

    @staticmethod
    def _cleanup_temp(item_dir: Path) -> None:
        try:
            shutil.rmtree(item_dir, ignore_errors=True)
        except Exception:
            pass
