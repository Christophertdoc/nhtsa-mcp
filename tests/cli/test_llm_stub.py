"""Tests for LLM agent with stubbed provider — no real API calls."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from cli.llm_agent import LLMProvider, ToolCall, run_agent
from cli.mcp_client import MCPClient

VIN = "1FA6P8AM0G5227539"
TEST_VIN = "TEST12345678901234"


class StubLLMProvider(LLMProvider):
    """Returns a predictable sequence of responses."""

    def __init__(self, responses: list[tuple[str | None, list[ToolCall]]]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
    ) -> tuple[str | None, list[ToolCall]]:
        if self._call_count < len(self._responses):
            resp = self._responses[self._call_count]
            self._call_count += 1
            return resp
        return "Done", []


def make_mock_client(tool_results: dict[str, Any] | None = None) -> MCPClient:
    """Create a mock MCPClient."""
    client = MagicMock(spec=MCPClient)
    client.list_tools.return_value = [
        {"name": "decode_vin_tool", "description": "Decode VIN", "inputSchema": {}},
        {"name": "ratings_search_tool", "description": "Search ratings", "inputSchema": {}},
    ]
    if tool_results:
        client.call_tool.return_value = tool_results
    else:
        client.call_tool.return_value = {"summary": {"vin": "TEST"}, "results": []}
    return client


class TestRunAgent:
    def test_single_tool_call(self):
        tc = ToolCall(id="tc1", name="decode_vin_tool", arguments={"vin": VIN})
        provider = StubLLMProvider(
            [
                (None, [tc]),
                ("The VIN decodes to a Ford Mustang.", []),
            ]
        )
        client = make_mock_client()
        answer = run_agent("Decode this VIN", client, provider)
        assert "Ford Mustang" in answer
        client.call_tool.assert_called_once_with("decode_vin_tool", {"vin": VIN})

    def test_circuit_breaker(self):
        infinite_calls = [
            (
                None,
                [
                    ToolCall(
                        id=f"tc{i}",
                        name="decode_vin_tool",
                        arguments={"vin": TEST_VIN},
                    )
                ],
            )
            for i in range(20)
        ]
        provider = StubLLMProvider(infinite_calls)
        client = make_mock_client()
        run_agent("Decode this", client, provider, max_iterations=3)
        assert client.call_tool.call_count == 3

    def test_unknown_tool_blocked(self):
        provider = StubLLMProvider(
            [
                (None, [ToolCall(id="tc1", name="malicious_tool", arguments={})]),
                ("Could not execute.", []),
            ]
        )
        client = make_mock_client()
        run_agent("Do something", client, provider)
        client.call_tool.assert_not_called()

    def test_no_tool_calls_returns_text(self):
        provider = StubLLMProvider(
            [
                ("Here is the answer directly.", []),
            ]
        )
        client = make_mock_client()
        answer = run_agent("What is NHTSA?", client, provider)
        assert answer == "Here is the answer directly."

    def test_tool_error_handled(self):
        tc = ToolCall(id="tc1", name="decode_vin_tool", arguments={"vin": "BAD"})
        provider = StubLLMProvider(
            [
                (None, [tc]),
                ("Sorry, the tool returned an error.", []),
            ]
        )
        client = make_mock_client()
        client.call_tool.side_effect = Exception("Connection refused")
        answer = run_agent("Decode BAD vin", client, provider)
        assert "error" in answer.lower() or "Sorry" in answer
