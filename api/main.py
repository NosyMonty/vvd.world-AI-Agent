"""
vvw-agent FastAPI server.

Run with:
    uvicorn api.main:app

Do NOT use --reload with Playwright on Windows.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.async_api import async_playwright
from pathlib import Path
import asyncio
import shutil

import backend.agent_core as core
from backend.memory import (
    load_memory, save_memory, log_action, wipe_memory,
    save_session, load_session, list_sessions, delete_session, start_new_session
)
from backend.knowledge import (
    load_knowledge_files, build_context, add_knowledge,
    extract_and_store_lore, list_knowledge_files, append_to_agent_lore,
    upload_lore_file
)
from backend.intent import parse_intent, get_missing_info
from backend.browser import login, go_to_world, list_worlds
from backend.cards import create_card, edit_card, delete_card, link_cards
from backend.maps import create_map, add_map_pin
from backend.worlds import create_world_action, view_graph
from backend.wiki import configure_wiki
from backend.sessions import create_session_note
from backend.search import answer_with_search, answer_question, ai_suggest
from backend.logs import log, get_logs, clear_logs

app = FastAPI(title="vvw-agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
# PERSISTENT BROWSER (LAZY INIT)
# -------------------------------------------------------
_playwright = None
_browser    = None
_page       = None
_page_lock  = asyncio.Lock()


async def get_page():
    global _playwright, _browser, _page
    if _page is not None:
        return _page
    log("api", "Starting Playwright (lazy init)...")
    _playwright = await async_playwright().start()
    _browser    = await _playwright.chromium.launch(headless=False, slow_mo=200)
    _page       = await _browser.new_page()
    await _page.set_viewport_size({"width": 1280, "height": 800})
    log("api", "Logging in...")
    await login(_page)
    log("api", "Browser ready!")
    return _page


def resolve_world(requested: str) -> str:
    world = requested if requested else core.ACTIVE_WORLD
    if not world:
        raise HTTPException(
            status_code=400,
            detail="No world selected. Call POST /worlds/select first."
        )
    return world


# -------------------------------------------------------
# MODELS
# -------------------------------------------------------

class IntentRequest(BaseModel):
    message: str
    chat_history: list = []

class CardRequest(BaseModel):
    world: str = ""
    card_type: str
    name: str
    description: str = ""

class EditCardRequest(BaseModel):
    world: str = ""
    card_name: str
    new_description: str

class DeleteCardRequest(BaseModel):
    world: str = ""
    card_name: str

class LinkCardsRequest(BaseModel):
    world: str = ""
    card_a: str
    card_b: str
    relationship: str = ""

class MapRequest(BaseModel):
    world: str = ""
    map_name: str
    description: str = ""

class MapPinRequest(BaseModel):
    world: str = ""
    map_name: str
    pin_name: str
    linked_card: str = ""

class WorldCreateRequest(BaseModel):
    name: str
    description: str = ""

class WorldSelectRequest(BaseModel):
    world: str

class WorldGraphRequest(BaseModel):
    world: str = ""

class WikiConfigRequest(BaseModel):
    world: str = ""
    wiki_title: str
    is_public: bool = True

class SessionNoteRequest(BaseModel):
    world: str = ""
    title: str
    notes: str

class SearchRequest(BaseModel):
    question: str

class QuestionRequest(BaseModel):
    question: str

class AddKnowledgeRequest(BaseModel):
    category: str
    content: str

class SaveSessionRequest(BaseModel):
    session_name: str = ""

class LoadSessionRequest(BaseModel):
    session_key: str

class NewSessionRequest(BaseModel):
    save_current: bool = True
    session_name: str = ""


# -------------------------------------------------------
# HEALTH & LOGS
# -------------------------------------------------------

@app.get("/health")
async def health():
    browser_alive = _page is not None and not _page.is_closed()
    ollama_alive = False
    try:
        await core.ollama.chat(
            model=core.MODEL,
            messages=[{"role": "user", "content": "ping"}]
        )
        ollama_alive = True
    except:
        pass
    return {
        "api":          "ok",
        "browser":      "connected" if browser_alive else "not started",
        "ollama":       "connected" if ollama_alive else "unreachable",
        "active_world": core.ACTIVE_WORLD or "none selected",
        "model":        core.MODEL,
    }


@app.get("/logs")
async def api_get_logs(since: int = 0):
    entries = get_logs(since_index=since)
    return {"logs": entries, "total": len(get_logs())}


@app.delete("/logs")
async def api_clear_logs():
    clear_logs()
    return {"status": "ok"}


# -------------------------------------------------------
# CHAT SESSION MANAGEMENT
# -------------------------------------------------------

@app.get("/sessions")
async def api_list_sessions():
    """List all saved chat sessions."""
    memory = load_memory()
    return {"sessions": list_sessions(memory)}


@app.post("/sessions/save")
async def api_save_session(req: SaveSessionRequest):
    """Save the current chat history as a named session."""
    memory = load_memory()
    key = save_session(memory, req.session_name)
    if not key:
        return {"status": "skipped", "reason": "No chat history to save"}
    return {"status": "ok", "session_key": key}


@app.post("/sessions/load")
async def api_load_session(req: LoadSessionRequest):
    """Load a saved session back into chat history."""
    memory = load_memory()
    found = load_session(memory, req.session_key)
    if not found:
        raise HTTPException(status_code=404, detail=f"Session '{req.session_key}' not found")
    messages = len(memory["chat_history"])
    return {"status": "ok", "messages_loaded": messages}


@app.post("/sessions/new")
async def api_new_session(req: NewSessionRequest):
    """Start a new session, optionally saving the current one first."""
    memory = load_memory()
    key = start_new_session(memory, req.save_current, req.session_name)
    return {
        "status": "ok",
        "saved_as": key if key else None,
        "message": "New session started. Chat history cleared."
    }


@app.delete("/sessions/{session_key}")
async def api_delete_session(session_key: str):
    """Delete a saved session."""
    memory = load_memory()
    found = delete_session(memory, session_key)
    if not found:
        raise HTTPException(status_code=404, detail=f"Session '{session_key}' not found")
    return {"status": "ok"}


@app.get("/sessions/{session_key}")
async def api_get_session(session_key: str):
    """Get a specific session's messages."""
    memory = load_memory()
    sessions = memory.get("sessions", {})
    if session_key not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_key}' not found")
    return sessions[session_key]


