from playwright.async_api import Page
from .vision import vision_click, vision_fill
from .browser import go_to_world
from .memory import log_action
from .logs import log
 
 
async def create_session_note(page: Page, memory: dict, world: str, title: str, notes: str):
    await go_to_world(page, world)
    await vision_click(page, "the Sessions or Notes navigation link")
    await vision_click(page, "the New Session or Add Note button")
    await vision_fill(page, "session title field", title)
    await vision_fill(page, "notes content field", notes)
    await vision_click(page, "Save button")
    await page.wait_for_load_state("networkidle")
    log_action(memory, "Created session note", f"{title} in {world}")
    log("playwright", f"Created session note: {title}")