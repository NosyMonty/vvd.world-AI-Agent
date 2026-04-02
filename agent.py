import asyncio
import os
import base64
import json
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page
from ollama import AsyncClient

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------
load_dotenv()
EMAIL        = os.getenv("VVW_EMAIL")
PASSWORD     = os.getenv("VVW_PASSWORD")
MODEL        = os.getenv("OLLAMA_MODEL", "vvd-agent")
VISION_MODEL = os.getenv("VISION_MODEL", "llava")
BASE_URL     = "https://www.vvd.world"

ollama        = AsyncClient()
MEMORY_FILE   = Path("memory.json")
KNOWLEDGE_DIR = Path("knowledge")
ACTIVE_WORLD  = ""

HELP_TEXT = """
Here's what I can do:

CARDS
  "make a character card for [name]"
  "create a location called [name]"
  "add a faction card for [name]"
  "edit [card name] description to [new description]"
  "delete the card for [name]"
  "link [card a] and [card b] as [relationship]"

MAPS
  "create a map called [name]"
  "add a pin for [place] on the [map] map"

WORLDS
  "create a new world called [name]"
  "switch to world [name]"
  "show me the relationship graph"

WIKI & NOTES
  "set the wiki title to [title]"
  "create a session note called [title]"

KNOWLEDGE
  "remember that [lore fact]"
  "what do you know about my campaign?"
  "suggest what I should create next"

D&D QUESTIONS
  "how does the silence spell work?"
  "what monsters live in the underdark?"
  "what are the rules for grappling?"

DEBUG
  "card debug" — test card creation without AI

ADD TO KNOWLEDGE
    "remember that [X]" or "note that [X]" — adds X to campaign knowledge under the right category (lore, characters, factions, locations)
    "add to knowledge "X" under "characters" — adds X to characters knowledge category"
    "add to knowledge "X" under "factions" — adds X to factions knowledge category"
    "add to knowledge "X" under "locations" — adds X to locations knowledge category"
    "add to knowledge "X" under "lore" — adds X to lore knowledge category"
    "add to knowledge"
    
Type 'quit' to exit.
"""

# -------------------------------------------------------
# MEMORY & KNOWLEDGE
# -------------------------------------------------------
def load_memory() -> dict:
    if MEMORY_FILE.exists():
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    return {
        "knowledge": {"lore": [], "characters": [], "factions": [], "locations": []},
        "action_log": [],
        "created_cards": [],
        "created_maps": [],
        "created_worlds": [],
        "chat_history": []
    }
    

def save_memory(memory: dict):
    MEMORY_FILE.write_text(
        json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8"
    )

def log_action(memory: dict, action: str, details: str = ""):
    log_list = memory.setdefault("action_log", [])
    log_list.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": action,
        "details": details
    })
    save_memory(memory)

def load_knowledge_files() -> str:
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    files = list(KNOWLEDGE_DIR.glob("*.md")) + list(KNOWLEDGE_DIR.glob("*.txt"))
    combined = []
    for f in files:
        if f.name == "vvd_knowledge.md":
            continue  # Skip site docs — already baked into model
        content = f.read_text(encoding="utf-8").strip()
        if content:
            combined.append(f"=== {f.name} ===\n{content}")
    return "\n\n".join(combined)

def build_context(memory: dict) -> str:
    parts = []
    file_knowledge = load_knowledge_files()
    if file_knowledge:
        parts.append("CAMPAIGN FILES:\n" + file_knowledge)
    for category, entries in memory["knowledge"].items():
        if entries:
            parts.append(f"{category.upper()}:\n" + "\n".join(f"  {e}" for e in entries))
    if memory["created_cards"]:
        parts.append("CARDS CREATED:\n" + "\n".join(f"  {c}" for c in memory["created_cards"][-20:]))
    if memory["created_maps"]:
        parts.append("MAPS CREATED:\n" + "\n".join(f"  {m}" for m in memory["created_maps"][-10:]))
    if memory["created_worlds"]:
        parts.append("WORLDS:\n" + "\n".join(f"  {w}" for w in memory["created_worlds"]))
    if memory["action_log"]:
        parts.append("RECENT ACTIONS:\n" + "\n".join(
            f"  [{e['time']}] {e['action']}: {e['details']}"
            for e in memory["action_log"][-10:]
        ))
    return "\n\n".join(parts) if parts else ""

