"""Tests for the EventBus."""

import asyncio

import pytest

from nexus.core.event_bus import EventBus
from nexus.core.events import Event, UserMessageEvent


@pytest.fixture
async def bus():
    b = EventBus()
    await b.start()
    yield b
    await b.stop()


class TestEventBus:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        bus = EventBus()
        assert not bus.is_running
        await bus.start()
        assert bus.is_running
        await bus.stop()
        assert not bus.is_running

    @pytest.mark.asyncio
    async def test_publish_subscribe(self, bus):
        received = []

        async def handler(event: UserMessageEvent):
            received.append(event.content)

        bus.subscribe(UserMessageEvent, handler)
        await bus.publish(
            UserMessageEvent(content="hello", session_id="test", interface="test")
        )

        # Give event loop time to process
        await asyncio.sleep(0.1)
        assert received == ["hello"]

    @pytest.mark.asyncio
    async def test_multiple_handlers(self, bus):
        calls = []

        async def h1(event: Event):
            calls.append("h1")

        async def h2(event: Event):
            calls.append("h2")

        bus.subscribe(Event, h1)
        bus.subscribe(Event, h2)

        await bus.publish(Event())
        await asyncio.sleep(0.1)
        assert "h1" in calls
        assert "h2" in calls

    @pytest.mark.asyncio
    async def test_decorator_subscribe(self, bus):
        received = []

        @bus.on(UserMessageEvent)
        async def handler(event: UserMessageEvent):
            received.append(event.content)

        await bus.publish(
            UserMessageEvent(content="decorated", session_id="t", interface="t")
        )
        await asyncio.sleep(0.1)
        assert received == ["decorated"]

    @pytest.mark.asyncio
    async def test_handler_error_doesnt_crash(self, bus):
        """A failing handler should not stop the bus."""
        calls = []

        async def bad_handler(event: Event):
            raise ValueError("boom")

        async def good_handler(event: Event):
            calls.append("ok")

        bus.subscribe(Event, bad_handler)
        bus.subscribe(Event, good_handler)

        await bus.publish(Event())
        await asyncio.sleep(0.1)
        assert calls == ["ok"]
