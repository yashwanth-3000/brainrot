from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from uuid import uuid4

from brainrot_backend.config import Settings
from brainrot_backend.models.domain import AssetRecord
from brainrot_backend.models.enums import AssetKind
from brainrot_backend.storage.base import BlobStore, Repository

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-") or "file.bin"


class AssetService:
    def __init__(self, settings: Settings, repository: Repository, blob_store: BlobStore) -> None:
        self.settings = settings
        self.repository = repository
        self.blob_store = blob_store

    async def upload_asset(
        self,
        *,
        kind: AssetKind,
        filename: str,
        content: bytes,
        tags: list[str],
        metadata: dict[str, object] | None = None,
        content_type: str | None = None,
    ) -> AssetRecord:
        bucket = self._bucket_for(kind)
        safe_name = sanitize_filename(filename)
        path = f"{kind.value}/{uuid4()}-{safe_name}"
        public_url = await self.blob_store.upload_bytes(
            bucket,
            path,
            content,
            content_type=content_type,
        )
        asset = AssetRecord(
            kind=kind,
            bucket=bucket,
            path=path,
            public_url=public_url,
            tags=tags,
            metadata=metadata or {},
        )
        return await self.repository.create_asset(asset)

    async def list_assets(self, kind: AssetKind | None = None) -> list[AssetRecord]:
        return await self.repository.list_assets(kind)

    async def auto_seed_gameplay_assets(self) -> int:
        existing = await self.repository.list_assets(AssetKind.GAMEPLAY)
        if existing:
            logger.info("Found %d existing gameplay assets, skipping auto-seed", len(existing))
            return 0

        clips_dir = self.settings.assets_dir / "clips"
        index_csv = clips_dir / "index.csv"
        if not index_csv.exists():
            logger.warning("No index.csv found at %s, skipping auto-seed", index_csv)
            return 0

        seeded = 0
        with open(index_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game = row.get("game", "").strip()
                clip_name = row.get("clip_name", "").strip()
                if not game or not clip_name:
                    continue

                clip_path = clips_dir / game / clip_name
                if not clip_path.exists():
                    logger.warning("Clip file not found: %s", clip_path)
                    continue

                duration = float(row.get("duration_seconds", 25))
                hook_note = row.get("hook_note", "")
                tags = [game, "gameplay", "vertical", "no-copyright"]
                if hook_note:
                    tags.extend(word.lower() for word in hook_note.split() if len(word) > 3)

                bucket = self.settings.gameplay_bucket
                blob_path = f"gameplay/{game}/{clip_name}"
                content = clip_path.read_bytes()
                public_url = await self.blob_store.upload_bytes(
                    bucket, blob_path, content, content_type="video/mp4",
                )
                asset = AssetRecord(
                    kind=AssetKind.GAMEPLAY,
                    bucket=bucket,
                    path=blob_path,
                    public_url=public_url,
                    tags=tags,
                    metadata={
                        "game": game,
                        "duration_seconds": duration,
                        "hook_note": hook_note,
                        "source_path": str(clip_path.relative_to(self.settings.project_root)),
                    },
                )
                await self.repository.create_asset(asset)
                seeded += 1

        logger.info("Auto-seeded %d gameplay assets from %s", seeded, clips_dir)
        return seeded

    def _bucket_for(self, kind: AssetKind) -> str:
        return {
            AssetKind.GAMEPLAY: self.settings.gameplay_bucket,
            AssetKind.MUSIC: self.settings.music_bucket,
            AssetKind.FONT: self.settings.font_bucket,
            AssetKind.OVERLAY: self.settings.overlay_bucket,
        }[kind]
