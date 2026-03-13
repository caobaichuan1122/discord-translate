import asyncio
from .base import BaseTranslator
import config

class GoogleFreeTranslator(BaseTranslator):
    async def translate(self, text: str, source_lang: str = "auto", target_lang: str = None) -> str:
        if not text.strip():
            return ""
        from deep_translator import GoogleTranslator
        target = target_lang or config.TARGET_LANG
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: GoogleTranslator(source="auto", target=target).translate(text)
        )
        return result or ""

    @property
    def name(self) -> str:
        return "Google Translate (Free)"
