"""Tests for agent node helpers."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from clinical_trials_agent.agent.nodes import repair_dangling_tool_calls


def _tool_call(call_id: str) -> dict:
    return {"name": "sql_db_query", "args": {"query": "SELECT 1"}, "id": call_id}


class TestRepairDanglingToolCalls:
    """History left by an interrupted run must still be valid for OpenAI."""

    def test_complete_history_unchanged(self):
        messages = [
            HumanMessage(content="q"),
            AIMessage(content="", tool_calls=[_tool_call("a")]),
            ToolMessage(content="1", tool_call_id="a"),
            AIMessage(content="answer"),
        ]
        assert repair_dangling_tool_calls(messages) == messages

    def test_dangling_calls_get_placeholder_responses(self):
        messages = [
            HumanMessage(content="q1"),
            AIMessage(content="", tool_calls=[_tool_call("a"), _tool_call("b")]),
            HumanMessage(content="q2"),
        ]
        repaired = repair_dangling_tool_calls(messages)

        assert [m.type for m in repaired] == ["human", "ai", "tool", "tool", "human"]
        assert [m.tool_call_id for m in repaired[2:4]] == ["a", "b"]
        assert repaired[-1].content == "q2"

    def test_partially_answered_calls(self):
        messages = [
            AIMessage(content="", tool_calls=[_tool_call("a"), _tool_call("b")]),
            ToolMessage(content="1", tool_call_id="a"),
            HumanMessage(content="q2"),
        ]
        repaired = repair_dangling_tool_calls(messages)

        assert [m.type for m in repaired] == ["ai", "tool", "tool", "human"]
        assert [m.tool_call_id for m in repaired[1:3]] == ["a", "b"]

    def test_dangling_call_at_end_of_history(self):
        messages = [AIMessage(content="", tool_calls=[_tool_call("a")])]
        repaired = repair_dangling_tool_calls(messages)

        assert [m.type for m in repaired] == ["ai", "tool"]
