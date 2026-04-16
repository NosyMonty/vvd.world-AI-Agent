import asyncio
import re
from playwright.async_api import Page
from .vision import vision_click, vision_fill
from .browser import go_to_world
from .memory import log_action
from .logs import log
import backend.agent_core as core
 
 
async def do_create_card_steps(page: Page, card_type: str, name: str, description: str = ""):
    """Runs the browser steps to create a card. Assumes already in the world editor."""
 
    # Step 1: Click Card button
    log("playwright", f"Clicking Card button")
    await page.get_by_role("button", name="Card", exact=True).click()
    await asyncio.sleep(0.5)
 
    # Step 2: Select card type
    log("playwright", f"Selecting type: {card_type}")
    type_clicked = False
    for variant in [card_type.title(), card_type.lower(), card_type.capitalize()]:
        try:
            await page.get_by_role("button", name=variant, exact=True).click()
            type_clicked = True
            break
        except:
            continue
    if not type_clicked:
        try:
            await page.click(f"button:has-text('{card_type}')", timeout=3000)
        except:
            await vision_click(page, f"the {card_type} card type button")
    await asyncio.sleep(0.5)
 
    # Step 3: Fill in card name
    log("playwright", f"Setting name: {name}")
    name_filled = False
    for attempt in [
        lambda: page.get_by_role("textbox", name="New Card"),
        lambda: page.locator("input[placeholder*='New Card' i]"),
        lambda: page.locator("input[placeholder*='name' i]"),
    ]:
        try:
            el = attempt()
            await el.click()
            await el.fill(name)
            name_filled = True
            break
        except:
            continue
    if not name_filled:
        await vision_fill(page, "card name field", name)
 
    # Step 4: Add description
    if description:
        log("playwright", "Adding description")
        try:
            await page.get_by_role("button", name="Text").click()
            await asyncio.sleep(0.5)
            await page.get_by_role("paragraph").filter(
                has_text=re.compile(r"^$")
            ).click()
            await page.locator(".tiptap.ProseMirror.w-full").fill(description)
        except:
            try:
                await page.locator(".tiptap.ProseMirror.w-full").fill(description)
            except:
                await vision_fill(page, "description text editor", description)
 
    # Step 5: Close — autosaves
    log("playwright", "Closing card")
    await asyncio.sleep(0.5)
    try:
        await page.get_by_role("button", name="Close").click()
    except:
        try:
            await page.click("button:has-text('Close')", timeout=2000)
        except:
            await page.keyboard.press("Escape")
 
    await page.wait_for_load_state("networkidle")
    log("playwright", f"Card '{name}' created!")
 
 
async def create_card(page: Page, memory: dict, world: str, card_type: str,
                      name: str, description: str = "", extra: str = ""):
    current_url = page.url
    if "/worlds/" in current_url and current_url.split("/worlds/")[-1] not in ("", "worlds"):
        log("playwright", "Already in world, skipping navigation")
    else:
        await go_to_world(page, world)
 
    core.ACTIVE_WORLD = world
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
    log("playwright", f"Edited card: {card_name}")
 
 
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
    log("playwright", f"Deleted card: {card_name}")
 
 
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
    log("playwright", f"Linked {card_a} → {card_b}")