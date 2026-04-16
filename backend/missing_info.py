from .intent import parse_intent
from .knowledge import load_knowledge_files
from .memory import load_memory
import json

REQUIRED_FIELDS = {
    "create_card":         ["world", "card_type", "name"],
    "edit_card":           ["world", "card_name", "new_description"],
    "delete_card":         ["world", "card_name"],
    "link_cards":          ["world", "card_a", "card_b"],
    "create_map":          ["world", "map_name"],
    "add_map_pin":         ["world", "map_name", "pin_name"],
    "create_world":        ["name"],
    "switch_world":        ["world"],
    "view_graph":          ["world"],
    "configure_wiki":      ["world", "wiki_title"],
    "create_session_note": ["world", "title", "notes"],
    "invite_collaborator": ["world", "email"],
    "add_knowledge":       ["category", "content"],
    "web_search":          ["question"],
    "ask_question":        ["question"],
}

async def get_missing_info(intent: dict, memory: dict):
    params = intent.get("params", {})
    intent_name = intent.get("intent", "")

    for field in REQUIRED_FIELDS.get(intent_name, []):
        if not params.get(field):
            return f"Missing required field: {field}"

    return None
