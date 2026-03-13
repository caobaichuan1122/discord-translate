from abc import ABC, abstractmethod

class BaseTranslator(ABC):
    @abstractmethod
    async def translate(self, text: str, source_lang: str = "auto", target_lang: str = None) -> str:
        """Translate text. Returns translated string."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
