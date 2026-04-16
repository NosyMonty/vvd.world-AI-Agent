from playwright.async_api import Page
from .vision import vision_click, vision_fill
from .browser import go_to_world
from .memory import log_action
from .logs import log


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
    log("playwright", f"Configured wiki: {wiki_title}")