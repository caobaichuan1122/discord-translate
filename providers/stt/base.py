from abc import ABC, abstractmethod
import io

class BaseSTT(ABC):
    @abstractmethod
    async def transcribe(self, audio_file: io.BytesIO, source_lang: str = None) -> str:
        """Transcribe audio to text. Returns empty string if no speech detected."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
