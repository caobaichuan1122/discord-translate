import asyncio
import io
from .base import BaseSTT
import config

class OpenAIWhisperSTT(BaseSTT):
    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI Whisper STT")
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    async def transcribe(self, audio_file: io.BytesIO, source_lang: str = None) -> str:
        audio_file.seek(0)
        # OpenAI API requires a named file-like object
        audio_file.name = "audio.wav"

        kwargs = {"model": "whisper-1", "file": audio_file}
        if source_lang and source_lang != "auto":
            kwargs["language"] = source_lang

        response = await self._client.audio.transcriptions.create(**kwargs)
        return response.text.strip()

    @property
    def name(self) -> str:
        return "OpenAI Whisper API"
