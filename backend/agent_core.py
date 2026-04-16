import os
from pathlib import Path
from dotenv import load_dotenv
from ollama import AsyncClient
 
load_dotenv()
 
EMAIL        = os.getenv("VVW_EMAIL")
PASSWORD     = os.getenv("VVW_PASSWORD")
MODEL        = os.getenv("OLLAMA_MODEL", "vvd-agent")
VISION_MODEL = os.getenv("VISION_MODEL", "llava")
BASE_URL     = "https://www.vvd.world"
 
ollama        = AsyncClient()
MEMORY_FILE   = Path("memory.json")
KNOWLEDGE_DIR = Path("knowledge")
 
# Updated by world selection at runtime
ACTIVE_WORLD  = ""
 