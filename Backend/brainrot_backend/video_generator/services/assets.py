from __future__ import annotations

import csv
import logging
import re
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from uuid import uuid4

from brainrot_backend.config import Settings
from brainrot_backend.core.models.domain import AssetRecord
from brainrot_backend.core.models.enums import AssetKind
from brainrot_backend.core.storage.base import BlobStore, Repository

logger = logging.getLogger(__name__)
_FONT_SUFFIXES = {".ttf", ".otf"}
_FONT_CONTENT_TYPES = {
    ".ttf": "font/ttf",
    ".otf": "font/otf",
}


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
        allowed_games = allowed_gameplay_games(self.settings)
        with open(index_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game = row.get("game", "").strip()
                clip_name = row.get("clip_name", "").strip()
                if not game or not clip_name:
                    continue
                if normalize_game_slug(game) not in allowed_games:
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

    async def auto_seed_font_assets(self) -> int:
        fonts_dir = self.settings.assets_dir / "fonts"
        if not fonts_dir.exists():
            existing = await self.repository.list_assets(AssetKind.FONT)
            if existing:
                logger.info(
                    "No local fonts directory at %s; using %d stored font assets",
                    fonts_dir,
                    len(existing),
                )
                return 0
            logger.warning("No fonts directory found at %s, skipping font auto-seed", fonts_dir)
            return 0

        existing = await self.repository.list_assets(AssetKind.FONT)
        existing_paths = {asset.path for asset in existing}
        existing_source_paths = {
            str(asset.metadata.get("source_path", ""))
            for asset in existing
            if asset.metadata.get("source_path")
        }

        seeded = 0
        for font_path in _iter_font_files(fonts_dir):
            relative_to_fonts = font_path.relative_to(fonts_dir)
            source_path = str(font_path.relative_to(self.settings.project_root))
            blob_path = f"fonts/{relative_to_fonts.as_posix()}"
            if blob_path in existing_paths or source_path in existing_source_paths:
                continue

            content = font_path.read_bytes()
            public_url = await self.blob_store.upload_bytes(
                self.settings.font_bucket,
                blob_path,
                content,
                content_type=_FONT_CONTENT_TYPES.get(font_path.suffix.lower(), "application/octet-stream"),
            )
            asset = AssetRecord(
                kind=AssetKind.FONT,
                bucket=self.settings.font_bucket,
                path=blob_path,
                public_url=public_url,
                tags=["font", font_path.stem.lower()],
                metadata={
                    "filename": font_path.name,
                    "source_path": source_path,
                    "family_hint": font_path.stem.replace("-", " "),
                },
            )
            await self.repository.create_asset(asset)
            seeded += 1

        if seeded:
            logger.info("Auto-seeded %d subtitle fonts from %s", seeded, fonts_dir)
        else:
            logger.info("Found %d existing font assets, no new fonts seeded", len(existing))
        return seeded

    def _bucket_for(self, kind: AssetKind) -> str:
        return {
            AssetKind.GAMEPLAY: self.settings.gameplay_bucket,
            AssetKind.MUSIC: self.settings.music_bucket,
            AssetKind.FONT: self.settings.font_bucket,
            AssetKind.OVERLAY: self.settings.overlay_bucket,
        }[kind]


def _iter_font_files(fonts_dir: Path) -> Iterable[Path]:
    for candidate in sorted(fonts_dir.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in _FONT_SUFFIXES:
            yield candidate


def normalize_game_slug(value: str) -> str:
    return value.strip().casefold()


def allowed_gameplay_games(settings: Settings) -> set[str]:
    return set(settings.allowed_gameplay_games)


def gameplay_asset_game_slug(asset: AssetRecord) -> str | None:
    game = asset.metadata.get("game")
    if isinstance(game, str) and game.strip():
        return normalize_game_slug(game)

    path_parts = PurePosixPath(asset.path).parts
    if len(path_parts) >= 2 and path_parts[0] == "gameplay":
        return normalize_game_slug(path_parts[1])

    source_path = asset.metadata.get("source_path")
    if isinstance(source_path, str) and source_path:
        source_parts = PurePosixPath(source_path).parts
        if "clips" in source_parts:
            clips_index = source_parts.index("clips")
            if clips_index + 1 < len(source_parts):
                return normalize_game_slug(source_parts[clips_index + 1])

    return None


def filter_allowed_gameplay_assets(
    settings: Settings,
    assets: Iterable[AssetRecord],
) -> list[AssetRecord]:
    allowed_games = allowed_gameplay_games(settings)
    return [
        asset
        for asset in assets
        if asset.kind == AssetKind.GAMEPLAY
        and gameplay_asset_game_slug(asset) in allowed_games
    ]
