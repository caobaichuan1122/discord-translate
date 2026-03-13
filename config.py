from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()

class STTProvider(str, Enum):
    WHISPER_LOCAL = "whisper_local"    # Free: runs locally, no API key needed
    OPENAI_WHISPER = "openai_whisper"  # Paid: OpenAI Whisper API, faster

class TranslateProvider(str, Enum):
    GOOGLE_FREE = "google_free"   # Free: unofficial Google Translate, no key needed
    DEEPL = "deepl"               # Paid: DeepL API (has 500k chars/month free tier)
    OPENAI_GPT = "openai_gpt"     # Paid: GPT translation, most context-aware

# Discord
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# Provider selection
STT_PROVIDER = STTProvider(os.getenv("STT_PROVIDER", "whisper_local"))
TRANSLATE_PROVIDER = TranslateProvider(os.getenv("TRANSLATE_PROVIDER", "google_free"))

# Language settings
SOURCE_LANG: str = os.getenv("SOURCE_LANG", "auto")
TARGET_LANG: str = os.getenv("TARGET_LANG", "zh-CN")

# Whisper local settings
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")

# API Keys
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DEEPL_API_KEY: str = os.getenv("DEEPL_API_KEY", "")

# Recording
RECORDING_INTERVAL: int = int(os.getenv("RECORDING_INTERVAL", "5"))
MIN_AUDIO_SECONDS: float = float(os.getenv("MIN_AUDIO_SECONDS", "0.5"))