def add_knowledge(memory: dict, category: str, content: str):
    allowed_categories = ["lore", "characters", "factions", "locations"]
    
    if category not in allowed_categories:
        print(f"  Unknown knowledge category: {category}")
        return

    category_list = memory["knowledge"].setdefault(category, [])

    if content not in category_list:   
        prompt_text = f"Do you want to add this to your campaign knowledge under '{category}'?\n\n{content}\n\nType 'yes' to confirm: "
        user_choice = input(prompt_text).strip().lower()
        
        if user_choice == "yes":   
            category_list.append(content)
            save_memory(memory)
            log_action(memory, f"Added knowledge to {category}", content)
            print("Successfully added to knowledge base.")
        else:
            print("Addition cancelled by user.")           
    else:
        print(f"Knowledge already exists in {category}.")
# -------------------------------------------------------
# LOGIN
# -------------------------------------------------------
async def login(page: Page):
    print("  Logging in...")
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.get_by_role("button", name="Continue with Email").click()
    await page.wait_for_selector("input#email", timeout=5000)
    await page.fill("input#email", EMAIL)
    await page.fill("input#password", PASSWORD)
    await page.get_by_role("button", name="Sign In").click()
    await page.wait_for_load_state("networkidle")
    print("  Logged in!\n")

# -------------------------------------------------------
# WORLD SELECTOR
# -------------------------------------------------------
async def pick_world(page: Page, memory: dict) -> str:
    global ACTIVE_WORLD
    await page.goto(f"{BASE_URL}/worlds", wait_until="networkidle")
    await page.wait_for_selector("h3.font-medium", timeout=5000)

    world_elements = await page.query_selector_all("h3.font-medium")
    worlds = []
    for el in world_elements:
        text = (await el.inner_text()).strip()
        if text:
            worlds.append(text)

    if not worlds:
        name = input("  Agent: I couldn't read your worlds. What's your world called? ").strip()
        ACTIVE_WORLD = name
        return name

    if len(worlds) == 1:
        print(f"  Agent: I can see your world: {worlds[0]}. Opening it now!\n")
        ACTIVE_WORLD = worlds[0]
        await go_to_world(page, worlds[0])
        return worlds[0]

    print("\n  Agent: I can see these worlds:")
    for i, w in enumerate(worlds, 1):
        print(f"    {i}. {w}")
    print()

    while True:
        choice = input("  Agent: Which world do you want to work in? (name or number): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(worlds):
                ACTIVE_WORLD = worlds[idx]
                await go_to_world(page, ACTIVE_WORLD)
                print(f"\n  Opened: {ACTIVE_WORLD}\n")
                return ACTIVE_WORLD
        else:
            match = next((w for w in worlds if choice.lower() in w.lower()), None)
            if match:
                ACTIVE_WORLD = match
                await go_to_world(page, ACTIVE_WORLD)
                print(f"\n  Opened: {ACTIVE_WORLD}\n")
                return ACTIVE_WORLD
        print("  Didn't recognise that, try again.")

# -------------------------------------------------------
# NAVIGATE TO WORLD
# -------------------------------------------------------
async def go_to_world(page: Page, world_name: str):
    current_url = page.url
    if "/worlds/" in current_url and current_url.split("/worlds/")[-1] not in ("", "worlds"):
        print(f"  Already in a world, skipping navigation")
        return

    await page.goto(f"{BASE_URL}/worlds", wait_until="networkidle")
    await page.wait_for_selector("h3.font-medium", timeout=5000)

    try:
        world_buttons = await page.query_selector_all(
            "button.relative.w-full.text-left.rounded-xl"
        )
        clicked = False
        for btn in world_buttons:
            h3 = await btn.query_selector("h3.font-medium")
            if h3:
                text = (await h3.inner_text()).strip()
                if world_name.lower() in text.lower() or text.lower() in world_name.lower():
                    await btn.click()
                    clicked = True
                    break
        if not clicked:
            raise Exception("World button not found")
        await page.wait_for_load_state("networkidle")
        print(f"  Opened world: {world_name}")
    except Exception as e:
        print(f"  Fallback for world navigation: {e}")
        await vision_click(page, f"the world card called {world_name}")
        await page.wait_for_load_state("networkidle")


# -------------------------------------------------------
# VISION — last resort only
# -------------------------------------------------------
async def screenshot_b64(page: Page) -> str:
    return base64.b64encode(await page.screenshot(type="png")).decode("utf-8")

async def vision_find(page: Page, goal: str) -> dict:
    dims = await page.evaluate("() => ({ w: window.innerWidth, h: window.innerHeight })")
    try:
        b64 = await screenshot_b64(page)
        prompt = (
            f"Browser screenshot {dims['w']}x{dims['h']}px.\n"
            f"Goal: {goal}\n"
            "Reply ONLY with JSON: "
            '{"x": 320, "y": 215, "description": "the button"}\n'
            f"x: 0-{dims['w']}, y: 0-{dims['h']}."
        )
        response = await asyncio.wait_for(
            ollama.chat(model=VISION_MODEL, messages=[{
                "role": "user", "content": prompt, "images": [b64]
            }]),
            timeout=30.0
        )
        raw = response["message"]["content"].strip()
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            x, y = result.get("x"), result.get("y")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                if 0 <= x <= dims["w"] and 0 <= y <= dims["h"]:
                    return result
    except asyncio.TimeoutError:
        print(f"  Vision timed out")
    except Exception as e:
        print(f"  Vision error: {e}")
    return None

async def vision_click(page: Page, goal: str) -> bool:
    print(f"  Vision: {goal}")
    result = await vision_find(page, goal)
    if result:
        try:
            await page.mouse.click(int(result["x"]), int(result["y"]))
            await page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            print(f"  Click failed: {e}")
    return False

async def vision_fill(page: Page, goal: str, value: str) -> bool:
    print(f"  Vision fill: {goal}")
    result = await vision_find(page, f"input field for {goal}")
    if result:
        try:
            await page.mouse.click(int(result["x"]), int(result["y"]))
            await asyncio.sleep(0.3)
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(value)
            return True
        except Exception as e:
            print(f"  Fill failed: {e}")
    return False

# -------------------------------------------------------
# CARD CREATION STEPS
# -------------------------------------------------------
async def do_create_card_steps(page: Page, card_type: str, name: str, description: str = ""):
    """Runs browser steps to create a card. Assumes already in world NOT in editor."""
    
    # Press 2 to open the Editor/Cards tab
    print(f"  Pressing 2 to open Editor...")
    await page.keyboard.press("2")
    await asyncio.sleep(0.5)
    await page.wait_for_load_state("networkidle")

    # Step 1: Click Card button
    print(f"  Clicking Card button...")
    await page.get_by_role("button", name="Card", exact=True).click()
    await asyncio.sleep(0.5)

    # Step 2: Select card type
    print(f"  Selecting type: {card_type}")
    try:
        await page.get_by_role("button", name=card_type.title(), exact=True).click()
    except:
        try:
            await page.get_by_role("button", name=card_type).click()
        except:
            await vision_click(page, f"the {card_type} card type button")
    await asyncio.sleep(0.5)

    # Step 3: Fill in card name
    print(f"  Setting name: {name}")
    try:
        await page.get_by_role("textbox", name="New Card").click()
        await page.get_by_role("textbox", name="New Card").fill(name)
    except:
        await vision_fill(page, "card name field", name)

    # Step 4: Click Text button then fill description
    if description:
        print(f"  Adding description...")
        try:
            await page.get_by_role("button", name="Text").click()
            await asyncio.sleep(0.5)
            await page.get_by_role("paragraph").filter(has_text=re.compile(r"^$")).click()
            await page.locator(".tiptap.ProseMirror.w-full").fill(description)
        except:
            try:
                await page.locator(".tiptap.ProseMirror.w-full").fill(description)
            except:
                await vision_fill(page, "description text editor", description)

    # Step 5: Close — card autosaves
    print(f"  Closing card...")
    await asyncio.sleep(0.5)
    try:
        await page.get_by_role("button", name="Close").click()
    except:
        try:
            await page.click("button:has-text('Close')", timeout=2000)
        except:
            await page.keyboard.press("Escape")

    await page.wait_for_load_state("networkidle")
    print(f"  Card '{name}' created!")

# -------------------------------------------------------
# SITE ACTIONS
# -------------------------------------------------------
async def create_card(page: Page, memory: dict, world: str, card_type: str,
                      name: str, description: str = "", extra: str = ""):
    global ACTIVE_WORLD
    print(f"  Navigating to world: {world}")
    current_url = page.url
    if "/worlds/" in current_url and current_url.split("/worlds/")[-1] not in ("", "worlds"):
        print(f"  Already in world, skipping navigation")
    else:
        await go_to_world(page, world)
        ACTIVE_WORLD = world

    await do_create_card_steps(page, card_type, name, description)
    memory["created_cards"].append(f"{name} ({card_type}) in {world}")
    log_action(memory, f"Created {card_type} card", f"{name} in {world}")

async def edit_card(page: Page, memory: dict, world: str, card_name: str, new_description: str):
    await go_to_world(page, world)
    try:
        await page.click(f"text={card_name}", timeout=3000)
    except:
        await vision_click(page, f"the card called {card_name}")
    try:
        await page.locator(".tiptap.ProseMirror.w-full").click()
        await page.keyboard.press("Control+a")
        await page.keyboard.type(new_description)
    except:
        await vision_fill(page, "description editor", new_description)
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Edited card", f"{card_name} in {world}")

async def delete_card(page: Page, memory: dict, world: str, card_name: str):
    await go_to_world(page, world)
    try:
        await page.click(f"text={card_name}", timeout=3000)
    except:
        await vision_click(page, f"the card called {card_name}")
    await vision_click(page, "the Delete button")
    await vision_click(page, "the Confirm or Yes button")
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Deleted card", f"{card_name} in {world}")

async def link_cards(page: Page, memory: dict, world: str,
                     card_a: str, card_b: str, relationship: str = ""):
    await go_to_world(page, world)
    try:
        await page.click(f"text={card_a}", timeout=3000)
    except:
        await vision_click(page, f"the card called {card_a}")
    await vision_click(page, "the Link or Relationship button")
    await vision_fill(page, "search for card to link", card_b)
    try:
        await page.click(f"text={card_b}", timeout=3000)
    except:
        await vision_click(page, f"search result for {card_b}")
    if relationship:
        await vision_fill(page, "relationship label", relationship)
    await vision_click(page, "Save button")
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Linked cards", f"{card_a} to {card_b} ({relationship})")

async def create_map(page: Page, memory: dict, world: str, map_name: str, description: str = ""):
    await go_to_world(page, world)
    await vision_click(page, "the Maps navigation link")
    await vision_click(page, "the New Map button")
    await vision_fill(page, "map name field", map_name)
    if description:
        await vision_fill(page, "description field", description)
    await vision_click(page, "the Create or Save button")
    await page.wait_for_load_state("networkidle")
    memory["created_maps"].append(f"{map_name} in {world}")
    log_action(memory, "Created map", f"{map_name} in {world}")

async def add_map_pin(page: Page, memory: dict, world: str, map_name: str,
                      pin_name: str, linked_card: str = ""):
    await go_to_world(page, world)
    await vision_click(page, "the Maps navigation link")
    try:
        await page.click(f"text={map_name}", timeout=3000)
    except:
        await vision_click(page, f"the map called {map_name}")
    await vision_click(page, "the Add Pin button")
    await vision_fill(page, "pin name field", pin_name)
    if linked_card:
        await vision_fill(page, "search to link a card to this pin", linked_card)
        try:
            await page.click(f"text={linked_card}", timeout=3000)
        except:
            await vision_click(page, f"search result for {linked_card}")
    await vision_click(page, "Save button")
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Added map pin", f"{pin_name} on {map_name}")

async def view_graph(page: Page, world: str):
    await go_to_world(page, world)
    await vision_click(page, "the Graph or Relationship Graph navigation link")
    await page.wait_for_load_state("networkidle")

async def create_world_action(page: Page, memory: dict, name: str, description: str = ""):
    await page.goto(f"{BASE_URL}/worlds", wait_until="networkidle")
    await vision_click(page, "the New World or Create World button")
    await vision_fill(page, "world name field", name)
    if description:
        await vision_fill(page, "description field", description)
    await vision_click(page, "the Create or Save button")
    await page.wait_for_load_state("networkidle")
    memory["created_worlds"].append(name)
    log_action(memory, "Created world", name)

async def configure_wiki(page: Page, memory: dict, world: str,
                         wiki_title: str, is_public: bool = True):
    await go_to_world(page, world)
    await vision_click(page, "the Wiki navigation link")
    await vision_click(page, "the Wiki Settings button")
    await vision_fill(page, "wiki title field", wiki_title)
    await vision_click(page, f"the {'Public' if is_public else 'Private'} option")
    await vision_click(page, "Save button")
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Configured wiki", f"{wiki_title} in {world}")

async def create_session_note(page: Page, memory: dict, world: str, title: str, notes: str):
    await go_to_world(page, world)
    await vision_click(page, "the Sessions or Notes navigation link")
    await vision_click(page, "the New Session or Add Note button")
    await vision_fill(page, "session title field", title)
    await vision_fill(page, "notes content field", notes)
    await vision_click(page, "Save button")
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Created session note", f"{title} in {world}")

async def invite_collaborator(page: Page, memory: dict, world: str, email: str):
    await go_to_world(page, world)
    await vision_click(page, "the Collaborate or Share or Settings button")
    await vision_fill(page, "email field to invite collaborator", email)
    await vision_click(page, "Invite or Send button")
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Invited collaborator", email)

async def update_profile(page: Page, memory: dict, display_name: str = "", bio: str = ""):
    await page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
    if display_name:
        await vision_fill(page, "display name field", display_name)
    if bio:
        await vision_fill(page, "bio field", bio)
    await vision_click(page, "Save button")
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Updated profile", f"name={display_name}")

async def ai_suggest(memory: dict) -> str:
    context = build_context(memory)
    response = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
        "You are a creative D&D worldbuilding assistant.\n\n"
        f"CAMPAIGN KNOWLEDGE:\n{context}\n\n"
        "Suggest 5 specific NEW things to create as cards or maps that don't exist yet.\n"
        "Be creative and make them fit the world's style and tone.\n"
        "Format: TYPE | NAME | one sentence description."
    )}])
    return response["message"]["content"].strip()

