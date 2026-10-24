from __future__ import annotations
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional

class JobEventBroker:
    def __init__(self):
        self._queues: Dict[str, List[asyncio.Queue]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}

    def clear(self) -> None:
        self._queues.clear()
        self._history.clear()

    def publish(self, job_id: str, event_type: str, data: Dict[str, Any]) -> None:
        hist = self._history.setdefault(job_id, [])
        event_id = str(len(hist) + 1)
        item = {"id": event_id, "event": event_type, "data": data}
        hist.append(item)
        if job_id in self._queues:
            for q in list(self._queues[job_id]):
                q.put_nowait(item)

    async def subscribe(
        self,
        job_id: str,
        last_event_id: Optional[str] = None,
        heartbeat_sec: float = 15.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(job_id, []).append(q)
        try:
            start_idx = 0
            if last_event_id and str(last_event_id).isdigit():
                start_idx = int(last_event_id)
            hist = list(self._history.get(job_id, []))
            for item in hist[start_idx:]:
                yield item
                if item["event"] in ("job.completed", "job.failed", "job.cancelled"):
                    return
            seen_ids = {item["id"] for item in hist[start_idx:]}
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=heartbeat_sec)
                except asyncio.TimeoutError:
                    yield {"comment": "heartbeat"}
                    continue
                if msg.get("id") in seen_ids:
                    continue
                seen_ids.add(msg.get("id"))
                yield msg
                if msg["event"] in ("job.completed", "job.failed", "job.cancelled"):
                    break
        finally:
            if job_id in self._queues and q in self._queues[job_id]:
                self._queues[job_id].remove(q)
                if not self._queues[job_id]:
                    del self._queues[job_id]

_broker = JobEventBroker()

def get_event_broker() -> JobEventBroker:
    return _broker