# -------------------------------------------------------
# KNOWLEDGE & LORE
# -------------------------------------------------------

@app.get("/knowledge/files")
async def api_knowledge_files():
    """List all files in the knowledge folder."""
    return {"files": list_knowledge_files()}


@app.get("/knowledge/view")
async def api_knowledge_view():
    memory = load_memory()
    return {
        "files":   load_knowledge_files(),
        "memory":  memory.get("knowledge", {}),
        "context": build_context(memory)
    }


@app.post("/knowledge/add")
async def api_knowledge_add(req: AddKnowledgeRequest):
    memory = load_memory()
    add_knowledge(memory, req.category, req.content)
    save_memory(memory)
    return {"status": "ok"}


@app.post("/knowledge/upload")
async def api_knowledge_upload(file: UploadFile = File(...)):
    """
    Upload a lore file (.md or .txt) into the knowledge folder.
    The agent will use it as context from the next request onward.
    """
    if not file.filename.endswith((".md", ".txt")):
        raise HTTPException(status_code=400, detail="Only .md and .txt files are supported")

    dest = Path("knowledge") / file.filename
    dest.parent.mkdir(exist_ok=True)

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    log("api", f"Uploaded lore file: {file.filename}")
    return {
        "status":   "ok",
        "filename": file.filename,
        "message":  f"Lore file '{file.filename}' uploaded. It will be used as context immediately."
    }


@app.delete("/knowledge/files/{filename}")
async def api_delete_knowledge_file(filename: str):
    """Delete a file from the knowledge folder."""
    target = Path("knowledge") / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    target.unlink()
    return {"status": "ok"}


# -------------------------------------------------------
# MEMORY
# -------------------------------------------------------

@app.get("/memory")
async def api_memory_view():
    return load_memory()


@app.delete("/memory")
async def api_memory_wipe():
    """Wipe memory but preserve saved sessions."""
    memory = load_memory()
    wipe_memory(memory)
    return {"status": "ok", "message": "Memory wiped. Sessions preserved."}


# -------------------------------------------------------
# INTENT
# -------------------------------------------------------