# -------------------------------------------------------
# WEB SEARCH (Tavily)
# -------------------------------------------------------
async def answer_with_search(question: str, memory: dict) -> str:
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise Exception("TAVILY_API_KEY not set in .env")
        client = TavilyClient(api_key=api_key)
        print(f"  Searching: {question}")
        results = await asyncio.to_thread(
            client.search, question, max_results=4, search_depth="advanced"
        )
        results_text = "\n\n".join(
            f"Title: {r['title']}\nSummary: {r['content']}\nSource: {r['url']}"
            for r in results.get("results", [])
        )
    except Exception as e:
        print(f"  Search failed: {e}")
        results_text = "Web search unavailable."

    context = build_context(memory)
    response = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
        "You are a knowledgeable D&D assistant.\n\n"
        f"CAMPAIGN KNOWLEDGE:\n{context}\n\n"
        f"WEB SEARCH RESULTS:\n{results_text}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using web results and campaign knowledge together.\n"
        "Be concise and directly useful to a dungeon master."
    )}])
    return response["message"]["content"].strip()

# -------------------------------------------------------
# INTENT PARSING
# -------------------------------------------------------
async def parse_intent(user_message: str, memory: dict, chat_history: list) -> dict:
    global ACTIVE_WORLD
    context = build_context(memory)
    history_str = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Agent'}: {m['content']}"
        for m in chat_history[-6:]
    ) if chat_history else ""

    prompt = (
        "You are an AI assistant managing a D&D worldbuilding site (vvd.world).\n\n"
        f"ACTIVE WORLD: {ACTIVE_WORLD}\n\n"
        f"CAMPAIGN KNOWLEDGE:\n{context}\n\n"
        f"RECENT CONVERSATION:\n{history_str}\n\n"
        f"USER SAYS: {user_message}\n\n"
        "RULES:\n"
        f"1. Default world is '{ACTIVE_WORLD}' — always use this unless told otherwise.\n"
        "2. Use campaign knowledge as INSPIRATION to create NEW original content.\n"
        "   Invent completely new characters/creatures/locations that FIT the world style.\n"
        "   Write LONG detailed descriptions — minimum 4-5 sentences covering appearance,\n"
        "   personality, backstory, role, motivations, and one unique memorable trait.\n"
        "   NEVER copy existing characters. Use lore as background context only.\n"
        "3. Infer card_type: person/villain/hero/NPC=character, place/city=location,\n"
        "   group/guild=faction, creature/monster/beast/animal=character.\n"
        "4. The NAME must come EXACTLY from what the user said — never substitute from lore.\n"
        "5. 'remember that X' or 'note that X' = add_knowledge.\n"
        "6. CRITICAL intent matching — check IN ORDER:\n"
        "   - 'delete', 'remove', 'get rid of' = delete_card. NEVER create_card.\n"
        "   - 'edit', 'update', 'change', 'modify' = edit_card. NEVER create_card.\n"
        "   - 'link', 'connect', 'relate' = link_cards. NEVER create_card.\n"
        "   - 'create', 'make', 'add', 'new' + anything = create_card.\n"
        "   - D&D rules/spells/monsters/mechanics questions = web_search.\n"
        "   - Campaign questions = ask_question.\n"
        "   NEVER explain. NEVER summarise. Always return JSON only.\n\n"
        "   - Questions starting with 'how do I', 'what is', 'what are', 'how does', 'can I', 'tell me' = ask_question or web_search. NEVER create_card.\n"
        "   - If the sentence contains a question mark or starts with a question word, it is NEVER create_card.\n"
        "Available intents:\n"
        "- create_card: world, card_type, name, description (optional: extra)\n"
        "- edit_card: world, card_name, new_description\n"
        "- delete_card: world, card_name\n"
        "- link_cards: world, card_a, card_b (optional: relationship)\n"
        "- create_map: world, map_name (optional: description)\n"
        "- add_map_pin: world, map_name, pin_name (optional: linked_card)\n"
        "- create_world: name (optional: description)\n"
        "- switch_world: world\n"
        "- view_graph: world\n"
        "- configure_wiki: world, wiki_title, is_public\n"
        "- create_session_note: world, title, notes\n"
        "- invite_collaborator: world, email\n"
        "- update_profile: display_name and/or bio\n"
        "- add_knowledge: category (lore/characters/factions/locations), content\n"
        "- view_knowledge\n"
        "- ai_suggest\n"
        "- web_search: question (D&D rules, spells, monsters, mechanics)\n"
        "- ask_question: question (campaign specific)\n"
        "- help\n"
        "- unknown\n\n"
        "Set missing fields to null only if truly cannot infer.\n\n"
        f'Reply ONLY with JSON:\n'
        f'{{"intent": "create_card", "params": {{"world": "{ACTIVE_WORLD}", '
        f'"card_type": "character", "name": "Zara the Healer", '
        f'"description": "A battle-hardened cleric...", "extra": null}}, "confidence": "high"}}'
    )

    response = await ollama.chat(
        model=MODEL, messages=[{"role": "user", "content": prompt}]
    )
    raw = response["message"]["content"].strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return {"intent": "unknown", "params": {}, "confidence": "low"}


