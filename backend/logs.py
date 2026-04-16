"""
In-memory log queue for the API.
Both Playwright actions and AI intent parsing write here.
The /logs endpoint lets the frontend poll for new entries.
"""
from collections import deque
from datetime import datetime
 
_log_queue: deque = deque(maxlen=500)
 
 
def log(source: str, message: str, level: str = "info"):
    """Write a log entry."""
    _log_queue.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "source": source,   # "playwright" | "intent" | "api" | "agent"
        "level": level,     # "info" | "warn" | "error"
        "message": message
    })
 
 
def get_logs(since_index: int = 0) -> list:
    """Return all logs from a given index onward."""
    all_logs = list(_log_queue)
    return all_logs[since_index:]
 
 
def clear_logs():
    _log_queue.clear()