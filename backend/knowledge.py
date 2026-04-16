"""
Knowledge module — manages campaign lore at two levels:
  Short term: memory["knowledge"] dict (cleared on wipe)
  Long term:  knowledge/agent_lore.md (persists forever, auto-written by agent)

Also provides build_context() for AI prompt construction.
"""
from pathlib import Path
from datetime import datetime
from .agent_core import KNOWLEDGE_DIR, MODEL, ollama
from .memory import save_memory, log_action

AGENT_LORE_FILE = Path("knowledge/agent_lore.md")


# -------------------------------------------------------
# FILE LOADING
# -------------------------------------------------------

def load_knowledge_files() -> str:
    """Load all .md and .txt files from the knowledge folder."""
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    files = sorted(
        list(KNOWLEDGE_DIR.glob("*.md")) +
        list(KNOWLEDGE_DIR.glob("*.txt"))
    )
    combined = []
    for f in files:
        if f.name == "vvd_knowledge.md":
            continue  # excluded — baked into old Modelfile
        content = f.read_text(encoding="utf-8").strip()
        if content:
            combined.append(f"=== {f.name} ===\n{content}")
    return "\n\n".join(combined)


def build_context(memory: dict) -> str:
    """
    Build a full context string combining:
    - Knowledge files (lore.md, agent_lore.md, etc.)
    - In-memory knowledge entries
    - Created cards/maps/worlds
    - Recent action log
    """
    parts = []

    file_knowledge = load_knowledge_files()
    if file_knowledge:
        parts.append("CAMPAIGN FILES:\n" + file_knowledge)

    for category, entries in memory.get("knowledge", {}).items():
        if entries:
            parts.append(
                f"{category.upper()}:\n" +
                "\n".join(f"  {e}" for e in entries)
            )

    if memory.get("created_cards"):
        parts.append("CARDS CREATED:\n" + "\n".join(
            f"  {c}" for c in memory["created_cards"][-20:]
        ))

    if memory.get("created_maps"):
        parts.append("MAPS CREATED:\n" + "\n".join(
            f"  {m}" for m in memory["created_maps"][-10:]
        ))

    if memory.get("created_worlds"):
        parts.append("WORLDS:\n" + "\n".join(
            f"  {w}" for w in memory["created_worlds"]
        ))

    if memory.get("action_log"):
        parts.append("RECENT ACTIONS:\n" + "\n".join(
            f"  [{e['time']}] {e['action']}: {e['details']}"
            for e in memory["action_log"][-10:]
        ))

    return "\n\n".join(parts) if parts else ""


# -------------------------------------------------------
# KNOWLEDGE MANAGEMENT
# -------------------------------------------------------

def add_knowledge(memory: dict, category: str, content: str):
    """Add a piece of knowledge to short-term memory."""
    allowed = ["lore", "characters", "factions", "locations"]
    if category not in allowed or not content:
        return
    entries = memory["knowledge"].setdefault(category, [])
    if content not in entries:
        entries.append(content)
        save_memory(memory)
        log_action(memory, f"Added knowledge to {category}", content)


def append_to_agent_lore(entry: str):
    """
    Write a fact to the long-term agent_lore.md file.
    This file grows over time as the agent learns about the campaign.
    """
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"- [{timestamp}] {entry.strip()}\n"

    if not AGENT_LORE_FILE.exists():
        AGENT_LORE_FILE.write_text(
            "# Agent-Generated Lore\n\n"
            "This file is automatically maintained by the vvw-agent.\n"
            "It records facts learned during sessions.\n\n",
            encoding="utf-8"
        )

    with open(AGENT_LORE_FILE, "a", encoding="utf-8") as f:
        f.write(line)


async def extract_and_store_lore(card_name: str, card_type: str,
                                 description: str, memory: dict):
    """
    After creating a card, use the AI to extract a one-line lore fact
    and store it in both short-term memory and agent_lore.md.
    """
    if not description:
        return

    try:
        response = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
            "Extract ONE concise lore fact from this card description for a campaign knowledge base.\n"
            f"Card: {card_name} ({card_type})\n"
            f"Description: {description}\n\n"
            "Reply with ONLY the fact as a single sentence. No preamble.\n"
            "Example: 'Malachar is an ancient lich who seeks to unmake the sky.'"
        )}])
        fact = response["message"]["content"].strip()

        # Store in short-term memory under the right category
        category_map = {
            "character": "characters",
            "location":  "locations",
            "faction":   "factions",
        }
        category = category_map.get(card_type.lower(), "lore")
        add_knowledge(memory, category, fact)

        # Store in long-term file
        append_to_agent_lore(f"{card_name} ({card_type}): {fact}")

    except Exception:
        pass  # Non-fatal — lore extraction is best-effort


def upload_lore_file(file_path: str, destination_name: str = "") -> bool:
    """
    Copy an external file into the knowledge/ folder.
    Returns True on success.
    """
    source = Path(file_path)
    if not source.exists():
        return False
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    dest_name = destination_name or source.name
    dest = KNOWLEDGE_DIR / dest_name
    dest.write_bytes(source.read_bytes())
    return True


def list_knowledge_files() -> list[dict]:
    """Return metadata about all files in the knowledge folder."""
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    files = list(KNOWLEDGE_DIR.glob("*.md")) + list(KNOWLEDGE_DIR.glob("*.txt"))
    result = []
    for f in files:
        stat = f.stat()
        result.append({
            "name":     f.name,
            "path":     str(f),
            "size_kb":  round(stat.st_size / 1024, 1),
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        })
    result.sort(key=lambda x: x["name"])
    return result