# -------------------------------------------------------
# MISSING INFO
# -------------------------------------------------------
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

async def get_missing_info(intent: dict, memory: dict) -> str | None:
    params      = intent.get("params", {})
    intent_name = intent.get("intent", "")
    for field in REQUIRED_FIELDS.get(intent_name, []):
        if not params.get(field):
            return await generate_question(field, intent_name, params, memory)
    return None

async def generate_question(missing_field: str, intent: str, params: dict, memory: dict) -> str:
    known   = {k: v for k, v in params.items() if v}
    context = build_context(memory)
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

# -------------------------------------------------------
# CAMPAIGN Q&A
# -------------------------------------------------------
async def answer_question(question: str, memory: dict) -> str:
    context = build_context(memory)
    response = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
        "You are a knowledgeable D&D worldbuilding assistant.\n\n"
        f"CAMPAIGN KNOWLEDGE:\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer helpfully from campaign knowledge.\n"
        "NEVER give step-by-step instructions for using vvd.world.\n"
        "If someone asks to create/make/add/delete something, tell them to just say it\n"
        "and the agent will do it automatically.\n"
        "If it is a D&D rules question suggest they ask it as a search query.\n"
        "If you don't know, say so honestly."
    )}])
    return response["message"]["content"].strip()


# -------------------------------------------------------
# EXECUTE INTENT
# -------------------------------------------------------
async def execute_intent(intent: dict, page: Page, memory: dict) -> str:
    global ACTIVE_WORLD
    name = intent.get("intent")
    p    = intent.get("params", {})

    if "world" in p and not p.get("world"):
        p["world"] = ACTIVE_WORLD

    try:
        if name == "create_card":
            await create_card(page, memory, p["world"], p["card_type"],
                              p["name"], p.get("description", ""), p.get("extra", ""))
            note = " with lore-inspired description" if p.get("description") else ""
            return f"Done! Created a {p['card_type']} card for **{p['name']}**{note}."

        elif name == "edit_card":
            await edit_card(page, memory, p["world"], p["card_name"], p["new_description"])
            return f"Done! Updated **{p['card_name']}**."

        elif name == "delete_card":
            await delete_card(page, memory, p["world"], p["card_name"])
            return f"Done! Deleted **{p['card_name']}**."

        elif name == "link_cards":
            await link_cards(page, memory, p["world"], p["card_a"],
                             p["card_b"], p.get("relationship", ""))
            return f"Done! Linked **{p['card_a']}** and **{p['card_b']}**."

        elif name == "create_map":
            await create_map(page, memory, p["world"], p["map_name"], p.get("description", ""))
            return f"Done! Created map **{p['map_name']}**."

        elif name == "add_map_pin":
            await add_map_pin(page, memory, p["world"], p["map_name"],
                              p["pin_name"], p.get("linked_card", ""))
            return f"Done! Added pin **{p['pin_name']}** to {p['map_name']}."

        elif name == "create_world":
            await create_world_action(page, memory, p["name"], p.get("description", ""))
            return f"Done! Created world **{p['name']}**."

        elif name == "switch_world":
            ACTIVE_WORLD = p["world"]
            await go_to_world(page, p["world"])
            return f"Switched to **{p['world']}**!"

        elif name == "view_graph":
            await view_graph(page, p["world"])
            return f"Opened the relationship graph."

        elif name == "configure_wiki":
            await configure_wiki(page, memory, p["world"], p["wiki_title"],
                                 p.get("is_public", True))
            return f"Done! Wiki configured."

        elif name == "create_session_note":
            await create_session_note(page, memory, p["world"], p["title"], p["notes"])
            return f"Done! Session note **{p['title']}** created."

        elif name == "invite_collaborator":
            await invite_collaborator(page, memory, p["world"], p["email"])
            return f"Done! Invite sent to {p['email']}."

        elif name == "update_profile":
            await update_profile(page, memory, p.get("display_name", ""), p.get("bio", ""))
            return "Done! Profile updated."

        elif name == "add_knowledge":
            cat     = p.get("category", "lore")
            content = p.get("content", "")
            if cat in memory["knowledge"] and content:
                memory["knowledge"][cat].append(content)
                save_memory(memory)
            return "Got it, I'll remember that."

        elif name == "view_knowledge":
            ctx = build_context(memory)
            return f"Here's what I know:\n\n{ctx}" if ctx else "Nothing stored yet."

        elif name == "ai_suggest":
            return f"Here are my suggestions:\n\n{await ai_suggest(memory)}"

        elif name == "web_search":
            return await answer_with_search(p.get("question", ""), memory)

        elif name == "ask_question":
            return await answer_question(p.get("question", ""), memory)

        elif name == "help":
            return HELP_TEXT

        else:
            return None

    except Exception as e:
        return f"Something went wrong: {e}\nTry rephrasing or give me more detail."

# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
async def main():
    global ACTIVE_WORLD
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    memory = load_memory()

    files = list(KNOWLEDGE_DIR.glob("*.md")) + list(KNOWLEDGE_DIR.glob("*.txt"))
    print("\n" + "="*50)
    print("  vvd.world AI Agent")
    print("="*50)
    print(f"  Model    : {MODEL}  |  Vision: {VISION_MODEL}")
    print(f"  Memory   : {len(memory['action_log'])} actions logged")
    print(f"  Knowledge: {sum(len(v) for v in memory['knowledge'].values())} entries")
    if files:
        print(f"  Files    : {', '.join(f.name for f in files)}")
    print("="*50 + "\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        ctx     = await browser.new_context(viewport={"width": 1280, "height": 800})
        page    = await ctx.new_page()

        await login(page)
        ACTIVE_WORLD = await pick_world(page, memory)

        print(f"\nAgent: Ready! Working in **{ACTIVE_WORLD}**.")
        print(f"Agent: What do you want to do? (type 'help' for commands)\n")

        pending_intent = None
        chat_history   = memory.get("chat_history", [])
        ACTION_WORDS   = {
            "create", "make", "add", "new", "delete", "remove",
            "edit", "update", "link", "connect", "switch",
            "invite", "map", "pin", "wiki", "note", "session", "card",
            "character", "location", "faction", "item", "lore",
            "creature", "monster", "beast", "animal"
        }

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAgent: Bye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "bye"):
                print("Agent: Bye! Progress saved.")
                break

            # Debug mode
            if user_input.lower() == "card debug":
                print("\n  Running card debug — skipping navigation...\n")
                try:
                    await do_create_card_steps(
                        page,
                        card_type="character",
                        name="Debug Test Card",
                        description="This is a debug test card created without AI."
                    )
                    print("Agent: Debug card created!\n")
                except Exception as e:
                    print(f"Agent: Debug failed at: {e}\n")
                continue
            elif user_input.lower() == "wipe memory":
                confirm = input("  Are you sure you want to wipe memory? (yes/no): ").strip().lower()
                if confirm == "yes":
                    memory.update({
                        "knowledge": {"lore": [], "characters": [], "factions": [], "locations": []},
                        "action_log": [],
                        "created_cards": [],
                        "created_maps": [],
                        "created_worlds": [],
                        "chat_history": []
                    })
                    save_memory(memory)
                    chat_history = []
                    pending_intent = None
                    print("Agent: Memory wiped! Starting fresh.\n")
                else:
                    print("Agent: Memory wipe cancelled.\n")
                continue

            chat_history.append({"role": "user", "content": user_input})
            memory["chat_history"] = chat_history[-20:]

            # Merge answer into pending intent
            if pending_intent:
                merge_resp = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
                    f"Update this intent with the user's answer:\n"
                    f"Intent: {json.dumps(pending_intent)}\n"
                    f"Answer: \"{user_input}\"\n"
                    "Reply ONLY with the updated JSON intent."
                )}])
                raw = merge_resp["message"]["content"].strip()
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    try:
                        pending_intent = json.loads(match.group())
                    except:
                        pass
            else:
                pending_intent = await parse_intent(user_input, memory, chat_history)

            missing_question = await get_missing_info(pending_intent, memory)

            if missing_question:
                print(f"\nAgent: {missing_question}\n")
                chat_history.append({"role": "assistant", "content": missing_question})
            else:
                # Spinner
                stop_spinner = asyncio.Event()

                async def spinner():
                    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
                    i = 0
                    while not stop_spinner.is_set():
                        print(f"\r  Working {frames[i % len(frames)]}", end="", flush=True)
                        i += 1
                        await asyncio.sleep(0.1)
                    print("\r                    \r", end="")

                spinner_task = asyncio.create_task(spinner())
                result = await execute_intent(pending_intent, page, memory)
                stop_spinner.set()
                await spinner_task

                if result:
                    print(f"Agent: {result}\n")
                    chat_history.append({"role": "assistant", "content": result})
                else:
                    # Force re-parse if it looks like an action
                    words = set(user_input.lower().split())
                    if words & ACTION_WORDS:
                        forced = await parse_intent(
                            f"PERFORM THIS ACTION on vvd.world right now: {user_input}",
                            memory, chat_history
                        )
                        if forced.get("intent") not in ("unknown", "ask_question", "help", None):
                            missing = await get_missing_info(forced, memory)
                            if not missing:
                                result2 = await execute_intent(forced, page, memory)
                                if result2:
                                    print(f"Agent: {result2}\n")
                                    chat_history.append({"role": "assistant", "content": result2})
                                    pending_intent = None
                                    memory["chat_history"] = chat_history[-20:]
                                    save_memory(memory)
                                    pending_intent = None
                                    memory["chat_history"] = chat_history[-20:]
                                    save_memory(memory)
                                    continue

                    answer = await answer_question(user_input, memory)
                    print(f"Agent: {answer}\n")
                    chat_history.append({"role": "assistant", "content": answer})

                pending_intent = None

            memory["chat_history"] = chat_history[-20:]
            save_memory(memory)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())