from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @abstractmethod
    def fetch_network(self) -> dict:
        pass
