"""Async message queue for decoupled channel-agent communication."""

import asyncio
from collections import deque
from typing import Callable, Awaitable

import logging as logger

from nanobot.bus.events import InboundMessage, OutboundMessage


class AsyncQueue:
    """
    Minimal async queue compatible with MicroPython.
    
    MicroPython's asyncio lacks Queue, so we build one
    using asyncio.Event and collections.deque.
    """

    def __init__(self):
        self._queue = deque((), 100)
        self._event = asyncio.Event()

    async def put(self, item):
        """Put an item into the queue."""
        self._queue.append(item)
        self._event.set()

    async def get(self):
        """Remove and return an item. Blocks until one is available."""
        while not self._queue:
            self._event.clear()
            await self._event.wait()
        item = self._queue.popleft()
        if not self._queue:
            self._event.clear()
        return item

    def qsize(self) -> int:
        """Return the number of items in the queue."""
        return len(self._queue)


class MessageBus:
    """
    Async message bus that decouples chat channels from the agent core.
    
    Channels push messages to the inbound queue, and the agent processes
    them and pushes responses to the outbound queue.
    """
    
    def __init__(self):
        self.inbound = AsyncQueue()
        self.outbound = AsyncQueue()
        self._outbound_subscribers: dict[str, list[Callable[[OutboundMessage], Awaitable[None]]]] = {}
        self._running = False
    
    async def publish_inbound(self, msg: InboundMessage) -> None:
        """Publish a message from a channel to the agent."""
        await self.inbound.put(msg)
    
    async def consume_inbound(self) -> InboundMessage:
        """Consume the next inbound message (blocks until available)."""
        return await self.inbound.get()
    
    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """Publish a response from the agent to channels."""
        await self.outbound.put(msg)
    
    async def consume_outbound(self) -> OutboundMessage:
        """Consume the next outbound message (blocks until available)."""
        return await self.outbound.get()
    
    def subscribe_outbound(
        self, 
        channel: str, 
        callback: Callable[[OutboundMessage], Awaitable[None]]
    ) -> None:
        """Subscribe to outbound messages for a specific channel."""
        if channel not in self._outbound_subscribers:
            self._outbound_subscribers[channel] = []
        self._outbound_subscribers[channel].append(callback)
    
    async def dispatch_outbound(self) -> None:
        """
        Dispatch outbound messages to subscribed channels.
        Run this as a background task.
        """
        self._running = True
        while self._running:
            try:
                msg = await asyncio.wait_for(self.outbound.get(), timeout=1.0)
                subscribers = self._outbound_subscribers.get(msg.channel, [])
                for callback in subscribers:
                    try:
                        await callback(msg)
                    except Exception as e:
                        logger.error(f"Error dispatching to {msg.channel}: {e}")
            except asyncio.TimeoutError:
                continue
    
    def stop(self) -> None:
        """Stop the dispatcher loop."""
        self._running = False
    
    @property
    def inbound_size(self) -> int:
        """Number of pending inbound messages."""
        return self.inbound.qsize()
    
    @property
    def outbound_size(self) -> int:
        """Number of pending outbound messages."""
        return self.outbound.qsize()
