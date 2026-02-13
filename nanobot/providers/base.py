"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Any


class ToolCallRequest:
    """A tool call request from the LLM."""

    __slots__ = ("id", "name", "arguments")

    def __init__(self, id: str, name: str, arguments: dict):
        self.id = id
        self.name = name
        self.arguments = arguments


class LLMResponse:
    """Response from an LLM provider."""

    __slots__ = ("content", "tool_calls", "finish_reason", "usage", "reasoning_content")

    def __init__(
        self,
        content: str | None,
        tool_calls: list | None = None,
        finish_reason: str = "stop",
        usage: dict | None = None,
        reasoning_content: str | None = None,
    ):
        self.content = content
        self.tool_calls = list(tool_calls) if tool_calls is not None else []
        self.finish_reason = finish_reason
        self.usage = dict(usage) if usage is not None else {}
        self.reasoning_content = reasoning_content

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Implementations should handle the specifics of each provider's API
    while maintaining a consistent interface.
    """
    
    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        self.api_key = api_key
        self.api_base = api_base
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions.
            model: Model identifier (provider-specific).
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
        
        Returns:
            LLMResponse with content and/or tool calls.
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        pass
