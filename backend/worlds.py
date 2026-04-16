from playwright.async_api import Page
from .vision import vision_click, vision_fill
from .browser import go_to_world
from .memory import log_action
from .logs import log
from .agent_core import BASE_URL


async def view_graph(page: Page, world: str):
    await go_to_world(page, world)
    await vision_click(page, "the Graph or Relationship Graph navigation link")
    await page.wait_for_load_state("networkidle")
    log("playwright", f"Opened graph for: {world}")


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
    log("playwright", f"Created world: {name}")