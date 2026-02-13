"""
litellm.completion — Core async chat completion implementation.

Sends OpenAI-compatible POST requests to /v1/chat/completions endpoints.
Works with any provider that exposes an OpenAI-compatible API, which includes
nearly all modern LLM providers (OpenAI, Anthropic via proxy, DeepSeek,
Gemini, Moonshot, MiniMax, DashScope, Zhipu, OpenRouter, AiHubMix, vLLM,
Groq, Ollama, etc.).

MicroPython compatibility notes:
  - Uses `urequests` (MicroPython) with fallback to `requests` (CPython).
  - No dependency on asyncio networking — uses sync HTTP under an async wrapper.
    This is intentional: MicroPython's asyncio has limited HTTP support,
    and most MCU workloads are single-threaded anyway.
  - If running on CPython, an optional aiohttp path can be enabled.
"""

import json

# --- HTTP client abstraction (MicroPython / CPython compatible) ---

_http_impl = None  # "urequests" | "requests" | "aiohttp"

try:
    import urequests as _requests_mod

    _http_impl = "urequests"
except ImportError:
    try:
        import requests as _requests_mod

        _http_impl = "requests"
    except ImportError:
        _requests_mod = None

# Optional: on CPython, prefer aiohttp for true async
_aiohttp = None
try:
    import aiohttp as _aiohttp
    _http_impl = _http_impl or "aiohttp"
except ImportError:
    pass

if _http_impl is None:
    raise ImportError(
        "litellm-micro requires one of: urequests (MicroPython), "
        "requests (CPython), or aiohttp (CPython async)"
    )

from litellm.types import (
    ModelResponse,
    Choices,
    Message,
    Usage,
    FunctionCall,
    ChatCompletionMessageToolCall,
)

# --- Provider endpoint resolution ---

# Known provider API base URLs, keyed by the litellm-style prefix.
# The prefix is stripped from the model name before sending to the API.
_PROVIDER_ENDPOINTS = {
    "openrouter":   "https://openrouter.ai/api/v1",
    "deepseek":     "https://api.deepseek.com",
    "gemini":       "https://generativelanguage.googleapis.com/v1beta/openai",
    "moonshot":     "https://api.moonshot.ai/v1",
    "dashscope":    "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "minimax":      "https://api.minimax.io/v1",
    "groq":         "https://api.groq.com/openai/v1",
    "hosted_vllm":  None,  # requires explicit api_base
    "zai":          "https://open.bigmodel.cn/api/paas/v4",
}

# Providers whose model names are natively recognized by their API
# (no prefix stripping needed when sending to the endpoint).
_NATIVE_PROVIDERS = {
    "openrouter",  # OpenRouter expects "anthropic/claude-3" as-is
}

# Default endpoints for non-prefixed models (matched by keyword).
_DEFAULT_ENDPOINTS = {
    "claude":  "https://api.anthropic.com/v1",
    "gpt":     "https://api.openai.com/v1",
    "o1":      "https://api.openai.com/v1",
    "o3":      "https://api.openai.com/v1",
    "o4":      "https://api.openai.com/v1",
}

# Anthropic models need special handling (non-OpenAI API format)
_ANTHROPIC_KEYWORDS = ("claude",)


def _resolve_endpoint_and_model(model, api_base=None):
    """
    Determine the API base URL and actual model name to send.
    
    Args:
        model: Model string, possibly prefixed like "deepseek/deepseek-chat"
        api_base: Explicit API base override
        
    Returns:
        (base_url, actual_model_name, is_anthropic)
    """
    import litellm as _litellm_mod

    is_anthropic = False

    # If api_base is explicitly provided, use it directly
    if api_base:
        # Still need to strip provider prefix from model name
        actual_model = model
        for prefix in _PROVIDER_ENDPOINTS:
            tag = prefix + "/"
            if model.startswith(tag) and prefix not in _NATIVE_PROVIDERS:
                actual_model = model[len(tag):]
                break
        return api_base.rstrip("/"), actual_model, is_anthropic

    # Check for provider prefix in model name
    for prefix, endpoint in _PROVIDER_ENDPOINTS.items():
        tag = prefix + "/"
        if model.startswith(tag):
            if endpoint is None:
                raise ValueError(
                    "Provider '{}' requires an explicit api_base".format(prefix)
                )
            actual_model = model if prefix in _NATIVE_PROVIDERS else model[len(tag):]
            return endpoint.rstrip("/"), actual_model, is_anthropic

    # No prefix — try to match by keyword in model name
    model_lower = model.lower()
    for keyword, endpoint in _DEFAULT_ENDPOINTS.items():
        if keyword in model_lower:
            # Check if this is an Anthropic model
            for ak in _ANTHROPIC_KEYWORDS:
                if ak in model_lower:
                    is_anthropic = True
                    break
            return endpoint.rstrip("/"), model, is_anthropic

    # Fallback: use global api_base or default to OpenAI
    fallback_base = getattr(_litellm_mod, "api_base", None) or "https://api.openai.com/v1"
    return fallback_base.rstrip("/"), model, is_anthropic