@app.post("/intent")
async def api_intent(req: IntentRequest):
    memory = load_memory()
    result  = await parse_intent(req.message, memory, req.chat_history)
    missing = await get_missing_info(result, memory)
    return {"intent": result, "missing_field": missing}


# -------------------------------------------------------
# WORLD MANAGEMENT
# -------------------------------------------------------

@app.get("/worlds")
async def api_list_worlds():
    async with _page_lock:
        pg = await get_page()
        worlds = await list_worlds(pg)
    return {"worlds": worlds}


@app.post("/worlds/select")
async def api_select_world(req: WorldSelectRequest):
    async with _page_lock:
        pg = await get_page()
        await go_to_world(pg, req.world)
    core.ACTIVE_WORLD = req.world
    log("api", f"Active world: {req.world}")
    return {"status": "ok", "active_world": core.ACTIVE_WORLD}


@app.post("/worlds/create")
async def api_worlds_create(req: WorldCreateRequest):
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await create_world_action(pg, memory, req.name, req.description)
    save_memory(memory)
    return {"status": "ok"}


@app.post("/worlds/graph")
async def api_worlds_graph(req: WorldGraphRequest):
    world = resolve_world(req.world)
    async with _page_lock:
        pg = await get_page()
        await view_graph(pg, world)
    return {"status": "ok"}


# -------------------------------------------------------
# CARDS
# -------------------------------------------------------

@app.post("/cards/create")
async def api_cards_create(req: CardRequest):
    world  = resolve_world(req.world)
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await create_card(pg, memory, world, req.card_type, req.name, req.description)
    # Extract lore and store it automatically
    await extract_and_store_lore(req.name, req.card_type, req.description, memory)
    save_memory(memory)
    log("api", f"Created card: {req.name} ({req.card_type})")
    return {"status": "ok", "card": req.name, "world": world}


@app.post("/cards/edit")
async def api_cards_edit(req: EditCardRequest):
    world  = resolve_world(req.world)
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await edit_card(pg, memory, world, req.card_name, req.new_description)
    save_memory(memory)
    return {"status": "ok"}


@app.post("/cards/delete")
async def api_cards_delete(req: DeleteCardRequest):
    world  = resolve_world(req.world)
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await delete_card(pg, memory, world, req.card_name)
    save_memory(memory)
    return {"status": "ok"}


@app.post("/cards/link")
async def api_cards_link(req: LinkCardsRequest):
    world  = resolve_world(req.world)
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await link_cards(pg, memory, world, req.card_a, req.card_b, req.relationship)
    save_memory(memory)
    return {"status": "ok"}


# -------------------------------------------------------
# MAPS
# -------------------------------------------------------

@app.post("/maps/create")
async def api_maps_create(req: MapRequest):
    world  = resolve_world(req.world)
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await create_map(pg, memory, world, req.map_name, req.description)
    save_memory(memory)
    return {"status": "ok"}


@app.post("/maps/pin")
async def api_maps_pin(req: MapPinRequest):
    world  = resolve_world(req.world)
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await add_map_pin(pg, memory, world, req.map_name, req.pin_name, req.linked_card)
    save_memory(memory)
    return {"status": "ok"}


# -------------------------------------------------------
# WIKI & SESSIONS
# -------------------------------------------------------

@app.post("/wiki/configure")
async def api_wiki_configure(req: WikiConfigRequest):
    world  = resolve_world(req.world)
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await configure_wiki(pg, memory, world, req.wiki_title, req.is_public)
    save_memory(memory)
    return {"status": "ok"}


@app.post("/sessions/create")
async def api_sessions_create(req: SessionNoteRequest):
    world  = resolve_world(req.world)
    memory = load_memory()
    async with _page_lock:
        pg = await get_page()
        await create_session_note(pg, memory, world, req.title, req.notes)
    save_memory(memory)
    return {"status": "ok"}


# -------------------------------------------------------
# SEARCH & AI
# -------------------------------------------------------

@app.post("/search")
async def api_search(req: SearchRequest):
    memory = load_memory()
    answer = await answer_with_search(req.question, memory)
    return {"answer": answer}


@app.post("/ask")
async def api_ask(req: QuestionRequest):
    memory = load_memory()
    answer = await answer_question(req.question, memory)
    return {"answer": answer}


@app.get("/suggest")
async def api_suggest():
    memory = load_memory()
    return {"suggestions": await ai_suggest(memory)}