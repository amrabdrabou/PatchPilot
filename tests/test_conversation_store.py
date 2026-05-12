# Verifies JSON-backed saved conversation storage.
import json

from backend import conversation_store


def test_missing_store_returns_empty_list(tmp_path):
    store_file = tmp_path / "conversations.json"

    assert conversation_store.list_conversations(store_file) == []


def test_empty_or_corrupt_store_returns_empty_list(tmp_path):
    empty_file = tmp_path / "empty.json"
    corrupt_file = tmp_path / "corrupt.json"
    empty_file.write_text("", encoding="utf-8")
    corrupt_file.write_text("{not-json", encoding="utf-8")

    assert conversation_store.list_conversations(empty_file) == []
    assert conversation_store.list_conversations(corrupt_file) == []


def test_save_list_and_load_conversation(tmp_path):
    store_file = tmp_path / "data" / "conversations.json"
    messages = [
        {
            "agentId": "user",
            "id": "msg-1",
            "text": "Fix the parser bug",
            "type": "user_task",
        },
        {
            "agentId": "backend",
            "id": "msg-2",
            "text": "Final Answer: done",
            "type": "agent_trace_final",
        },
    ]

    saved = conversation_store.save_conversation(messages, store_file)
    conversations = conversation_store.list_conversations(store_file)
    loaded = conversation_store.get_conversation(saved["id"], store_file)

    assert store_file.exists()
    assert len(conversations) == 1
    assert loaded == saved
    assert saved["title"] == "Fix the parser bug"
    assert saved["messages"] == messages
    assert saved["created_at"].endswith("+01:00") or saved["created_at"].endswith(
        "+02:00"
    )
    assert saved["updated_at"] == saved["created_at"]


def test_list_conversation_summaries_excludes_full_messages(tmp_path):
    store_file = tmp_path / "conversations.json"
    saved = conversation_store.save_conversation(
        [{"agentId": "user", "text": "Summarize this", "type": "user_task"}],
        store_file,
    )

    summaries = conversation_store.list_conversation_summaries(store_file)

    assert summaries == [
        {
            "id": saved["id"],
            "title": "Summarize this",
            "created_at": saved["created_at"],
            "updated_at": saved["updated_at"],
            "message_count": 1,
        }
    ]
    assert "messages" not in summaries[0]


def test_delete_conversation_removes_only_matching_record(tmp_path):
    store_file = tmp_path / "conversations.json"
    first = conversation_store.save_conversation(
        [{"agentId": "user", "text": "First", "type": "user_task"}],
        store_file,
    )
    second = conversation_store.save_conversation(
        [{"agentId": "user", "text": "Second", "type": "user_task"}],
        store_file,
    )

    assert conversation_store.delete_conversation(first["id"], store_file) is True
    assert conversation_store.delete_conversation("missing", store_file) is False

    conversations = conversation_store.list_conversations(store_file)
    assert conversations == [second]


def test_title_falls_back_and_truncates_long_text(tmp_path):
    store_file = tmp_path / "conversations.json"
    fallback = conversation_store.save_conversation([], store_file)
    long_text = " ".join(["word"] * 30)
    titled = conversation_store.save_conversation(
        [{"agentId": "user", "text": long_text, "type": "user_task"}],
        store_file,
    )

    assert fallback["title"] == conversation_store.UNTITLED_CONVERSATION
    assert len(titled["title"]) <= conversation_store.MAX_TITLE_CHARS
    assert titled["title"].endswith("...")


def test_save_overwrites_corrupt_store_with_valid_data(tmp_path):
    store_file = tmp_path / "conversations.json"
    store_file.write_text("{not-json", encoding="utf-8")

    saved = conversation_store.save_conversation(
        [{"agentId": "user", "text": "Recover store", "type": "user_task"}],
        store_file,
    )

    data = json.loads(store_file.read_text(encoding="utf-8"))
    assert data["conversations"] == [saved]