def _build_openai_payload(model, messages, **kwargs):
    """Build an OpenAI-compatible request payload."""
    payload = {
        "model": model,
        "messages": messages,
    }
    
    # Standard parameters
    for key in ("max_tokens", "temperature", "top_p", "frequency_penalty",
                "presence_penalty", "stop", "stream", "seed", "n"):
        if key in kwargs and kwargs[key] is not None:
            payload[key] = kwargs[key]

    # Tools (function calling)
    if "tools" in kwargs and kwargs["tools"]:
        payload["tools"] = kwargs["tools"]
        payload["tool_choice"] = kwargs.get("tool_choice", "auto")

    return payload


def _build_anthropic_payload(model, messages, **kwargs):
    """
    Build an Anthropic Messages API payload.
    
    Converts OpenAI-style messages to Anthropic format:
      - Extracts 'system' messages into top-level 'system' field
      - Maps role names appropriately
    """
    system_parts = []
    api_messages = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append(content)
        else:
            api_messages.append({"role": role, "content": content})

    payload = {
        "model": model,
        "messages": api_messages,
        "max_tokens": kwargs.get("max_tokens", 4096),
    }

    if system_parts:
        payload["system"] = "\n\n".join(system_parts)

    if "temperature" in kwargs:
        payload["temperature"] = kwargs["temperature"]

    # Anthropic tool use
    if "tools" in kwargs and kwargs["tools"]:
        anthropic_tools = []
        for tool in kwargs["tools"]:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                })
        if anthropic_tools:
            payload["tools"] = anthropic_tools

    return payload


def _parse_anthropic_response(data):
    """
    Convert Anthropic Messages API response to OpenAI-compatible ModelResponse.
    """
    content_text = None
    tool_calls = []
    reasoning_content = None
    tc_index = 0

    for block in data.get("content", []):
        btype = block.get("type", "")
        if btype == "text":
            content_text = block.get("text", "")
        elif btype == "thinking":
            reasoning_content = block.get("thinking", "")
        elif btype == "tool_use":
            tool_calls.append(
                ChatCompletionMessageToolCall(
                    id=block.get("id", "call_{}".format(tc_index)),
                    type="function",
                    function=FunctionCall(
                        name=block.get("name", ""),
                        arguments=(
                            json.dumps(block["input"])
                            if isinstance(block.get("input"), dict)
                            else str(block.get("input", "{}"))
                        ),
                    ),
                )
            )
            tc_index += 1

    message = Message(
        role="assistant",
        content=content_text,
        tool_calls=tool_calls if tool_calls else None,
        reasoning_content=reasoning_content,
    )

    usage_data = data.get("usage", {})
    usage = Usage(
        prompt_tokens=usage_data.get("input_tokens", 0),
        completion_tokens=usage_data.get("output_tokens", 0),
        total_tokens=(
            usage_data.get("input_tokens", 0)
            + usage_data.get("output_tokens", 0)
        ),
    )

    finish_reason_map = {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "tool_use": "tool_calls",
        "max_tokens": "length",
    }
    raw_stop = data.get("stop_reason", "end_turn")
    finish_reason = finish_reason_map.get(raw_stop, raw_stop)

    return ModelResponse(
        id=data.get("id", ""),
        choices=[Choices(finish_reason=finish_reason, index=0, message=message)],
        created=0,
        model=data.get("model", ""),
        usage=usage,
    )


