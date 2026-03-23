from __future__ import annotations

from dataclasses import dataclass

from brainrot_backend.config import Settings
from brainrot_backend.integrations.elevenlabs import ElevenLabsAgentsClient
from brainrot_backend.integrations.firecrawl import FirecrawlClient
from brainrot_backend.render.assets import AssetSelector
from brainrot_backend.render.ffmpeg import FFmpegRenderer
from brainrot_backend.services.agents import AgentService
from brainrot_backend.services.assets import AssetService
from brainrot_backend.services.batches import BatchService
from brainrot_backend.services.chats import ChatService
from brainrot_backend.services.events import EventBroker
from brainrot_backend.storage.base import BlobStore, Repository
from brainrot_backend.storage.memory import InMemoryRepository, LocalBlobStore
from brainrot_backend.storage.supabase import SupabaseBlobStore, SupabaseRepository
from brainrot_backend.workers.orchestrator import BatchOrchestrator


@dataclass
class ServiceContainer:
    settings: Settings
    repository: Repository
    blob_store: BlobStore
    events: EventBroker
    asset_service: AssetService
    agent_service: AgentService
    chat_service: ChatService
    batch_service: BatchService


def build_container(settings: Settings) -> ServiceContainer:
    settings.ensure_directories()
    if settings.supabase_enabled:
        repository = SupabaseRepository(
            settings.supabase_url or "",
            settings.supabase_service_role_key or "",
        )
        blob_store = SupabaseBlobStore(
            settings.supabase_url or "",
            settings.supabase_service_role_key or "",
            settings.supabase_public_url,
        )
    else:
        repository = InMemoryRepository()
        blob_store = LocalBlobStore(settings.data_dir)

    events = EventBroker(repository)
    firecrawl = FirecrawlClient(settings)
    chat_service = ChatService(repository=repository)
    agent_service = AgentService(
        settings=settings,
        repository=repository,
        blob_store=blob_store,
        events=events,
        elevenlabs=ElevenLabsAgentsClient(settings),
    )
    asset_service = AssetService(settings, repository, blob_store)
    orchestrator = BatchOrchestrator(
        settings=settings,
        repository=repository,
        blob_store=blob_store,
        events=events,
        firecrawl=firecrawl,
        agent_service=agent_service,
        chat_service=chat_service,
        asset_selector=AssetSelector(),
        renderer=FFmpegRenderer(settings),
    )
    batch_service = BatchService(
        settings=settings,
        repository=repository,
        blob_store=blob_store,
        events=events,
        orchestrator=orchestrator,
        chat_service=chat_service,
    )
    return ServiceContainer(
        settings=settings,
        repository=repository,
        blob_store=blob_store,
        events=events,
        asset_service=asset_service,
        agent_service=agent_service,
        chat_service=chat_service,
        batch_service=batch_service,
    )
