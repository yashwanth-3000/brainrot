from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator, Callable

from brainrot_backend.core.models.enums import BatchEventType
from brainrot_backend.core.storage.base import Repository


class EventBroker:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self._conditions: dict[str, asyncio.Condition] = defaultdict(asyncio.Condition)

    async def publish(
        self,
        batch_id: str,
        event_type: BatchEventType,
        payload: dict[str, object],
    ):
        event = await self.repository.append_event(batch_id, event_type, payload)
        condition = self._conditions[batch_id]
        async with condition:
            condition.notify_all()
        return event

    def publisher_for(self, batch_id: str) -> Callable[[BatchEventType, dict[str, object]], asyncio.Future]:
        async def _publisher(event_type: BatchEventType, payload: dict[str, object]):
            await self.publish(batch_id, event_type, payload)

        return _publisher

    async def stream(
        self,
        batch_id: str,
        *,
        after_sequence: int = 0,
    ) -> AsyncIterator[dict[str, str]]:
        last_sequence = after_sequence
        condition = self._conditions[batch_id]

        while True:
            events = await self.repository.list_batch_events(batch_id, after_sequence=last_sequence)
            if events:
                for event in events:
                    last_sequence = event.sequence
                    yield {
                        "id": str(event.sequence),
                        "event": event.event_type.value,
                        "data": json.dumps(
                            {
                                "sequence": event.sequence,
                                "type": event.event_type.value,
                                "payload": event.payload,
                                "created_at": event.created_at.isoformat(),
                            }
                        ),
                    }
                continue

            try:
                async with condition:
                    await asyncio.wait_for(condition.wait(), timeout=12)
            except TimeoutError:
                yield {"event": "ping", "data": "{}"}