def _parse_openai_response(data):
    """Parse a standard OpenAI-compatible JSON response into ModelResponse."""
    choices_raw = data.get("choices", [])
    choices = []
    for i, c in enumerate(choices_raw):
        msg_raw = c.get("message", {})

        # Parse tool calls
        tc_list = None
        raw_tcs = msg_raw.get("tool_calls")
        if raw_tcs:
            tc_list = []
            for tc in raw_tcs:
                func = tc.get("function", {})
                tc_list.append(
                    ChatCompletionMessageToolCall(
                        id=tc.get("id", ""),
                        type=tc.get("type", "function"),
                        function=FunctionCall(
                            name=func.get("name", ""),
                            arguments=func.get("arguments", "{}"),
                        ),
                    )
                )

        message = Message(
            role=msg_raw.get("role", "assistant"),
            content=msg_raw.get("content"),
            tool_calls=tc_list,
            reasoning_content=msg_raw.get("reasoning_content"),
        )
        choices.append(
            Choices(
                finish_reason=c.get("finish_reason", "stop"),
                index=c.get("index", i),
                message=message,
            )
        )

    usage_raw = data.get("usage") or {}
    usage = Usage(
        prompt_tokens=usage_raw.get("prompt_tokens", 0),
        completion_tokens=usage_raw.get("completion_tokens", 0),
        total_tokens=usage_raw.get("total_tokens", 0),
    )

    return ModelResponse(
        id=data.get("id", ""),
        choices=choices,
        created=data.get("created", 0),
        model=data.get("model", ""),
        usage=usage,
    )


def _sync_post(url, headers, payload, timeout=120):
    """
    Perform a synchronous HTTP POST using urequests or requests.

    Returns parsed JSON dict.
    """
    body = json.dumps(payload).encode("utf-8")

    if _http_impl == "urequests":
        resp = _requests_mod.post(
            url,
            headers=headers,
            data=body,
            # urequests may not support timeout on all ports
        )
        status = resp.status_code
        text = resp.text
        resp.close()
    else:
        resp = _requests_mod.post(
            url,
            headers=headers,
            data=body,
            timeout=timeout,
        )
        status = resp.status_code
        text = resp.text

    if status >= 400:
        raise Exception(
            "HTTP {} from {}: {}".format(status, url, text[:500])
        )

    return json.loads(text)


async def _aiohttp_post(url, headers, payload, timeout=120):
    """Perform an async HTTP POST using aiohttp (CPython only)."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise Exception(
                    "HTTP {} from {}: {}".format(resp.status, url, text[:500])
                )
            return json.loads(text)


async def acompletion(
    model,
    messages,
    api_key=None,
    api_base=None,
    max_tokens=4096,
    temperature=0.7,
    tools=None,
    tool_choice=None,
    extra_headers=None,
    timeout=120,
    **kwargs
):
    """
    Async chat completion — drop-in replacement for litellm.acompletion().
    
    Sends an OpenAI-compatible (or Anthropic-native) chat completion request
    and returns a ModelResponse with the same attribute-access interface as
    the real litellm library.
    
    On MicroPython, the HTTP call is synchronous (via urequests) wrapped in
    an async function for API compatibility. On CPython with aiohttp
    installed, true async I/O is used.
    
    Args:
        model:      Model identifier, optionally prefixed (e.g. "deepseek/deepseek-chat").
        messages:   List of message dicts [{"role": "user", "content": "..."}].
        api_key:    API key for authentication.
        api_base:   Override the API endpoint base URL.
        max_tokens: Maximum tokens in the completion.
        temperature: Sampling temperature.
        tools:      Tool definitions in OpenAI format.
        tool_choice: Tool choice strategy ("auto", "none", etc.).
        extra_headers: Additional HTTP headers dict.
        timeout:    Request timeout in seconds.
        **kwargs:   Additional parameters forwarded to the API.
        
    Returns:
        ModelResponse compatible with litellm's response format.
        
    Raises:
        Exception: On HTTP errors (4xx/5xx) from the API.
        ValueError: If required configuration is missing.
    """
    base_url, actual_model, is_anthropic = _resolve_endpoint_and_model(
        model, api_base
    )

    if is_anthropic and not api_base:
        # --- Anthropic Messages API path ---
        url = base_url + "/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
        }
        if extra_headers:
            headers.update(extra_headers)

        payload = _build_anthropic_payload(
            actual_model, messages,
            max_tokens=max_tokens, temperature=temperature,
            tools=tools, **kwargs
        )

        if _aiohttp and _http_impl != "urequests":
            data = await _aiohttp_post(url, headers, payload, timeout)
        else:
            data = _sync_post(url, headers, payload, timeout)

        return _parse_anthropic_response(data)

    else:
        # --- OpenAI-compatible path (covers most providers) ---
        url = base_url + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = "Bearer " + api_key
        if extra_headers:
            headers.update(extra_headers)

        payload = _build_openai_payload(
            actual_model, messages,
            max_tokens=max_tokens, temperature=temperature,
            tools=tools, tool_choice=tool_choice,
            **kwargs
        )

        if _aiohttp and _http_impl != "urequests":
            data = await _aiohttp_post(url, headers, payload, timeout)
        else:
            data = _sync_post(url, headers, payload, timeout)

        return _parse_openai_response(data)