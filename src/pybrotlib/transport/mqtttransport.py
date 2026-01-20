from typing import get_type_hints
from aiomqtt import Client, Message  # type: ignore

from .transport import Transport


class MQTTTransport(Transport):
    def __init__(self, host: str, port: int):
        super().__init__()

        self.host = host
        self.port = port

    def __str__(self) -> str:
        return f"MQTT(host={self.host}, port={self.port})"

    async def publish(self, topic: str, message: str) -> None:
        async with Client(self.host, self.port) as client:
            await client.publish(topic, payload=message.encode("utf-8"))

    async def run(self) -> None:
        async with Client(self.host, self.port) as client:
            self._connected = True
            await client.subscribe("#")
            async for message in client.messages:
                await self._process_message(message)

    async def _process_message(self, msg: Message) -> None:
        # Telemetry handling
        if "Telemetry" in msg.topic.value:
            # we only want bytes...
            if not isinstance(msg.payload, bytes):
                return

            # analyse message
            key, value = msg.payload.decode("utf-8").split(" ")[1].split("=")
            s = key.upper().split(".")
            obj = self.telemetry

            # dict with ALL telemetry
            self.data[key] = str(value)

            # find object in telemetry tree
            for token in s[:-1]:
                if hasattr(obj, token):
                    obj = getattr(obj, token)
                else:
                    print("Unknown variable:", key)
                    return

            # does it exist?
            val: bool | int | float | str
            if hasattr(obj, s[-1]):
                typ = get_type_hints(obj)[s[-1]]
                if typ == bool:
                    val = value.lower() == "true"
                elif typ == int:
                    val = int(value)
                elif typ == float:
                    val = float(value)
                else:
                    val = value
                setattr(obj, s[-1], val)

        if "Log" in msg.topic.value:
            await self._process_log(msg)
            pass
            # payload = str(msg.payload)[2:-2].split(' message="')
            # log_message = payload[1]
            # log_level = payload[0].split("level=")[1]
            # self.logMessageReceived.emit(log_level, log_message)

    async def _process_log(self, msg: Message) -> None: ...
