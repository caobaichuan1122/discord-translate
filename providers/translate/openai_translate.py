from .base import BaseTranslator
import config

LANG_NAMES = {
    "zh": "Chinese", "en": "English", "ja": "Japanese", "ko": "Korean",
    "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
    "pt": "Portuguese", "ru": "Russian", "auto": "the detected language"
}

class OpenAITranslator(BaseTranslator):
    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI GPT translation")
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    async def translate(self, text: str, source_lang: str = "auto", target_lang: str = None) -> str:
        if not text.strip():
            return ""
        target = target_lang or config.TARGET_LANG
        target_name = LANG_NAMES.get(target, target)

        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a translator. Translate the user's text to {target_name}. Output only the translation, nothing else."
                },
                {"role": "user", "content": text}
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()

    @property
    def name(self) -> str:
        return "OpenAI GPT Translation"
