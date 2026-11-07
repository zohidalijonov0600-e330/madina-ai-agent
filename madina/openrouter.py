from __future__ import annotations

import json
import os
from typing import Any

import httpx

from madina.config import settings


class OpenRouterClient:
    def __init__(self) -> None:
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = settings.openrouter_api_key
        self.model = settings.gemini_model
        self.stt_model = settings.stt_model
        self.tts_model = settings.tts_model

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/zohidalijonov0600-e330/madina-ai-agent",
            "X-Title": "Madina AI Agent",
        }

    async def check_api(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def generate_chat_completion(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._build_headers(),
                json=payload,
            )
            if response.status_code >= 400:
                detail = response.text
                raise RuntimeError(f"OpenRouter chat completion failed: {detail}")
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def transcribe_audio(self, file_path: str, language: str = "uz") -> str:
        with open(file_path, "rb") as audio_file:
            form = {"file": (os.path.basename(file_path), audio_file, "audio/ogg")}
            data = {"model": self.stt_model, "language": language}
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=form,
                    data=data,
                )
                if response.status_code >= 400:
                    raise RuntimeError(f"STT failed: {response.text}")
                payload = response.json()
                return payload.get("text") or payload.get("transcript") or ""

    async def text_to_speech(self, text: str) -> bytes:
        payload = {
            "model": self.tts_model,
            "input": text,
            "voice": "alloy",
            "response_format": "mp3",
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.base_url}/audio/speech",
                headers=self._build_headers(),
                json=payload,
            )
            if response.status_code >= 400:
                raise RuntimeError(f"TTS failed: {response.text}")
            return response.content
