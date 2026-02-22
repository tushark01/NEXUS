"""NEXUS async event bus — the nervous system of the framework."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, TypeVar

from nexus.core.events import Event

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Event)
EventHandler = Callable[[Any], Awaitable[None]]


class EventBus:
    """In-process async pub/sub event bus with typed subscriptions."""

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task[None] | None = None

    def subscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    def on(self, event_type: type[E]) -> Callable[[Callable[[E], Awaitable[None]]], Callable[[E], Awaitable[None]]]:
        """Decorator form of subscribe."""

        def decorator(func: Callable[[E], Awaitable[None]]) -> Callable[[E], Awaitable[None]]:
            self.subscribe(event_type, func)
            return func

        return decorator

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers (non-blocking enqueue)."""
        await self._queue.put(event)

    def publish_nowait(self, event: Event) -> None:
        """Publish without awaiting — for use from sync code."""
        self._queue.put_nowait(event)

    async def _process(self) -> None:
        """Main event processing loop."""
        self._running = True
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            event_type = type(event)
            handlers = self._handlers.get(event_type, [])

            # Also dispatch to handlers subscribed to base Event type
            if event_type is not Event:
                handlers = handlers + self._handlers.get(Event, [])

            for handler in handlers:
                try:
                    await handler(event)
                except Exception:
                    logger.exception("Event handler error for %s", event_type.__name__)

    async def start(self) -> None:
        """Start the event processing loop as a background task."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._process())

    async def stop(self) -> None:
        """Graceful shutdown — process remaining events then stop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    @property
    def is_running(self) -> bool:
        return self._running
