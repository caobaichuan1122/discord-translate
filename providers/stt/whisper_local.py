import asyncio
import io
import os
import tempfile
from .base import BaseSTT
import config
from logger import get_logger

log = get_logger("whisper_local")

# Known whisper hallucination phrases to filter out
HALLUCINATION_PHRASES = {
    "thank you for watching", "thank you", "thanks for watching",
    "please subscribe", "like and subscribe", "bye", "goodbye",
    "you", ".", "...", " ", ""
}

class WhisperLocalSTT(BaseSTT):
    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None:
            import whisper
            log.info(f"Loading Whisper model '{config.WHISPER_MODEL}' (first load may take a while)...")
            self._model = whisper.load_model(config.WHISPER_MODEL)
            log.info("Whisper model loaded.")
        return self._model

    async def transcribe(self, audio_file: io.BytesIO, source_lang: str = None) -> str:
        loop = asyncio.get_event_loop()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_file.read())
            tmp_path = tmp.name

        try:
            model = self._load_model()
            lang = None if (source_lang in (None, "auto")) else source_lang

            result = await loop.run_in_executor(
                None,
                lambda: model.transcribe(
                    tmp_path,
                    language=lang,
                    no_speech_threshold=0.6,
                    condition_on_previous_text=False,
                )
            )

            parts = []
            for seg in result.get("segments", []):
                if seg.get("no_speech_prob", 0) < 0.6:
                    text = seg["text"].strip()
                    if text.lower() not in HALLUCINATION_PHRASES:
                        parts.append(text)

            return " ".join(parts).strip()
        finally:
            os.unlink(tmp_path)

    @property
    def name(self) -> str:
        return f"Whisper Local ({config.WHISPER_MODEL})"
