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

    def build_assistant_message(
        self, text: str | None, tool_calls: list[ToolCall]
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = []
        if text:
            content.append({"type": "text", "text": text})
        for tc in tool_calls:
            content.append(
                {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
            )
        return {"role": "assistant", "content": content}

    def build_tool_results(self, results: list[tuple[ToolCall, str, bool]]) -> list[dict[str, Any]]:
        tool_results = []
        for tc, content, is_error in results:
            entry: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": content,
            }
            if is_error:
                entry["is_error"] = True
            tool_results.append(entry)
        return [{"role": "user", "content": tool_results}]


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
        answer, _ = run_agent("Decode this VIN", client, provider)
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
        run_agent("Decode this", client, provider, max_iterations=3)  # returns tuple
        assert client.call_tool.call_count == 3

    def test_unknown_tool_blocked(self):
        provider = StubLLMProvider(
            [
                (None, [ToolCall(id="tc1", name="malicious_tool", arguments={})]),
                ("Could not execute.", []),
            ]
        )
        client = make_mock_client()
        run_agent("Do something", client, provider)  # returns tuple
        client.call_tool.assert_not_called()

    def test_no_tool_calls_returns_text(self):
        provider = StubLLMProvider(
            [
                ("Here is the answer directly.", []),
            ]
        )
        client = make_mock_client()
        answer, _ = run_agent("What is NHTSA?", client, provider)
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
        answer, _ = run_agent("Decode BAD vin", client, provider)
        assert "error" in answer.lower() or "Sorry" in answer


class TestRunAgentHistory:
    def test_multi_turn_history(self):
        """History from turn 1 is available in turn 2."""
        provider = StubLLMProvider(
            [
                ("Answer to first question.", []),
                ("Answer referencing history.", []),
            ]
        )
        client = make_mock_client()

        answer1, history = run_agent("First question", client, provider)
        assert answer1 == "Answer to first question."
        assert len(history) >= 1

        answer2, history2 = run_agent("Follow-up", client, provider, history=history)
        assert answer2 == "Answer referencing history."
        # history2 should contain messages from both turns
        user_msgs = [m for m in history2 if m.get("role") == "user"]
        assert len(user_msgs) == 2

    def test_history_not_mutated(self):
        """Passing history should not mutate the caller's list."""
        provider = StubLLMProvider([("OK.", [])])
        client = make_mock_client()

        original_history: list[dict[str, Any]] = [{"role": "user", "content": "old question"}]
        original_len = len(original_history)

        run_agent("New question", client, provider, history=original_history)
        assert len(original_history) == original_len
