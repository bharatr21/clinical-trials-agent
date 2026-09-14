"""Tests for conversation history formatting."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from clinical_trials_agent.agent.nodes import (
    INTERNAL_MESSAGE_KEY,
    LIST_TABLES_CALL_ID,
    TABLE_LIST_PREFIX,
)
from clinical_trials_agent.api.routes.conversations import _visible_messages


def _list_tables_messages(flagged: bool = True) -> list:
    return [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "sql_db_list_tables", "args": {}, "id": LIST_TABLES_CALL_ID}
            ],
            id="lt1",
        ),
        ToolMessage(
            content="studies, sponsors", tool_call_id=LIST_TABLES_CALL_ID, id="lt2"
        ),
        AIMessage(
            content=f"{TABLE_LIST_PREFIX}studies, sponsors",
            response_metadata={INTERNAL_MESSAGE_KEY: True} if flagged else {},
            id="lt3",
        ),
    ]


class TestVisibleMessages:
    """Pipeline internals must not appear as assistant replies."""

    def test_successful_turn_shows_question_sql_and_answer(self):
        sql_call = {"name": "sql_db_query", "args": {"query": "SELECT 1"}, "id": "q"}
        raw = [
            HumanMessage(content="How many trials?", id="h1"),
            *_list_tables_messages(),
            AIMessage(content="", tool_calls=[sql_call], id="a1"),
            ToolMessage(content="[(1,)]", tool_call_id="q", id="t1"),
            AIMessage(content="There is 1 trial.", id="a2"),
        ]
        visible = _visible_messages(raw)

        # The UI renders only messages with content; tool calls carry the SQL
        assert [(m.role, m.content) for m in visible if m.content] == [
            ("user", "How many trials?"),
            ("assistant", "There is 1 trial."),
        ]
        sql_calls = [m for m in visible if m.id == "a1"]
        assert sql_calls[0].tool_calls[0]["args"]["query"] == "SELECT 1"

    def test_failed_turn_does_not_show_table_list(self):
        raw = [
            HumanMessage(content="How many trials?", id="h1"),
            *_list_tables_messages(),
        ]
        visible = _visible_messages(raw)

        assert [m.role for m in visible if m.content] == ["user"]

    def test_unflagged_table_list_from_old_checkpoint_hidden(self):
        raw = [
            HumanMessage(content="How many trials?", id="h1"),
            *_list_tables_messages(flagged=False),
        ]
        visible = _visible_messages(raw)

        assert [m.role for m in visible if m.content] == ["user"]

    def test_answer_starting_with_table_list_prefix_kept(self):
        answer = f"{TABLE_LIST_PREFIX}studies, sponsors, and 22 more."
        raw = [
            HumanMessage(content="Which tables exist?", id="h1"),
            *_list_tables_messages(),
            AIMessage(content=answer, id="a1"),
        ]
        visible = _visible_messages(raw)

        assert [(m.role, m.content) for m in visible if m.content] == [
            ("user", "Which tables exist?"),
            ("assistant", answer),
        ]
