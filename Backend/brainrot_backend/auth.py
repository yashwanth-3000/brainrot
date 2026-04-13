from __future__ import annotations

from dataclasses import dataclass

import httpx

from brainrot_backend.config import Settings
from brainrot_backend.core.models.enums import ChatLibraryScope


class AuthConfigurationError(RuntimeError):
    """Raised when authenticated requests arrive but Supabase auth is unavailable."""


class AuthenticationError(RuntimeError):
    """Raised when a Supabase bearer token is invalid."""


@dataclass(frozen=True)
class RequestAuthContext:
    user_id: str | None = None
    email: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return bool(self.user_id)

    @property
    def library_scope(self) -> ChatLibraryScope:
        return ChatLibraryScope.USER if self.is_authenticated else ChatLibraryScope.GENERAL


class SupabaseAuthService:
    def __init__(self, settings: Settings) -> None:
        self.supabase_url = (settings.supabase_url or "").rstrip("/")
        self.service_role_key = settings.supabase_service_role_key or ""

    async def resolve_request(self, authorization: str | None) -> RequestAuthContext:
        token = self._extract_bearer_token(authorization)
        if not token:
            return RequestAuthContext()
        if not self.supabase_url or not self.service_role_key:
            raise AuthConfigurationError("Supabase auth is not configured on the backend.")

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            response = await client.get(
                f"{self.supabase_url}/auth/v1/user",
                headers={
                    "apikey": self.service_role_key,
                    "Authorization": f"Bearer {token}",
                },
            )

        if response.status_code in {401, 403}:
            raise AuthenticationError("Invalid Supabase session.")
        response.raise_for_status()

        payload = response.json()
        user_id = str(payload.get("id") or "").strip()
        if not user_id:
            raise AuthenticationError("Supabase session did not include a user id.")

        email = str(payload.get("email") or "").strip() or None
        return RequestAuthContext(user_id=user_id, email=email)

    def _extract_bearer_token(self, authorization: str | None) -> str | None:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer":
            return None
        resolved = token.strip()
        return resolved or None
