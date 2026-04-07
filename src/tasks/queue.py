import asyncio
import json
from typing import Dict, List

from src.config import get_settings

_research_queue: asyncio.Queue[str] = asyncio.Queue()
_concurrency_sem: asyncio.Semaphore = asyncio.Semaphore(2)
_task_subscribers: Dict[str, List[asyncio.Queue[str]]] = {}
_pending_events: Dict[str, asyncio.Event] = {}
_pending_answers: Dict[str, str] = {}


def init_concurrency() -> None:
    settings = get_settings()
    limit = max(1, settings.storage_settings.research_concurrency_limit)
    global _concurrency_sem
    _concurrency_sem = asyncio.Semaphore(limit)


async def submit_task(task_id: str) -> None:
    await _research_queue.put(task_id)


async def start_workers(run_fn, worker_count: int = 1):
    tasks = [asyncio.create_task(_worker(run_fn)) for _ in range(worker_count)]
    await asyncio.gather(*tasks)


def spawn_worker(run_fn) -> asyncio.Task:
    return asyncio.create_task(_worker(run_fn))


async def _worker(run_fn):
    while True:
        task_id = await _research_queue.get()
        async with _concurrency_sem:
            try:
                await run_fn(task_id)
            except Exception:
                # Worker exceptions are logged in run_fn or here if needed
                pass


def subscribe(task_id: str) -> asyncio.Queue[str]:
    q: asyncio.Queue[str] = asyncio.Queue()
    _task_subscribers.setdefault(task_id, []).append(q)
    return q


def unsubscribe(task_id: str, q: asyncio.Queue[str]) -> None:
    subs = _task_subscribers.get(task_id, [])
    if q in subs:
        subs.remove(q)


def publish_event(task_id: str, event: str, data: dict) -> None:
    payload = json.dumps({"event": event, "data": data}, ensure_ascii=False)
    for q in _task_subscribers.get(task_id, []):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


def ask_question(task_id: str, question: str, options: List[str]) -> None:
    _pending_events[task_id] = asyncio.Event()
    _pending_answers[task_id] = ""
    publish_event(task_id, "question", {"question": question, "options": options})


async def wait_for_response(task_id: str) -> str:
    event = _pending_events.get(task_id)
    if event is None:
        return ""
    await event.wait()
    return _pending_answers.pop(task_id, "")


def provide_response(task_id: str, answer: str) -> bool:
    if task_id not in _pending_events:
        return False
    _pending_answers[task_id] = answer
    _pending_events[task_id].set()
    return True
