from playwright.async_api import Page
from .vision import vision_click, vision_fill
from .browser import go_to_world
from .memory import log_action
from .logs import log


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
    log("playwright", f"Created map: {map_name}")


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
    log("playwright", f"Added pin: {pin_name}")