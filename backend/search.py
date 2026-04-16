import os
import asyncio
from .agent_core import MODEL, ollama
from .knowledge import build_context
from .logs import log
 
 
async def answer_with_search(question: str, memory: dict) -> str:
    """Search the web via Tavily then answer using campaign context."""
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise Exception("TAVILY_API_KEY not set in .env")
        client = TavilyClient(api_key=api_key)
        log("agent", f"Web search: {question}")
        results = await asyncio.to_thread(
            client.search, question, max_results=4, search_depth="advanced"
        )
        results_text = "\n\n".join(
            f"Title: {r['title']}\nSummary: {r['content']}\nSource: {r['url']}"
            for r in results.get("results", [])
        )
    except Exception as e:
        log("agent", f"Search failed: {e}", "warn")
        results_text = "Web search unavailable."
 
    context = build_context(memory)
    response = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
        "You are a knowledgeable D&D assistant.\n\n"
        f"CAMPAIGN KNOWLEDGE:\n{context}\n\n"
        f"WEB SEARCH RESULTS:\n{results_text}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using both sources. Be concise and directly useful to a dungeon master."
    )}])
    return response["message"]["content"].strip()
 
 
async def answer_question(question: str, memory: dict) -> str:
    """Answer a campaign-specific question using stored knowledge."""
    context = build_context(memory)
    response = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
        "You are a knowledgeable D&D worldbuilding assistant.\n\n"
        f"CAMPAIGN KNOWLEDGE:\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer helpfully from campaign knowledge.\n"
        "NEVER give step-by-step site instructions — the agent handles all actions.\n"
        "If it is a D&D rules question suggest searching the web instead.\n"
        "If you don't know, say so honestly."
    )}])
    return response["message"]["content"].strip()
 
 
async def ai_suggest(memory: dict) -> str:
    """Generate creative suggestions for new cards and maps."""
    context = build_context(memory)
    response = await ollama.chat(model=MODEL, messages=[{"role": "user", "content": (
        "You are a creative D&D worldbuilding assistant.\n\n"
        f"CAMPAIGN KNOWLEDGE:\n{context}\n\n"
        "Suggest 5 specific NEW things to create as cards or maps that don't exist yet.\n"
        "Make them creative and fit the world's style and tone.\n"
        "Format: TYPE | NAME | one sentence description."
    )}])
    return response["message"]["content"].strip()