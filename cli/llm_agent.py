"""LLM agent with tool-calling loop — Anthropic and OpenAI providers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from cli.mcp_client import MCPClient

SYSTEM_PROMPT = (
    "You are a vehicle safety research assistant with access to NHTSA data. "
    "Use the provided tools to answer questions. Always cite NHTSA as the data source. "
    "Do not speculate beyond what the tools return."
)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


class LLMProvider(ABC):
    @abstractmethod
    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
    ) -> tuple[str | None, list[ToolCall]]:
        """Return (text_response, tool_calls)."""
        ...


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
    ) -> tuple[str | None, list[ToolCall]]:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tools,
        )
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
        text = "\n".join(text_parts) if text_parts else None
        return text, tool_calls


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        import openai

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
    ) -> tuple[str | None, list[ToolCall]]:
        # Convert Anthropic tool format to OpenAI function format
        openai_tools = []
        for t in tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("inputSchema", t.get("input_schema", {})),
                    },
                }
            )

        all_messages = [{"role": "system", "content": system}, *messages]
        response = self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            tools=openai_tools if openai_tools else None,
        )
        choice = response.choices[0]
        text = choice.message.content
        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )
        return text, tool_calls


def get_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model_openai,
        )
    return AnthropicProvider(
        api_key=settings.anthropic_api_key,
        model=settings.llm_model_anthropic,
    )


def run_agent(
    question: str,
    mcp_client: MCPClient,
    provider: LLMProvider,
    max_iterations: int = 10,
) -> str:
    """Run the tool-calling agent loop. Returns final text answer."""
    # Get available tools
    tools_raw = mcp_client.list_tools()
    allowed_tool_names = {t["name"] for t in tools_raw}

    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]

    for _iteration in range(max_iterations):
        text, tool_calls = provider.complete_with_tools(messages, tools_raw, SYSTEM_PROMPT)

        if not tool_calls:
            return text or "(No response from model)"

        # Build assistant message with tool use
        assistant_content: list[dict[str, Any]] = []
        if text:
            assistant_content.append({"type": "text", "text": text})
        for tc in tool_calls:
            assistant_content.append(
                {
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                }
            )
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute each tool call
        tool_results: list[dict[str, Any]] = []
        for tc in tool_calls:
            if tc.name not in allowed_tool_names:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": json.dumps({"error": f"Unknown tool: {tc.name}"}),
                        "is_error": True,
                    }
                )
                continue
            try:
                result = mcp_client.call_tool(tc.name, tc.arguments)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": json.dumps(result),
                    }
                )
            except Exception as e:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": json.dumps({"error": str(e)}),
                        "is_error": True,
                    }
                )

        messages.append({"role": "user", "content": tool_results})

    return text or "(Agent reached maximum iterations without a final answer)"
