import json
import uuid
from datetime import datetime, timezone

import aiosqlite

from src.config import get_settings
from src.db.connection import get_db
from src.external.llm import chat_completion, is_llm_available
from src.external.search import fetch_url, search_llm_builtin, search_web
from src.tasks import queue as tq


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _update_task_status(
    db: aiosqlite.Connection,
    task_id: str,
    status: str,
    progress: int,
    error: str | None = None,
    source: str | None = None,
) -> None:
    await db.execute(
        """
        UPDATE research_tasks
        SET status = ?, progress_percent = ?, error_message = ?, search_source_used = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, progress, error, source, _now(), task_id),
    )
    await db.commit()
    tq.publish_event(task_id, "status", {"status": status})
    tq.publish_event(task_id, "progress", {"percent": progress})


async def _load_task(db: aiosqlite.Connection, task_id: str) -> dict | None:
    async with db.execute(
        "SELECT id, topic, scope_description, status FROM research_tasks WHERE id = ?",
        (task_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "topic": row[1],
        "scope": row[2] or "",
        "status": row[3],
    }


async def _save_section(
    db: aiosqlite.Connection,
    task_id: str,
    section_type: str,
    title: str,
    content: str,
    order_index: int,
) -> None:
    await db.execute(
        """
        INSERT INTO research_sections (id, task_id, section_type, title, content, order_index, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (str(uuid.uuid4()), task_id, section_type, title, content, order_index, _now()),
    )
    await db.commit()


async def _save_citation(
    db: aiosqlite.Connection, task_id: str, source: dict
) -> None:
    await db.execute(
        """
        INSERT INTO research_citations (id, task_id, source_title, source_url, source_summary, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            task_id,
            source.get("title", ""),
            source.get("url", ""),
            source.get("summary", ""),
            _now(),
        ),
    )
    await db.commit()


async def run_research_task(task_id: str) -> None:
    db = await get_db()
    try:
        task = await _load_task(db, task_id)
        if not task:
            return

        # Avoid re-running completed/failed tasks
        if task["status"] not in ("queued", "pending_recheck"):
            return

        await db.execute(
            "UPDATE research_tasks SET status = ?, started_at = ? WHERE id = ?",
            ("running", _now(), task_id),
        )
        await db.commit()
        tq.publish_event(task_id, "status", {"status": "running"})

        settings = get_settings()
        privacy = settings.privacy_settings
        llm_cfg = settings.llm_config
        allow_search = privacy.allow_web_search

        topic = task["topic"]
        scope = task["scope"] or ""

        # Stage 1: outline + breadth check
        tq.publish_event(
            task_id, "progress", {"percent": 10, "stage": "正在分析调研主题..."}
        )
        outline_prompt = f"""你是一个领域调研助手。用户希望调研以下主题：
主题：{topic}
范围描述：{scope}

请判断该主题是否过于宽泛。如果是，请输出 JSON：{{"broad": true, "question": "细化问题", "options": ["选项A", "选项B", "选项C"]}}
如果不宽泛，请输出 JSON：{{"broad": false, "outline": [{{"type": "background", "title": "..."}}, ...]}}。
只输出 JSON，不要其他内容。"""

        try:
            outline_raw = await chat_completion(
                [{"role": "user", "content": outline_prompt}], stream=False
            )
        except Exception as e:
            outline_raw = ""

        outline_data = _safe_json_parse(outline_raw)
        if outline_data is None:
            outline_data = {"broad": False, "outline": _default_outline()}

        if outline_data.get("broad"):
            tq.ask_question(
                task_id,
                outline_data.get("question", "请选择一个细化方向"),
                outline_data.get("options", ["继续"]),
            )
            await _update_task_status(db, task_id, "awaiting_input", 20)
            answer = await tq.wait_for_response(task_id)
            scope += f"\n用户选择：{answer}"
            await _update_task_status(db, task_id, "running", 25)

        outline = outline_data.get("outline") or _default_outline()

        # Stage 2: search (FR-006a priority: LLM builtin -> Search API -> HTTP crawler/fallback)
        search_results: list[dict] = []
        search_source = None
        if allow_search:
            tq.publish_event(
                task_id,
                "chunk",
                {"summary": "正在检索网络信息，请稍候..."},
            )
            tq.publish_event(
                task_id, "progress", {"percent": 30, "stage": "正在检索网络信息..."}
            )

            # 1) LLM builtin search
            if llm_cfg.enable_search:
                try:
                    search_results = await search_llm_builtin(topic + " " + scope)
                    if search_results:
                        search_source = "llm_builtin"
                except Exception:
                    search_results = []

            # 2) Independent search API fallback
            if not search_results:
                try:
                    search_results = await search_web(topic + " " + scope)
                    if search_results and any(r.get("url") for r in search_results):
                        search_source = "search_api"
                except Exception:
                    search_results = []

            if search_results:
                # Fetch top 3 URLs for deeper content
                fetched_texts = []
                for r in search_results[:3]:
                    text, _ = await fetch_url(r.get("url", ""))
                    if text:
                        fetched_texts.append(text[:2000])
                search_context = "\n\n".join(fetched_texts)
                for r in search_results:
                    await _save_citation(db, task_id, r)
            else:
                search_context = "无可用搜索结果。"
        else:
            search_context = "用户未启用网络搜索，仅使用模型内部知识。"

        if search_source is None:
            search_source = "local_llm"

        await db.execute(
            "UPDATE research_tasks SET search_source_used = ? WHERE id = ?",
            (search_source, task_id),
        )
        await db.commit()

        # Stage 3: write sections
        total_sections = len(outline)
        for idx, sec in enumerate(outline):
            progress = 40 + int((idx / total_sections) * 40)
            stype = sec.get("type", "summary")
            title = sec.get("title", "未命名章节")
            tq.publish_event(
                task_id, "progress", {"percent": progress, "stage": f"正在撰写：{title}..."}
            )
            section_prompt = f"""请根据以下检索到的信息，撰写调研报告的"{title}"部分。
主题：{topic}
范围：{scope}

检索信息摘要：
{search_context}

要求：结构清晰、内容充实、限 300 字以内。只输出正文，不要标题。"""
            try:
                section_content = await chat_completion(
                    [{"role": "user", "content": section_prompt}], stream=False
                )
            except Exception:
                section_content = f"由于外部服务不可用，'{title}'部分未能完整生成。"
            await _save_section(db, task_id, stype, title, section_content, idx)
            tq.publish_event(
                task_id, "chunk", {"summary": f"已完成 {title} 的撰写"}
            )

        # Stage 4: finalize
        tq.publish_event(
            task_id, "progress", {"percent": 90, "stage": "正在汇总报告..."}
        )
        await _update_task_status(db, task_id, "completed", 100, source=search_source)
        await db.execute(
            "UPDATE research_tasks SET completed_at = ? WHERE id = ?",
            (_now(), task_id),
        )
        await db.commit()

        # Send report summary via SSE
        async with db.execute(
            "SELECT section_type, title FROM research_sections WHERE task_id = ? ORDER BY order_index",
            (task_id,),
        ) as cursor:
            sections = [{"type": row[0], "title": row[1]} async for row in cursor]
        tq.publish_event(task_id, "report", {"sections": sections})

    except Exception as e:
        # If external services are unavailable, mark for recheck instead of permanent failure
        if not await is_llm_available():
            await _update_task_status(db, task_id, "pending_recheck", 0, error=str(e))
        else:
            await _update_task_status(db, task_id, "failed", 0, error=str(e))
    finally:
        await db.close()


def _safe_json_parse(text: str) -> dict | None:
    try:
        # strip markdown code fences if any
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.split("```json", 1)[-1].split("```", 1)[0].strip()
        elif raw.startswith("`"):
            raw = raw.strip("`")
        return json.loads(raw)
    except Exception:
        return None


def _default_outline() -> list[dict]:
    return [
        {"type": "background", "title": "背景概述"},
        {"type": "key_points", "title": "关键观点"},
        {"type": "trends", "title": "趋势分析"},
        {"type": "conclusion", "title": "结论"},
    ]


async def save_report_to_knowledge(task_id: str) -> str | None:
    """Convert a completed research report into a KnowledgeItem."""
    from src.knowledge import service as kn_service

    db = await get_db()
    try:
        async with db.execute(
            "SELECT topic, status FROM research_tasks WHERE id = ?", (task_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        topic, status = row[0], row[1]
        if status != "completed":
            return None

        async with db.execute(
            "SELECT title, content FROM research_sections WHERE task_id = ? ORDER BY order_index",
            (task_id,),
        ) as cursor:
            sections = await cursor.fetchall()

        lines = [f"# 调研报告：{topic}\n"]
        for title, content in sections:
            lines.append(f"## {title}\n{content}\n")
        full_text = "\n".join(lines)

        item_id = await kn_service.create_knowledge_text(
            db,
            kn_service.KnowledgeCreate(
                title=f"调研报告：{topic}",
                content=full_text,
                source_type="research_report",
                tags=["调研报告"],
            ),
        )
        await db.execute(
            "UPDATE research_tasks SET saved_item_id = ? WHERE id = ?",
            (item_id, task_id),
        )
        await db.commit()
        return item_id
    finally:
        await db.close()
