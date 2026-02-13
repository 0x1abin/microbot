"""Event types for the message bus."""

from datetime import datetime
from typing import Any


class InboundMessage:
    """Message received from a chat channel."""

    __slots__ = ("channel", "sender_id", "chat_id", "content", "timestamp", "media", "metadata")

    def __init__(
        self,
        channel: str,
        sender_id: str,
        chat_id: str,
        content: str,
        timestamp: datetime | None = None,
        media: list | None = None,
        metadata: dict | None = None,
    ):
        self.channel = channel
        self.sender_id = sender_id
        self.chat_id = chat_id
        self.content = content
        self.timestamp = datetime.now() if timestamp is None else timestamp
        self.media = list(media) if media is not None else []
        self.metadata = dict(metadata) if metadata is not None else {}

    @property
    def session_key(self) -> str:
        """Unique key for session identification."""
        return f"{self.channel}:{self.chat_id}"


class OutboundMessage:
    """Message to send to a chat channel."""

    __slots__ = ("channel", "chat_id", "content", "reply_to", "media", "metadata")

    def __init__(
        self,
        channel: str,
        chat_id: str,
        content: str,
        reply_to: str | None = None,
        media: list | None = None,
        metadata: dict | None = None,
    ):
        self.channel = channel
        self.chat_id = chat_id
        self.content = content
        self.reply_to = reply_to
        self.media = list(media) if media is not None else []
        self.metadata = dict(metadata) if metadata is not None else {}
