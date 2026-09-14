import asyncio

import pytest
from aiomqtt import MqttError

from pybrotlib.transport import mqtttransport as mqtt_module
from pybrotlib.transport.mqtttransport import MQTTTransport


class _FakeMessages:
    """Async message iterator that raises MqttError once `drop` is set, or ends cleanly once
    the transport is closing -- mimicking aiomqtt.Client.messages under a dropped connection.
    """

    def __init__(self, transport: MQTTTransport, drop: asyncio.Event) -> None:
        self._transport = transport
        self._drop = drop

    def __aiter__(self) -> "_FakeMessages":
        return self

    async def __anext__(self) -> object:
        drop_wait = asyncio.ensure_future(self._drop.wait())
        closing_wait = asyncio.ensure_future(self._transport._closing.wait())
        try:
            await asyncio.wait(
                [drop_wait, closing_wait], return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            drop_wait.cancel()
            closing_wait.cancel()
        if self._transport._closing.is_set():
            raise StopAsyncIteration
        raise MqttError("connection lost")


class _FakeClient:
    def __init__(
        self,
        transport: MQTTTransport,
        fail_connect: bool,
        drop: asyncio.Event,
        published: list[tuple[str, bytes]],
    ) -> None:
        self._transport = transport
        self._fail_connect = fail_connect
        self._drop = drop
        self._published = published

    async def __aenter__(self) -> "_FakeClient":
        if self._fail_connect:
            raise MqttError("connect failed")
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def subscribe(self, topic: str) -> None:
        return None

    async def publish(self, topic: str, payload: bytes) -> None:
        self._published.append((topic, payload))

    @property
    def messages(self) -> _FakeMessages:
        return _FakeMessages(self._transport, self._drop)


async def test_run_retries_after_connect_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mqtt_module, "_INITIAL_BACKOFF", 0.01)
    monkeypatch.setattr(mqtt_module, "_MAX_BACKOFF", 0.01)

    transport = MQTTTransport(host="localhost", port=1883)
    published: list[tuple[str, bytes]] = []
    attempts: list[bool] = []
    drop_events = [asyncio.Event(), asyncio.Event()]

    def fake_client(host: str, port: int) -> _FakeClient:
        fail = len(attempts) == 0
        attempts.append(fail)
        return _FakeClient(
            transport,
            fail_connect=fail,
            drop=drop_events[len(attempts) - 1],
            published=published,
        )

    monkeypatch.setattr(mqtt_module, "Client", fake_client)

    assert transport.connected is False
    task = asyncio.create_task(transport.run())

    await asyncio.wait_for(transport._connected_event.wait(), timeout=1)
    assert transport.connected is True
    assert attempts == [True, False]

    await transport.close()
    await asyncio.wait_for(task, timeout=1)
    assert transport.connected is False


async def test_publish_blocks_across_disconnect_and_reconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mqtt_module, "_INITIAL_BACKOFF", 0.01)
    monkeypatch.setattr(mqtt_module, "_MAX_BACKOFF", 0.01)

    transport = MQTTTransport(host="localhost", port=1883)
    published: list[tuple[str, bytes]] = []
    drop_events = [asyncio.Event(), asyncio.Event()]
    attempt = 0

    def fake_client(host: str, port: int) -> _FakeClient:
        nonlocal attempt
        client = _FakeClient(
            transport,
            fail_connect=False,
            drop=drop_events[attempt],
            published=published,
        )
        attempt += 1
        return client

    monkeypatch.setattr(mqtt_module, "Client", fake_client)

    task = asyncio.create_task(transport.run())
    await asyncio.wait_for(transport._connected_event.wait(), timeout=1)
    assert transport.connected is True

    # simulate the broker connection dropping
    drop_events[0].set()
    for _ in range(1000):
        if not transport.connected:
            break
        await asyncio.sleep(0)
    assert transport.connected is False
    assert not transport._connected_event.is_set()

    publish_task = asyncio.create_task(transport.publish("brot/x", "cmd"))
    await asyncio.sleep(0)
    assert not publish_task.done()

    await asyncio.wait_for(transport._connected_event.wait(), timeout=1)
    await asyncio.wait_for(publish_task, timeout=1)
    assert published == [("brot/x", b"cmd")]

    await transport.close()
    await asyncio.wait_for(task, timeout=1)
