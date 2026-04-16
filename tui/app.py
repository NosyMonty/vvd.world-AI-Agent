"""
vvw-agent Terminal UI (Textual)
Hybrid layout: sidebar menu + command bar + live log panel + intent viewer

Install: pip install textual aiohttp
Run:     python tui/app.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Button, Input, RichLog,
    Label, Static, ListView, ListItem
)
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.screen import ModalScreen

from backend.intent import parse_intent, get_missing_info
from backend.memory import (
    load_memory, save_memory, wipe_memory,
    save_session, load_session, list_sessions, start_new_session
)
from backend.knowledge import build_context, list_knowledge_files
import backend.agent_core as core


API_BASE = "http://localhost:8000"

HELP_TEXT = """\
[bold]vvd.world AI Agent — Commands[/bold]

[bold cyan]CARDS[/bold cyan]
  create a character card for [name]
  create a location called [name]
  delete the card for [name]
  edit [card name] description to [new text]
  link [card a] and [card b] as [relationship]

[bold cyan]MAPS[/bold cyan]
  create a map called [name]
  add a pin for [place] on the [map] map

[bold cyan]D&D QUESTIONS[/bold cyan]
  how does the silence spell work in D&D 5e?
  what monsters live in the underdark?
  what are the rules for grappling?

[bold cyan]CAMPAIGN[/bold cyan]
  what do you know about my campaign?
  remember that [lore fact]
  suggest what I should create next

[bold cyan]SESSIONS[/bold cyan]
  new session           — start fresh (saves current)
  save session [name]   — save current chat
  load session [name]   — recall a previous session

[bold cyan]SPECIAL[/bold cyan]
  help        — show this
  wipe memory — clear memory (keeps sessions)
  quit        — exit

[dim]Ctrl+L = clear log | Ctrl+C = quit[/dim]
"""


class SessionListScreen(ModalScreen):
    """Modal popup showing saved sessions to load."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, sessions: list):
        super().__init__()
        self.sessions = sessions

    def compose(self) -> ComposeResult:
        with Vertical(id="session-modal"):
            yield Label("[bold]Saved Sessions[/bold] (press Enter to load, Esc to cancel)")
            if self.sessions:
                lv = ListView()
                for s in self.sessions:
                    label = f"{s['name']}  [{s['messages']} messages | {s['timestamp']}]"
                    lv.append(ListItem(Label(label), id=f"session-{s['key']}"))
                yield lv
            else:
                yield Label("[dim]No saved sessions yet.[/dim]")

    def on_list_view_selected(self, event: ListView.Selected):
        key = event.item.id.replace("session-", "")
        self.dismiss(key)


