import asyncio
from typing import Callable, TypeVar

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    timeout: float | None = None,
) -> T:
    """Execute an async function with exponential backoff retry.

    Delays: 1s, 2s, 4s, ... capped at max_delay.
    """
    import asyncio

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if timeout is not None:
                return await asyncio.wait_for(func(), timeout=timeout)
            return await func()
        except Exception as exc:
            last_exception = exc
            if attempt >= max_retries:
                break
            delay = min(base_delay * (2 ** attempt), max_delay)
            await asyncio.sleep(delay)

    raise last_exception
