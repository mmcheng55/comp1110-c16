from abc import ABC, abstractmethod

class BaseFareProvider(ABC):
    @abstractmethod
    def fetch_fares(self) -> dict:
        pass

