from __future__ import annotations

import hashlib
from typing import Iterable

from brainrot_backend.core.models.domain import AssetRecord, ScriptDraft
from brainrot_backend.core.models.enums import AssetKind


class AssetSelector:
    def choose_gameplay(
        self,
        script: ScriptDraft,
        assets: list[AssetRecord],
        *,
        used_asset_ids: set[str] | None = None,
    ) -> AssetRecord:
        return self._choose(
            script,
            assets,
            script.gameplay_tags,
            AssetKind.GAMEPLAY,
            used_asset_ids=used_asset_ids,
        )

    def choose_music(
        self,
        script: ScriptDraft,
        assets: list[AssetRecord],
        *,
        used_asset_ids: set[str] | None = None,
    ) -> AssetRecord:
        return self._choose(
            script,
            assets,
            script.music_tags,
            AssetKind.MUSIC,
            used_asset_ids=used_asset_ids,
        )

    def _choose(
        self,
        script: ScriptDraft,
        assets: list[AssetRecord],
        desired_tags: list[str],
        expected_kind: AssetKind,
        *,
        used_asset_ids: set[str] | None = None,
    ) -> AssetRecord:
        matches = [asset for asset in assets if asset.kind == expected_kind]
        if not matches:
            raise RuntimeError(f"No {expected_kind.value} assets are available.")

        ranked = sorted(
            (
                (self._score(asset, desired_tags, script), asset)
                for asset in matches
            ),
            key=lambda item: (item[0], item[1].path),
            reverse=True,
        )
        available = [item for item in ranked if not used_asset_ids or item[1].id not in used_asset_ids] or ranked
        best_score = available[0][0]
        finalists = [asset for score, asset in available if score == best_score]
        if len(finalists) == 1:
            return finalists[0]

        seed = self._stable_seed(script, desired_tags, expected_kind)
        return finalists[seed % len(finalists)]

    @staticmethod
    def _score(asset: AssetRecord, desired_tags: list[str], script: ScriptDraft) -> tuple[int, int]:
        asset_tags = {tag.lower() for tag in asset.tags}
        desired = {tag.lower() for tag in desired_tags}
        overlap = len(asset_tags.intersection(desired))
        duration_fit = 1 if asset.metadata.get("duration_seconds", 0) >= script.estimated_seconds else 0
        return overlap, duration_fit

    @staticmethod
    def _stable_seed(script: ScriptDraft, desired_tags: list[str], expected_kind: AssetKind) -> int:
        payload = "|".join(
            [
                expected_kind.value,
                script.title,
                script.hook,
                ",".join(sorted(tag.lower() for tag in desired_tags)),
            ]
        ).encode("utf-8")
        return int(hashlib.sha256(payload).hexdigest()[:8], 16)
