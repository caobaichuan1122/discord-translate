import asyncio
from .base import BaseTranslator
import config

# DeepL language code mapping (DeepL uses different codes than Google)
DEEPL_LANG_MAP = {
    "zh": "ZH", "en": "EN-US", "ja": "JA", "ko": "KO",
    "fr": "FR", "de": "DE", "es": "ES", "it": "IT",
    "pt": "PT-BR", "ru": "RU", "pl": "PL", "nl": "NL",
}

class DeepLTranslator(BaseTranslator):
    def __init__(self):
        if not config.DEEPL_API_KEY:
            raise ValueError("DEEPL_API_KEY is required for DeepL translation")
        import deepl
        self._translator = deepl.Translator(config.DEEPL_API_KEY)

    async def translate(self, text: str, source_lang: str = "auto", target_lang: str = None) -> str:
        if not text.strip():
            return ""
        target = target_lang or config.TARGET_LANG
        deepl_target = DEEPL_LANG_MAP.get(target.lower(), target.upper())
        deepl_source = None if source_lang == "auto" else source_lang.upper()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._translator.translate_text(text, source_lang=deepl_source, target_lang=deepl_target)
        )
        return result.text

    @property
    def name(self) -> str:
        return "DeepL API"
