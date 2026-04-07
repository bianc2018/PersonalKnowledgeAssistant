import uuid
from datetime import datetime, timezone
from typing import List, Optional

import aiosqlite

from src.db.connection import get_db
from src.research.models import (
    ResearchCreate,
    ResearchTaskDetail,
    ResearchTaskOut,
)
from src.tasks import queue as tq


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_task(db: aiosqlite.Connection, data: ResearchCreate) -> str:
    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO research_tasks (id, topic, scope_description, status, progress_percent, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (task_id, data.topic, data.scope_description, "queued", 0, _now()),
    )
    await db.commit()
    await tq.submit_task(task_id)
    return task_id


async def list_tasks(
    db: aiosqlite.Connection, offset: int = 0, limit: int = 20
) -> tuple[List[ResearchTaskOut], int]:
    async with db.execute("SELECT COUNT(*) FROM research_tasks") as cursor:
        row = await cursor.fetchone()
        total = row[0] if row else 0

    items: List[ResearchTaskOut] = []
    async with db.execute(
        """
        SELECT
            id, topic, status, progress_percent, search_source_used,
            created_at, started_at, completed_at
        FROM research_tasks
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ) as cursor:
        async for row in cursor:
            items.append(
                ResearchTaskOut(
                    id=row[0],
                    topic=row[1],
                    status=row[2],
                    progress_percent=row[3],
                    search_source_used=row[4],
                    created_at=datetime.fromisoformat(row[5]),
                    started_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                )
            )
    return items, total


async def get_task_detail(db: aiosqlite.Connection, task_id: str) -> Optional[ResearchTaskDetail]:
    async with db.execute(
        """
        SELECT
            id, topic, scope_description, status, progress_percent, search_source_used,
            created_at, started_at, completed_at, error_message, saved_item_id
        FROM research_tasks
        WHERE id = ?
        """,
        (task_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None

    sections: List[dict] = []
    async with db.execute(
        """
        SELECT section_type, title, content, order_index
        FROM research_sections
        WHERE task_id = ?
        ORDER BY order_index
        """,
        (task_id,),
    ) as cursor:
        async for sec in cursor:
            sections.append(
                {"section_type": sec[0], "title": sec[1], "content": sec[2], "order_index": sec[3]}
            )

    citations: List[dict] = []
    async with db.execute(
        """
        SELECT source_title, source_url, source_summary
        FROM research_citations
        WHERE task_id = ?
        """,
        (task_id,),
    ) as cursor:
        async for cit in cursor:
            citations.append(
                {"source_title": cit[0], "source_url": cit[1], "source_summary": cit[2]}
            )

    return ResearchTaskDetail(
        id=row[0],
        topic=row[1],
        status=row[3],
        progress_percent=row[4],
        search_source_used=row[5],
        created_at=datetime.fromisoformat(row[6]),
        started_at=datetime.fromisoformat(row[7]) if row[7] else None,
        completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
        scope_description=row[2],
        sections=sections,
        citations=citations,
        saved_item_id=row[10],
        error_message=row[9],
    )


async def respond_to_task(task_id: str, answer: str) -> bool:
    from src.research.worker import run_research_task

    ok = tq.provide_response(task_id, answer)
    if not ok:
        return False
    # Resume task by re-queueing it. Worker will pick it up as long as status
    # transitions back to running in the worker loop.
    await tq.submit_task(task_id)
    return True


async def save_report(task_id: str) -> Optional[str]:
    from src.research.worker import save_report_to_knowledge

    return await save_report_to_knowledge(task_id)
