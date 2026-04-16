"""
Intent parsing module.
The AI acts as a general D&D rules + DM assistant.
Campaign lore is injected at runtime from knowledge files — not baked into the model.
"""
import json
import re
from .agent_core import MODEL, ollama
from .knowledge import build_context
from .logs import log
import backend.agent_core as core

REQUIRED_FIELDS = {
    "create_card":         ["card_type", "name"],
    "edit_card":           ["card_name", "new_description"],
    "delete_card":         ["card_name"],
    "link_cards":          ["card_a", "card_b"],
    "create_map":          ["map_name"],
    "add_map_pin":         ["map_name", "pin_name"],
    "create_world":        ["name"],
    "switch_world":        ["world"],
    "view_graph":          [],
    "configure_wiki":      ["wiki_title"],
    "create_session_note": ["title", "notes"],
    "invite_collaborator": ["email"],
    "add_knowledge":       ["category", "content"],
    "web_search":          ["question"],
    "ask_question":        ["question"],
}


async def parse_intent(user_message: str, memory: dict, chat_history: list) -> dict:
    context = build_context(memory)
    active_world = core.ACTIVE_WORLD

    history_str = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Agent'}: {m['content']}"
        for m in chat_history[-8:]
    ) if chat_history else ""

    prompt = (
        "You are an expert D&D Dungeon Master assistant and worldbuilding AI.\n"
        "You know all D&D 5e rules, monsters, spells, classes, and DM techniques.\n"
        "You also help manage a vvd.world worldbuilding account.\n\n"
        f"ACTIVE WORLD: {active_world or 'none selected'}\n\n"
        f"CAMPAIGN KNOWLEDGE (from lore files):\n{context}\n\n"
        f"RECENT CONVERSATION:\n{history_str}\n\n"
        f"USER SAYS: {user_message}\n\n"
        "RULES:\n"
        f"1. Default world is '{active_world}' unless told otherwise.\n"
        "2. Use campaign lore as INSPIRATION. Invent NEW original content that\n"
        "   FITS the world style. Never copy existing characters directly.\n"
        "3. Write LONG rich descriptions — minimum 4-5 sentences covering\n"
        "   appearance, personality, backstory, role, motivations, unique trait.\n"
        "4. NAME must come from what the user said. Invent a fitting name if\n"
        "   they only described a concept (e.g. 'dark elf assassin' → invent name).\n"
        "5. Infer card_type: person/NPC/villain/hero/creature/monster = character,\n"
        "   place/city/dungeon = location, group/guild/kingdom = faction.\n"
        "6. 'remember that X' or 'note that X' = add_knowledge.\n"
        "7. CRITICAL intent rules — check IN ORDER:\n"
        "   - 'delete', 'remove', 'get rid of' = delete_card.\n"
        "   - 'edit', 'update', 'change', 'modify' = edit_card.\n"
        "   - 'link', 'connect', 'relate' = link_cards.\n"
        "   - Questions with '?', 'how do I', 'what is', 'what are',\n"
        "     'how does', 'can I', 'tell me', 'explain' = ask_question or web_search.\n"
        "   - D&D rules/spells/monsters/mechanics = web_search.\n"
        "   - 'create', 'make', 'add', 'new' + card/character/creature/\n"
        "     location/faction/item/lore = create_card.\n"
        "   - Campaign-specific questions = ask_question.\n"
        "   NEVER explain. NEVER summarise. JSON only.\n\n"
        "Available intents:\n"
        "- create_card: world (optional), card_type, name, description\n"
        "- edit_card: world (optional), card_name, new_description\n"
        "- delete_card: world (optional), card_name\n"
        "- link_cards: world (optional), card_a, card_b, relationship (optional)\n"
        "- create_map: world (optional), map_name, description (optional)\n"
        "- add_map_pin: world (optional), map_name, pin_name, linked_card (optional)\n"
        "- create_world: name, description (optional)\n"
        "- switch_world: world\n"
        "- view_graph: world (optional)\n"
        "- configure_wiki: world (optional), wiki_title, is_public (optional)\n"
        "- create_session_note: world (optional), title, notes\n"
        "- invite_collaborator: world (optional), email\n"
        "- add_knowledge: category (lore/characters/factions/locations), content\n"
        "- view_knowledge\n"
        "- ai_suggest\n"
        "- web_search: question\n"
        "- ask_question: question\n"
        "- new_session: session_name (optional)\n"
        "- list_sessions\n"
        "- load_session: session_key\n"
        "- upload_lore\n"
        "- help\n"
        "- unknown\n\n"
        f'Reply ONLY with JSON:\n'
        f'{{"intent": "create_card", "params": {{"world": "{active_world}", '
        f'"card_type": "character", "name": "EXACT NAME FROM USER", '
        f'"description": "RICH ORIGINAL DESCRIPTION", "extra": null}}, "confidence": "high"}}'
    )

    response = await ollama.chat(
        model=MODEL, messages=[{"role": "user", "content": prompt}]
    )
    raw = response["message"]["content"].strip()
    log("intent", f"Raw: {raw[:300]}")

    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            log("intent",
                f"Intent: {result.get('intent')} "
                f"(confidence: {result.get('confidence')})")
            return result
        except:
            pass

    log("intent", "Parse failed — returning unknown", "warn")
    return {"intent": "unknown", "params": {}, "confidence": "low"}


async def get_missing_info(intent: dict, memory: dict) -> str | None:
    """Return a question if required fields are missing, else None."""
    params      = intent.get("params", {})
    intent_name = intent.get("intent", "")
    for field in REQUIRED_FIELDS.get(intent_name, []):
        if not params.get(field):
            return await _generate_question(field, intent_name, params, memory)
    return None


async def _generate_question(missing_field: str, intent: str,
                              params: dict, memory: dict) -> str:
    from .knowledge import build_context
    context = build_context(memory)
    known   = {k: v for k, v in params.items() if v}
    response = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
        "You are a friendly D&D worldbuilding assistant.\n\n"
        f"User wants to: {intent}\n"
        f"You know: {json.dumps(known)}\n"
        f"You need: {missing_field}\n"
        f"Campaign context: {context[:400]}\n\n"
        f"Write ONE short natural question to get '{missing_field}'.\n"
        "No technical terms. Just ask naturally. Reply with just the question."
    )}])
    return response["message"]["content"].strip()