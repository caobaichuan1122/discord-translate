import config
from config import STTProvider, TranslateProvider

def get_stt_provider():
    if config.STT_PROVIDER == STTProvider.WHISPER_LOCAL:
        from .stt.whisper_local import WhisperLocalSTT
        return WhisperLocalSTT()
    elif config.STT_PROVIDER == STTProvider.OPENAI_WHISPER:
        from .stt.openai_stt import OpenAIWhisperSTT
        return OpenAIWhisperSTT()
    raise ValueError(f"Unknown STT provider: {config.STT_PROVIDER}")

def get_translate_provider():
    if config.TRANSLATE_PROVIDER == TranslateProvider.GOOGLE_FREE:
        from .translate.google_free import GoogleFreeTranslator
        return GoogleFreeTranslator()
    elif config.TRANSLATE_PROVIDER == TranslateProvider.DEEPL:
        from .translate.deepl_provider import DeepLTranslator
        return DeepLTranslator()
    elif config.TRANSLATE_PROVIDER == TranslateProvider.OPENAI_GPT:
        from .translate.openai_translate import OpenAITranslator
        return OpenAITranslator()
    raise ValueError(f"Unknown translate provider: {config.TRANSLATE_PROVIDER}")
