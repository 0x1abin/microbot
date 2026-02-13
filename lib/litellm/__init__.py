"""
litellm — MicroPython-compatible lightweight replacement.

A minimal implementation of the litellm interface, providing just enough
functionality to satisfy the nanobot LiteLLMProvider module.

Designed for MicroPython environments where the full litellm package
(and its heavy dependencies like httpx, openai, etc.) cannot run.

Supports any OpenAI-compatible chat completions endpoint, which covers:
  - OpenAI, Anthropic (via proxy), DeepSeek, Gemini, Moonshot, MiniMax,
    DashScope, Zhipu, OpenRouter, AiHubMix, vLLM, Groq, Ollama, etc.
"""

from litellm.completion import acompletion
from litellm.types import (
    ModelResponse,
    Choices,
    Message,
    Usage,
    FunctionCall,
    ChatCompletionMessageToolCall,
)

# Global configuration attributes (mirrors real litellm interface)
api_base = None
suppress_debug_info = False
drop_params = False

__all__ = [
    "acompletion",
    "ModelResponse",
    "Choices",
    "Message",
    "Usage",
    "FunctionCall",
    "ChatCompletionMessageToolCall",
    "api_base",
    "suppress_debug_info",
    "drop_params",
]