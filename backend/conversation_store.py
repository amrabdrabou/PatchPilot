# Stores saved UI conversations in a small JSON file.
import json
import re
import uuid
from copy import deepcopy
from pathlib import Path

from backend.config import CONVERSATION_STORE_FILE
from backend.run_logger import stockholm_now_iso

UNTITLED_CONVERSATION = "Untitled conversation"
MAX_TITLE_CHARS = 60


def normalize_title(text):
    """
    Return a compact display title from free-form message text.
    """
    title = re.sub(r"\s+", " ", str(text)).strip()

    if not title:
        return UNTITLED_CONVERSATION

    if len(title) <= MAX_TITLE_CHARS:
        return title

    return title[: MAX_TITLE_CHARS - 3].rstrip() + "..."


def derive_title(messages):
    """
    Build a conversation title from the first user-facing task message.
    """
    for message in messages:
        if message.get("type") == "user_task" or message.get("agentId") == "user":
            return normalize_title(message.get("text", ""))

    return UNTITLED_CONVERSATION


def read_store_file(store_file=CONVERSATION_STORE_FILE):
    """
    Read the JSON store, returning an empty shape when storage is unavailable.
    """
    store_path = Path(store_file)

    try:
        if not store_path.exists() or store_path.stat().st_size == 0:
            return {"conversations": []}

        data = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"conversations": []}

    conversations = data.get("conversations") if isinstance(data, dict) else None

    if not isinstance(conversations, list):
        return {"conversations": []}

    return {"conversations": conversations}


def write_store_file(data, store_file=CONVERSATION_STORE_FILE):
    """
    Persist the full conversation store as formatted JSON.
    """
    store_path = Path(store_file)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def list_conversations(store_file=CONVERSATION_STORE_FILE):
    """
    Return saved conversations without mutating storage.
    """
    return deepcopy(read_store_file(store_file)["conversations"])


def list_conversation_summaries(store_file=CONVERSATION_STORE_FILE):
    """
    Return compact saved-conversation records for the left panel.
    """
    summaries = []

    for conversation in list_conversations(store_file):
        summaries.append(
            {
                "id": conversation.get("id"),
                "title": conversation.get("title", UNTITLED_CONVERSATION),
                "created_at": conversation.get("created_at"),
                "updated_at": conversation.get("updated_at"),
                "message_count": len(conversation.get("messages", [])),
            }
        )

    return summaries


def get_conversation(conversation_id, store_file=CONVERSATION_STORE_FILE):
    """
    Return one saved conversation by id, or None when it is not found.
    """
    for conversation in list_conversations(store_file):
        if conversation.get("id") == conversation_id:
            return conversation

    return None


def save_conversation(messages, store_file=CONVERSATION_STORE_FILE):
    """
    Save one message stream as a new conversation.
    """
    now = stockholm_now_iso()
    conversation = {
        "id": str(uuid.uuid4()),
        "title": derive_title(messages),
        "created_at": now,
        "updated_at": now,
        "messages": deepcopy(messages),
    }
    data = read_store_file(store_file)
    data["conversations"].insert(0, conversation)
    write_store_file(data, store_file)

    return conversation


def delete_conversation(conversation_id, store_file=CONVERSATION_STORE_FILE):
    """
    Delete one saved conversation and return whether anything changed.
    """
    data = read_store_file(store_file)
    original_count = len(data["conversations"])
    data["conversations"] = [
        conversation
        for conversation in data["conversations"]
        if conversation.get("id") != conversation_id
    ]

    if len(data["conversations"]) == original_count:
        return False

    write_store_file(data, store_file)
    return True
