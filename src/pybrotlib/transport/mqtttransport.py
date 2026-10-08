import asyncio
import logging
import time
from typing import get_type_hints

from aiomqtt import Client, Message, MqttError

from .transport import Transport

log = logging.getLogger(__name__)

_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 30.0


def _split_field(field: str) -> tuple[str, str] | None:
    """Split an Influx line-protocol field set into (key, value), dropping an optional trailing timestamp."""
    key, sep, rest = field.partition("=")
    if not sep or not key:
        return None
    if rest.startswith('"'):
        # quoted string: runs to the closing unescaped quote and may contain spaces
        i = 1
        while i < len(rest) and rest[i] != '"':
            i += 2 if rest[i] == "\\" else 1
        return key, rest[: i + 1]
    return key, rest.partition(" ")[0]


class MQTTTransport(Transport):
    def __init__(self, host: str, port: int) -> None:
        super().__init__()

        self.host = host
        self.port = port
        self._client: Client | None = None
        self._connected_event = asyncio.Event()

    def __str__(self) -> str:
        return f"MQTT(host={self.host}, port={self.port})"

    async def publish(self, topic: str, message: str) -> None:
        # reuse the persistent connection from run() instead of opening a fresh one per
        # call -- each connect/publish/disconnect cycle used to expose every command to
        # paho-mqtt's blocking (non-executor) socket send, which could stall the whole
        # event loop for several seconds on a slow/congested broker connection.
        await self._connected_event.wait()
        assert self._client is not None
        await self._client.publish(topic, payload=message.encode("utf-8"))

    async def run(self) -> None:
        backoff = _INITIAL_BACKOFF
        while not self._closing.is_set():
            try:
                async with Client(self.host, self.port) as client:
                    self._client = client
                    self._connected = True
                    self._connected_event.set()
                    backoff = _INITIAL_BACKOFF
                    await client.subscribe("#")
                    async for message in client.messages:
                        if self._closing.is_set():
                            return
                        self._last_message_at = time.monotonic()
                        try:
                            await self._process_message(message)
                        except Exception:
                            log.exception("Error processing message on %s.", message.topic.value)
                        # _process_message has no await -- yield here so a queued
                        # backlog can't starve every other task on this loop.
                        await asyncio.sleep(0)
            except MqttError as e:
                self._connected = False
                self._connected_event.clear()
                if self._closing.is_set():
                    return
                log.warning(
                    "MQTT connection to %s:%d lost (%s), reconnecting in %.1fs.",
                    self.host,
                    self.port,
                    e,
                    backoff,
                )
                try:
                    await asyncio.wait_for(self._closing.wait(), timeout=backoff)
                    return
                except TimeoutError:
                    pass
                backoff = min(backoff * 2, _MAX_BACKOFF)
            finally:
                self._connected = False
                self._connected_event.clear()

    async def _process_message(self, msg: Message) -> None:
        # Telemetry handling
        if "Telemetry" in msg.topic.value:
            # we only want bytes...
            if not isinstance(msg.payload, bytes):
                return

            # analyse message
            text = msg.payload.decode("utf-8", errors="replace")
            _, _, field = text.partition(" ")
            parsed = _split_field(field)
            if parsed is None:
                log.warning("Malformed telemetry on %s: %r", msg.topic.value, text)
                return
            key, value = parsed
            s = key.upper().split(".")
            obj = self.telemetry

            # dict with ALL telemetry
            self.data[key] = value

            # find object in telemetry tree
            for token in s[:-1]:
                is_list = False
                if "[" in token:
                    is_list = True
                    idx = int(token.split("[")[1].split("]")[0])
                    token = token.split("[")[0]
                if hasattr(obj, token):
                    obj = getattr(obj, token)
                    if is_list:
                        obj = obj[idx]
                else:
                    return

            # does it exist?
            val: bool | int | float | str
            if hasattr(obj, s[-1]):
                typ = get_type_hints(obj)[s[-1]]
                if typ is bool:
                    val = value.lower() == "true"
                elif typ is int:
                    val = int(value.removesuffix("i"))
                elif typ is float:
                    val = float(value.removesuffix("i"))
                else:
                    val = value.removeprefix('"').removesuffix('"')
                setattr(obj, s[-1], val)

        if "Log" in msg.topic.value:
            await self._process_log(msg)
            pass
            # payload = str(msg.payload)[2:-2].split(' message="')
            # log_message = payload[1]
            # log_level = payload[0].split("level=")[1]
            # self.logMessageReceived.emit(log_level, log_message)

    async def _process_log(self, msg: Message) -> None: ...
