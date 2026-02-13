"""
litellm.types — Response data types compatible with the real litellm library.

These classes mirror the attribute-access patterns used by litellm_provider.py:
  - response.choices[0].message.content
  - response.choices[0].message.tool_calls[i].id
  - response.choices[0].message.tool_calls[i].function.name
  - response.choices[0].message.tool_calls[i].function.arguments
  - response.choices[0].finish_reason
  - response.usage.prompt_tokens / completion_tokens / total_tokens
  - message.reasoning_content  (DeepSeek-R1, Kimi, etc.)
"""


class FunctionCall:
    """Represents a function call within a tool call."""

    __slots__ = ("name", "arguments")

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def __repr__(self):
        return "FunctionCall(name={!r}, arguments={!r})".format(
            self.name, self.arguments
        )


class ChatCompletionMessageToolCall:
    """Represents a single tool call returned by the model."""

    __slots__ = ("id", "type", "function")

    def __init__(self, id, type, function):
        self.id = id
        self.type = type
        self.function = function

    def __repr__(self):
        return "ChatCompletionMessageToolCall(id={!r}, type={!r}, function={!r})".format(
            self.id, self.type, self.function
        )


class Message:
    """Represents the assistant's response message."""

    __slots__ = ("role", "content", "tool_calls", "reasoning_content")

    def __init__(self, role, content, tool_calls=None, reasoning_content=None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.reasoning_content = reasoning_content

    def __repr__(self):
        return "Message(role={!r}, content={!r}, tool_calls={!r})".format(
            self.role,
            self.content[:60] if self.content else None,
            self.tool_calls,
        )


class Choices:
    """Represents a single choice in the response."""

    __slots__ = ("finish_reason", "index", "message")

    def __init__(self, finish_reason, index, message):
        self.finish_reason = finish_reason
        self.index = index
        self.message = message

    def __repr__(self):
        return "Choices(finish_reason={!r}, index={})".format(
            self.finish_reason, self.index
        )


class Usage:
    """Token usage statistics."""

    __slots__ = ("prompt_tokens", "completion_tokens", "total_tokens")

    def __init__(self, prompt_tokens=0, completion_tokens=0, total_tokens=0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def __repr__(self):
        return "Usage(prompt={}, completion={}, total={})".format(
            self.prompt_tokens, self.completion_tokens, self.total_tokens
        )


class ModelResponse:
    """
    Top-level response object returned by acompletion().
    
    Compatible with the attribute access patterns used in litellm_provider.py:
        response.choices[0].message.content
        response.choices[0].finish_reason
        response.usage.prompt_tokens
    """

    __slots__ = ("id", "choices", "created", "model", "usage", "object")

    def __init__(self, id, choices, created, model, usage, object="chat.completion"):
        self.id = id
        self.choices = choices
        self.created = created
        self.model = model
        self.usage = usage
        self.object = object

    def __repr__(self):
        return "ModelResponse(id={!r}, model={!r}, choices={})".format(
            self.id, self.model, len(self.choices)
        )