class VVWAgentTUI(App):
    """vvd.world AI Agent — Terminal UI"""

    CSS = """
    Screen { layout: vertical; }

    #body { layout: horizontal; height: 1fr; }

    #sidebar {
        width: 26;
        border-right: solid $primary;
        padding: 1;
    }
    #sidebar Button {
        width: 100%;
        margin-bottom: 1;
    }
    #sidebar Label { margin-bottom: 1; }

    #main-panel { layout: vertical; width: 1fr; }

    #log-panel {
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }

    #intent-panel {
        height: 7;
        border: solid $warning;
        padding: 1;
    }

    #command-bar {
        height: 3;
        border-top: solid $primary;
        padding: 0 1;
    }

    #status-bar {
        height: 1;
        background: $primary;
        color: $background;
        padding: 0 1;
    }

#session-modal {
        width: 80;
        height: 24;
        border: solid $accent;
        background: $surface;
        padding: 2;
        margin: 4 8;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit",      "Quit"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
    ]

    def __init__(self):
        super().__init__()
        self.memory        = load_memory()
        self.chat_history  = list(self.memory.get("chat_history", []))
        self.pending_intent = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._status_text(), id="status-bar")

        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Label("[bold]Quick Actions[/bold]")
                yield Button("➕ Create Card",     id="btn_create_card",  variant="primary")
                yield Button("🗺  Create Map",      id="btn_create_map",   variant="primary")
                yield Button("🔗 Link Cards",       id="btn_link",         variant="default")
                yield Button("🌐 View Graph",       id="btn_graph",        variant="default")
                yield Button("💡 Suggest Ideas",    id="btn_suggest",      variant="success")
                yield Button("📚 View Knowledge",   id="btn_knowledge",    variant="default")
                yield Label("[bold]Sessions[/bold]")
                yield Button("💾 Save Session",     id="btn_save_session", variant="default")
                yield Button("📂 Load Session",     id="btn_load_session", variant="default")
                yield Button("🆕 New Session",      id="btn_new_session",  variant="default")
                yield Button("📤 Upload Lore",      id="btn_upload_lore",  variant="default")
                yield Label("[bold]System[/bold]")
                yield Button("🧹 Wipe Memory",      id="btn_wipe",         variant="error")
                yield Button("❓ Help",              id="btn_help",         variant="default")

            with Vertical(id="main-panel"):
                yield RichLog(id="log-panel", highlight=True, markup=True)
                with Vertical(id="intent-panel"):
                    yield Label("[bold yellow]Last Intent[/bold yellow]")
                    yield Static("None yet", id="intent-display")

        with Horizontal(id="command-bar"):
            yield Input(placeholder="Type a command and press Enter...", id="command-input")

        yield Footer()

    def _status_text(self) -> str:
        cards  = len(self.memory.get("created_cards", []))
        world  = core.ACTIVE_WORLD or "none"
        msgs   = len(self.memory.get("chat_history", []))
        return f"  Model: {core.MODEL}  |  World: {world}  |  Cards: {cards}  |  Messages: {msgs}"

    def on_mount(self):
        self._log(
            "[green bold]vvd.world AI Agent TUI ready![/green bold]\n"
            f"Active world: [bold]{core.ACTIVE_WORLD or 'not selected'}[/bold]\n"
            f"Sessions saved: [bold]{len(list_sessions(self.memory))}[/bold]\n"
            f"Knowledge files: [bold]{len(list_knowledge_files())}[/bold]\n\n"
            "Type a command below or use the sidebar. Type [bold]help[/bold] for commands.\n"
        )

    def _log(self, text: str):
        self.query_one("#log-panel", RichLog).write(text)

    def _update_status(self):
        self.query_one("#status-bar", Static).update(self._status_text())

    # -------------------------------------------------------
    # BUTTON HANDLERS
    # -------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        inp = self.query_one("#command-input", Input)

        prefill_map = {
            "btn_create_card": "create a character card for ",
            "btn_create_map":  "create a map called ",
            "btn_link":        "link  and  as ",
            "btn_graph":       f"show me the relationship graph",
            "btn_suggest":     "suggest what I should create next",
            "btn_knowledge":   "what do you know about my campaign?",
            "btn_help":        "help",
        }

        if bid in prefill_map:
            inp.value = prefill_map[bid]
            inp.focus()
            return

        if bid == "btn_wipe":
            self._action_wipe()
            return

        if bid == "btn_save_session":
            self._action_save_session()
            return

        if bid == "btn_load_session":
            self._action_show_sessions()
            return

        if bid == "btn_new_session":
            self._action_new_session()
            return

        if bid == "btn_upload_lore":
            self._log(
                "[yellow]Lore Upload:[/yellow] Use the API endpoint to upload files:\n"
                "  POST http://localhost:8000/knowledge/upload\n"
                "  or drag a .md file into your knowledge/ folder directly."
            )

    # -------------------------------------------------------
    # SESSION ACTIONS
    # -------------------------------------------------------

    def _action_save_session(self, name: str = ""):
        if not self.memory.get("chat_history"):
            self._log("[yellow]Nothing to save — chat history is empty.[/yellow]")
            return
        key = save_session(self.memory, name)
        self._log(f"[green]Session saved as:[/green] [bold]{key}[/bold]")

    def _action_new_session(self):
        key = start_new_session(self.memory, save_current=True)
        self.chat_history  = []
        self.pending_intent = None
        saved_msg = f" Previous session saved as: [bold]{key}[/bold]" if key else ""
        self._log(f"[green]New session started![/green]{saved_msg}\n"
                  "Chat history cleared. Knowledge and lore are still active.\n")
        self._update_status()

    def _action_show_sessions(self):
        sessions = list_sessions(self.memory)
        self.push_screen(SessionListScreen(sessions), self._on_session_selected)

    def _on_session_selected(self, session_key):
        if not session_key:
            return
        found = load_session(self.memory, session_key)
        if found:
            self.chat_history = list(self.memory["chat_history"])
            self._log(f"[green]Session loaded:[/green] [bold]{session_key}[/bold] "
                      f"({len(self.chat_history)} messages)\n")
            # Replay last few messages for context
            for msg in self.chat_history[-4:]:
                role  = "You" if msg["role"] == "user" else "Agent"
                color = "cyan" if msg["role"] == "user" else "green"
                self._log(f"[{color}]{role}:[/{color}] {msg['content'][:200]}")
        else:
            self._log(f"[red]Session not found:[/red] {session_key}")
        self._update_status()

    def _action_wipe(self):
        wipe_memory(self.memory)
        self.chat_history   = []
        self.pending_intent = None
        self._log("[yellow]Memory wiped! Sessions are preserved.[/yellow]\n")
        self._update_status()

    # -------------------------------------------------------
    # COMMAND HANDLING
    # -------------------------------------------------------

    async def on_input_submitted(self, event: Input.Submitted):
        user_input = event.value.strip()
        if not user_input:
            return

        self.query_one("#command-input", Input).value = ""
        self._log(f"\n[bold cyan]You:[/bold cyan] {user_input}")

        lower = user_input.lower()

        # Special commands
        if lower in ("quit", "exit"):
            self.exit()
            return

        if lower == "help":
            self._log(HELP_TEXT)
            return

        if lower == "wipe memory":
            self._action_wipe()
            return

        if lower.startswith("new session"):
            name = user_input[11:].strip()
            self._action_new_session()
            return

        if lower.startswith("save session"):
            name = user_input[12:].strip()
            self._action_save_session(name)
            return

        if lower.startswith("load session"):
            key = user_input[12:].strip()
            if key:
                found = load_session(self.memory, key)
                if found:
                    self.chat_history = list(self.memory["chat_history"])
                    self._log(f"[green]Session loaded:[/green] {key}")
                else:
                    self._log(f"[red]Session not found:[/red] {key}")
                    sessions = list_sessions(self.memory)
                    if sessions:
                        self._log("Available: " + ", ".join(s["key"] for s in sessions))
            else:
                self._action_show_sessions()
            return

        # Add to chat history
        self.chat_history.append({"role": "user", "content": user_input})
        self.memory["chat_history"] = self.chat_history[-20:]

        self._log("[dim]Parsing intent...[/dim]")

        try:
            if self.pending_intent:
                updated = await parse_intent(
                    f"The user answered: {user_input}. "
                    f"Update this intent: {self.pending_intent}",
                    self.memory, self.chat_history
                )
                self.pending_intent = updated
            else:
                self.pending_intent = await parse_intent(
                    user_input, self.memory, self.chat_history
                )

            # Show intent
            self.query_one("#intent-display", Static).update(
                f"[bold]{self.pending_intent.get('intent')}[/bold]  "
                f"confidence: {self.pending_intent.get('confidence', '?')}\n"
                f"params: {self.pending_intent.get('params', {})}"
            )

            missing = await get_missing_info(self.pending_intent, self.memory)
            if missing:
                self._log(f"[green]Agent:[/green] {missing}")
                self.chat_history.append({"role": "assistant", "content": missing})
            else:
                await self._execute_via_api()
                self.pending_intent = None

        except Exception as e:
            self._log(f"[red]Error: {e}[/red]")
            self.pending_intent = None

        self.memory["chat_history"] = self.chat_history[-20:]
        save_memory(self.memory)
        self._update_status()

    # -------------------------------------------------------
    # API EXECUTION
    # -------------------------------------------------------

    async def _execute_via_api(self):
        import aiohttp

        intent      = self.pending_intent
        intent_name = intent.get("intent")
        params      = intent.get("params", {})
        world       = params.get("world") or core.ACTIVE_WORLD

        ROUTES = {
            "create_card":    ("POST", f"{API_BASE}/cards/create",
                               {"world": world,
                                "card_type":    params.get("card_type", "character"),
                                "name":         params.get("name", ""),
                                "description":  params.get("description", "")}),
            "edit_card":      ("POST", f"{API_BASE}/cards/edit",
                               {"world": world,
                                "card_name":        params.get("card_name", ""),
                                "new_description":  params.get("new_description", "")}),
            "delete_card":    ("POST", f"{API_BASE}/cards/delete",
                               {"world": world,
                                "card_name": params.get("card_name", "")}),
            "link_cards":     ("POST", f"{API_BASE}/cards/link",
                               {"world": world,
                                "card_a":       params.get("card_a", ""),
                                "card_b":       params.get("card_b", ""),
                                "relationship": params.get("relationship", "")}),
            "create_map":     ("POST", f"{API_BASE}/maps/create",
                               {"world": world,
                                "map_name":    params.get("map_name", ""),
                                "description": params.get("description", "")}),
            "add_map_pin":    ("POST", f"{API_BASE}/maps/pin",
                               {"world": world,
                                "map_name":    params.get("map_name", ""),
                                "pin_name":    params.get("pin_name", ""),
                                "linked_card": params.get("linked_card", "")}),
            "create_world":   ("POST", f"{API_BASE}/worlds/create",
                               {"name":        params.get("name", ""),
                                "description": params.get("description", "")}),
            "switch_world":   ("POST", f"{API_BASE}/worlds/select",
                               {"world": params.get("world", "")}),
            "view_graph":     ("POST", f"{API_BASE}/worlds/graph",
                               {"world": world}),
            "configure_wiki": ("POST", f"{API_BASE}/wiki/configure",
                               {"world":      world,
                                "wiki_title": params.get("wiki_title", ""),
                                "is_public":  params.get("is_public", True)}),
            "create_session_note": ("POST", f"{API_BASE}/sessions/create",
                               {"world": world,
                                "title": params.get("title", ""),
                                "notes": params.get("notes", "")}),
            "web_search":     ("POST", f"{API_BASE}/search",
                               {"question": params.get("question", "")}),
            "ask_question":   ("POST", f"{API_BASE}/ask",
                               {"question": params.get("question", "")}),
            "ai_suggest":     ("GET",  f"{API_BASE}/suggest", None),
            "view_knowledge": ("GET",  f"{API_BASE}/knowledge/view", None),
            "add_knowledge":  ("POST", f"{API_BASE}/knowledge/add",
                               {"category": params.get("category", "lore"),
                                "content":  params.get("content", "")}),
            "new_session":    None,
            "list_sessions":  None,
            "load_session":   None,
            "upload_lore":    None,
            "help":           None,
        }

        if intent_name == "help":
            self._log(HELP_TEXT)
            return

        if intent_name == "new_session":
            self._action_new_session()
            return

        if intent_name == "list_sessions":
            sessions = list_sessions(self.memory)
            if sessions:
                lines = "\n".join(
                    f"  [bold]{s['name']}[/bold] — {s['messages']} messages, {s['timestamp']}"
                    for s in sessions
                )
                self._log(f"[green]Saved sessions:[/green]\n{lines}")
            else:
                self._log("[yellow]No saved sessions yet.[/yellow]")
            return

        if intent_name == "load_session":
            key = params.get("session_key", "")
            self._on_session_selected(key)
            return

        if intent_name == "unknown":
            self._log("[yellow]Agent:[/yellow] I'm not sure what you want. Try rephrasing!")
            return

        if intent_name not in ROUTES or ROUTES[intent_name] is None:
            self._log(f"[yellow]Agent:[/yellow] Intent '{intent_name}' not wired to API yet.")
            return

        method, url, body = ROUTES[intent_name]
        self._log(f"[dim]→ {method} {url}[/dim]")

        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url) as resp:
                        if resp.content_type == "application/json":
                            data = await resp.json()
                        else:
                            text = await resp.text()
                            self._log(f"[red]API Error (non-JSON):[/red] {text[:300]}")
                            return
                else:
                    async with session.post(url, json=body) as resp:
                        if resp.content_type == "application/json":
                            data = await resp.json()
                        else:
                            text = await resp.text()
                            self._log(f"[red]API Error (non-JSON):[/red] {text[:300]}")
                            return

            # Format response
            if "answer" in data:
                reply = data["answer"]
            elif "suggestions" in data:
                reply = data["suggestions"]
            elif "knowledge" in data or "context" in data:
                ctx = data.get("context", data.get("knowledge", ""))
                reply = ctx[:1000] if ctx else "No knowledge stored yet."
            elif data.get("status") == "ok":
                card = data.get("card", "")
                reply = f"Done! ✓{' Created: ' + card if card else ''}"
            else:
                reply = str(data)

            self._log(f"[green]Agent:[/green] {reply}")
            self.chat_history.append({"role": "assistant", "content": reply})

            # If a world was switched, update local state
            if intent_name == "switch_world" and data.get("status") == "ok":
                core.ACTIVE_WORLD = params.get("world", core.ACTIVE_WORLD)

        except aiohttp.ClientConnectorError:
            self._log(
                "[red]Cannot connect to API.[/red]\n"
                "[dim]Make sure uvicorn api.main:app is running.[/dim]"
            )
        except Exception as e:
            self._log(f"[red]API Error:[/red] {e}")

    # -------------------------------------------------------
    # KEYBINDINGS
    # -------------------------------------------------------

    def action_clear_log(self):
        self.query_one("#log-panel", RichLog).clear()


if __name__ == "__main__":
    VVWAgentTUI().run()