from __future__ import annotations

import json
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from brainrot_backend.config import Settings

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class OpenAIStructuredClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def generate(
        self,
        response_model: type[StructuredModel],
        *,
        instructions: str,
        input_text: str,
        temperature: float = 0.2,
    ) -> StructuredModel:
        if self.client is None:
            raise RuntimeError("OpenAI API key is not configured.")

        response = await self.client.responses.parse(
            model=self.settings.openai_model,
            reasoning={"effort": self.settings.openai_reasoning_effort},
            instructions=instructions,
            input=input_text,
            text_format=response_model,
            temperature=temperature,
        )

        parsed = getattr(response, "output_parsed", None)
        if parsed is not None:
            return parsed

        output_text = getattr(response, "output_text", None)
        if output_text:
            return response_model.model_validate_json(output_text)

        data = getattr(response, "model_dump_json", None)
        if callable(data):
            return response_model.model_validate_json(data())

        raise RuntimeError("Unable to parse structured OpenAI response.")
