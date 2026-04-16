"""
Browser module — login, world navigation, world selection.
Vision functions are in vision.py to avoid circular imports.
"""
import asyncio
from playwright.async_api import Page
from .agent_core import EMAIL, PASSWORD, BASE_URL
from .vision import vision_click
from .logs import log
import backend.agent_core as core


async def login(page: Page):
    log("playwright", "Logging in...")
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.get_by_role("button", name="Continue with Email").click()
    await page.wait_for_selector("input#email", timeout=5000)
    await page.fill("input#email", EMAIL)
    await page.fill("input#password", PASSWORD)
    await page.get_by_role("button", name="Sign In").click()
    await page.wait_for_load_state("networkidle")
    log("playwright", "Logged in successfully")


async def go_to_world(page: Page, world_name: str):
    """Navigate to a world and open the editor. Skips if already inside a world."""
    current_url = page.url
    if "/worlds/" in current_url and current_url.split("/worlds/")[-1] not in ("", "worlds"):
        # Already inside a world — navigate directly to editor
        world_id = current_url.split("/worlds/")[1].split("/")[0]
        if world_name.lower().replace(" ", "-") in world_id.lower() or True:
            editor_url = f"{BASE_URL}/worlds/{world_id}/editor"
            if page.url != editor_url:
                await page.goto(editor_url, wait_until="networkidle")
            log("playwright", f"Already in world, opened editor")
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
    except Exception as e:
        log("playwright", f"World nav fallback: {e}", "warn")
        await vision_click(page, f"the world card called {world_name}")
        await page.wait_for_load_state("networkidle")

    # Navigate directly to editor via URL
    current_url = page.url
    world_id = current_url.split("/worlds/")[1].split("/")[0]
    await page.goto(f"{BASE_URL}/worlds/{world_id}/editor", wait_until="networkidle")
    log("playwright", f"Opened editor for world: {world_name}")

    # Update active world
    core.ACTIVE_WORLD = world_name


async def pick_world(page: Page, memory: dict) -> str:
    """Show list of worlds and return the selected one. For CLI use only."""
    await page.goto(f"{BASE_URL}/worlds", wait_until="networkidle")
    await page.wait_for_selector("h3.font-medium", timeout=5000)

    world_elements = await page.query_selector_all("h3.font-medium")
    worlds = []
    for el in world_elements:
        text = (await el.inner_text()).strip()
        if text:
            worlds.append(text)

    if not worlds:
        name = input("  Agent: I couldn't read your worlds. Name? ").strip()
        return name

    if len(worlds) == 1:
        print(f"  Agent: Opening {worlds[0]}...\n")
        await go_to_world(page, worlds[0])
        return worlds[0]

    print("\n  Agent: Your worlds:")
    for i, w in enumerate(worlds, 1):
        print(f"    {i}. {w}")
    print()

    while True:
        choice = input("  Which world? (name or number): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(worlds):
                await go_to_world(page, worlds[idx])
                return worlds[idx]
        else:
            match = next((w for w in worlds if choice.lower() in w.lower()), None)
            if match:
                await go_to_world(page, match)
                return match
        print("  Didn't recognise that, try again.")


async def list_worlds(page: Page) -> list[str]:
    """Return list of world names. For API use."""
    await page.goto(f"{BASE_URL}/worlds", wait_until="networkidle")
    await page.wait_for_selector("h3.font-medium", timeout=5000)
    world_elements = await page.query_selector_all("h3.font-medium")
    worlds = []
    for el in world_elements:
        text = (await el.inner_text()).strip()
        if text:
            worlds.append(text)
    return worlds