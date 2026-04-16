"""
Vision module — uses llava to find and interact with UI elements
when CSS selectors fail. Separated from browser.py to avoid
circular imports between browser.py and cards.py.
"""
import asyncio
import base64
import json
import re

from playwright.async_api import Page
from .agent_core import VISION_MODEL, ollama
from .logs import log


async def screenshot_b64(page: Page) -> str:
    return base64.b64encode(await page.screenshot(type="png")).decode("utf-8")


async def vision_find(page: Page, goal: str) -> dict | None:
    dims = await page.evaluate("() => ({ w: window.innerWidth, h: window.innerHeight })")
    try:
        b64 = await screenshot_b64(page)
        prompt = (
            f"Browser screenshot {dims['w']}x{dims['h']}px.\n"
            f"Goal: {goal}\n"
            'Reply ONLY with JSON: {"x": 320, "y": 215, "description": "the button"}\n'
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
        log("playwright", "Vision timed out", "warn")
    except Exception as e:
        log("playwright", f"Vision error: {e}", "error")
    return None


async def vision_click(page: Page, goal: str) -> bool:
    log("playwright", f"Vision click: {goal}")
    result = await vision_find(page, goal)
    if result:
        try:
            await page.mouse.click(int(result["x"]), int(result["y"]))
            await page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            log("playwright", f"Vision click failed: {e}", "error")
    return False


async def vision_fill(page: Page, goal: str, value: str) -> bool:
    log("playwright", f"Vision fill: {goal}")
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
            log("playwright", f"Vision fill failed: {e}", "error")
    return False