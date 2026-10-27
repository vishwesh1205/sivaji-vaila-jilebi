import asyncio
import json
import threading
from collections import deque
from datetime import datetime
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.subscribers: list[asyncio.Queue] = []
        self.recent: deque[dict[str, Any]] = deque(maxlen=100)

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "id": int(datetime.utcnow().timestamp() * 1000),
            "type": event_type,
            "at": datetime.utcnow().isoformat(),
            **payload,
        }
        with self.lock:
            self.recent.append(event)
            for q in list(self.subscribers):
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        with self.lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def snapshot(self) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.recent)


bus = EventBus()


def sse_format(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
