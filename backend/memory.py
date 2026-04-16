"""
Memory module — manages memory.json including:
- Short-term chat history per session
- Long-term action log
- Created cards/maps/worlds
- Campaign knowledge entries
- Named session history (recall previous sessions)
"""
import json
from datetime import datetime
from pathlib import Path
from .agent_core import MEMORY_FILE


# -------------------------------------------------------
# CORE MEMORY
# -------------------------------------------------------

def _empty_memory() -> dict:
    return {
        "knowledge": {
            "lore":       [],
            "characters": [],
            "factions":   [],
            "locations":  []
        },
        "action_log":     [],
        "created_cards":  [],
        "created_maps":   [],
        "created_worlds": [],
        "chat_history":   [],
        "sessions":       {}   # named session archive
    }


def load_memory() -> dict:
    if MEMORY_FILE.exists():
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        # Ensure sessions key exists for older memory files
        data.setdefault("sessions", {})
        return data
    return _empty_memory()


def save_memory(memory: dict):
    MEMORY_FILE.write_text(
        json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def log_action(memory: dict, action: str, details: str = ""):
    memory.setdefault("action_log", []).append({
        "time":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action":  action,
        "details": details
    })
    save_memory(memory)


def wipe_memory(memory: dict):
    """Reset all memory but preserve saved sessions."""
    sessions = memory.get("sessions", {})
    memory.clear()
    memory.update(_empty_memory())
    memory["sessions"] = sessions
    save_memory(memory)


# -------------------------------------------------------
# CHAT SESSION MANAGEMENT
# -------------------------------------------------------

def save_session(memory: dict, session_name: str = "") -> str:
    """
    Archive the current chat_history as a named session.
    Returns the session key used.
    """
    if not memory.get("chat_history"):
        return ""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    key = session_name.strip() if session_name.strip() else timestamp

    memory.setdefault("sessions", {})[key] = {
        "timestamp":   timestamp,
        "name":        key,
        "messages":    list(memory["chat_history"]),
        "cards_made":  list(memory.get("created_cards", [])),
        "maps_made":   list(memory.get("created_maps", []))
    }
    save_memory(memory)
    return key


def load_session(memory: dict, session_key: str) -> bool:
    """
    Load a saved session back into chat_history.
    Returns True if found.
    """
    sessions = memory.get("sessions", {})
    if session_key not in sessions:
        return False
    memory["chat_history"] = list(sessions[session_key]["messages"])
    save_memory(memory)
    return True


def list_sessions(memory: dict) -> list[dict]:
    """Return a list of saved sessions sorted newest first."""
    sessions = memory.get("sessions", {})
    result = []
    for key, data in sessions.items():
        result.append({
            "key":       key,
            "name":      data.get("name", key),
            "timestamp": data.get("timestamp", ""),
            "messages":  len(data.get("messages", [])),
            "cards":     len(data.get("cards_made", []))
        })
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    return result


def delete_session(memory: dict, session_key: str) -> bool:
    """Delete a saved session. Returns True if it existed."""
    sessions = memory.get("sessions", {})
    if session_key in sessions:
        del sessions[session_key]
        save_memory(memory)
        return True
    return False


def start_new_session(memory: dict, save_current: bool = True,
                      session_name: str = "") -> str:
    """
    Optionally save the current session then clear chat history.
    Returns the key of the saved session (or empty string).
    """
    key = ""
    if save_current and memory.get("chat_history"):
        key = save_session(memory, session_name)
    memory["chat_history"] = []
    save_memory(memory)
    return key