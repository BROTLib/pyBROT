from PySide6.QtCore import QObject, Signal
from abc import ABCMeta, abstractmethod
from typing import Any

from BROTgui.telemetry import Telemetry


class Transport(QObject):
    logMessageReceived = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.data: dict[str, Any] = {}
        self.telemetry = Telemetry()
        self._connected = False

    @abstractmethod
    async def run(self):
        pass

    @abstractmethod
    async def publish(self, topic: str, message: str) -> None:
        pass

    @property
    def connected(self) -> bool:
        return self._connected
