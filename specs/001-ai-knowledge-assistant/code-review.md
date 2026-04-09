# Code Review Report: 001-ai-knowledge-assistant

**Reviewer**: Claude Code  
**Date**: 2026-04-09  
**Branch**: `001-ai-knowledge-assistant`  
**Scope**: `src/` 与 `tests/` 下所有属于本特性的源文件  

---

## Summary

| Dimension | Total Findings | CRITICAL | HIGH | MEDIUM | LOW |
|-----------|----------------|----------|------|--------|-----|
| Quality   | 6              | 2        | 0    | 3      | 1   |
| Security  | 5              | 1        | 3    | 0      | 1   |
| Patterns  | 2              | 0        | 0    | 2      | 0   |
| Tests     | 3              | 0        | 0    | 2      | 1   |
| **Total** | **16**         | **3**    | **3** | **7**  | **3** |

**Recommendation**: **FIX CRITICAL+HIGH FIRST**  
存在 3 项 CRITICAL 与 3 项 HIGH 发现，均涉及功能崩溃、数据丢失或安全边界突破，必须在进入验证阶段前修复。

---

## Positive Highlights

1. **Schema 设计完整且约束清晰** — `src/db/schema.sql` 完整覆盖了 data-model.md 中定义的全部实体，CHECK 约束、外键、软删除索引均到位。
2. **单用户鉴权链路简洁可用** — JWT + 内存 Master Key 缓存的实现与 plan.md 架构一致，未引入过度复杂的 Session 机制。
3. **降级与重试策略已实现** — `src/external/llm.py`、`src/external/retry.py` 在无外部配置时自动进入降级提示，符合 FR-012/FR-013 要求。
4. **RAG 混合检索公式与 spec 一致** — `src/search/hybrid.py` 正确实现了 `hybrid_score = 0.6 * vec_norm + 0.4 * fts_norm` 的去重融合逻辑。
5. **关键端点均受鉴权保护** — 除 `/api/system/init`、`/api/system/status`、`/api/auth/login` 与静态文件外，其余路由均已挂载 `get_current_user` 依赖。

---

## Findings

### Quality

#### REV-001: 保存调研报告时引用不存在的模型
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | CRITICAL |
| **File** | `src/research/worker.py:316-322` |
| **Rule** | 引用已存在的类型/符号 |
| **What** | `kn_service.KnowledgeCreate(...)` 中的 `KnowledgeCreate` 定义在 `src.knowledge.models`，但 `src.knowledge.service` 并未将其导出到模块命名空间。 |
| **Why it matters** | 用户点击“保存到知识库”时将抛出 `AttributeError`，导致 FR-006a “调研报告保存到知识库”完全不可用。 |
| **Suggested fix** | 在 worker 顶部显式导入模型类：`from src.knowledge.models import KnowledgeCreate`，并将调用改为 `KnowledgeCreate(...)`。 |

#### REV-002: 每次应用启动都会清空向量索引数据
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | CRITICAL |
| **File** | `src/db/connection.py:40-62` |
| **Rule** | 生命周期钩子不得破坏持久化数据 |
| **What** | `init_db()` 被 `lifespan()` 在每次启动时调用，内部无条件 `DROP TABLE IF EXISTS vec_chunks` 与 `embedding_chunks_fts`，随后重新创建空虚拟表。 |
| **Why it matters** | sqlite-vec 与 FTS5 的虚拟表 `DROP` 会同步删除其索引数据。服务重启后所有 Embedding 向量与全文索引全部丢失，RAG 检索将永久失效（除非重新生成）。 |
| **Suggested fix** | 删除 `DROP TABLE` 逻辑。改为先查询 `sqlite_master` 判断虚拟表是否已存在，仅在首次初始化时创建；`embedding_dim` 变化应通过显式迁移脚本处理，而非在启动时无条件销毁数据。 |

#### REV-003: 多处 N+1 查询影响列表性能
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | MEDIUM |
| **File** | `src/knowledge/service.py:268-287`、`src/chat/service.py:74-85` |
| **Rule** | 避免在循环中执行单条查询 |
| **What** | `get_knowledge_list()` 对每一行结果分别调用 `_get_item_tags()` 与 `_get_current_confidence()`；`get_messages()` 对每条消息调用 `_get_message_citations()`。 |
| **Why it matters** | 以默认分页 20 条为例，知识列表会产生 40 次额外查询，显著增加 SC-005 中“100 条知识 <=2 秒”的达成风险。 |
| **Suggested fix** | 将 tags、confidence、citations 改为 `IN (...)` 批量查询，在 Python 中按 ID 分组映射到列表项。 |

#### REV-004: 重复实现的归档函数与死代码
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | MEDIUM |
| **File** | `src/knowledge/archive.py`、`src/system/service.py:419-446` |
| **Rule** | DRY / 清理未使用代码 |
| **What** | `archive_old_attachments` 在两个模块中分别实现，且 `src/system/service.py` 中的版本未被任何调用方引用。此外 `cleanup_old_versions` 中 `ptype == "days"` 分支使用 `getattr(db, "_last_row_count", 0)` 进行计数，但 `aiosqlite.Connection` 无此属性，导致计数始终为 0。 |
| **Why it matters** | 造成维护困惑，且 days 策略的清理反馈信息不准确。 |
| **Suggested fix** | 删除 `src/system/service.py` 中的 `archive_old_attachments`；在 `cleanup_old_versions` 的 days 分支中，先执行 `SELECT changes()` 或在 `DELETE` 前后计数获取实际删除数量。 |

#### REV-005: 代码重复（`_safe_json_parse`、`_fallback_embedding`）
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | LOW |
| **File** | `src/external/search.py:127-136`、`src/knowledge/confidence.py:80-91`、`src/research/worker.py:267-277`、`src/external/llm.py:79-82`、`src/knowledge/service.py:538-542` |
| **Rule** | 提取公共辅助函数 |
| **What** | `_safe_json_parse` 在 3 个文件中各自实现；`_fallback_embedding` 在 `llm.py` 与 `service.py` 中各有一份。 |
| **Why it matters** | 一处的修复（如支持更多 markdown fence 格式）无法同步到所有副本。 |
| **Suggested fix** | 在 `src/utils/` 或 `src/common.py` 中统一提供 `safe_json_parse()` 与 `fallback_embedding()`。 |

#### REV-006: `import io` 位置异常
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | LOW |
| **File** | `src/knowledge/extractor.py:123` |
| **Rule** | 模块级导入应位于文件顶部 |
| **What** | `import io` 被放置在文件末尾，虽然 Python 支持，但破坏可读性且易遗漏。 |
| **Why it matters** | 维护者可能误以为缺少依赖导致运行时错误。 |
| **Suggested fix** | 将 `import io` 移至文件顶部。 |

### Security

#### REV-007: 向量检索存在 SQL 注入风险
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | CRITICAL |
| **File** | `src/search/vec.py:47-58` |
| **Rule** | 禁止将用户/外部数据直接拼接到 SQL 字符串 |
| **What** | `search_similar()` 中将 `emb_json` 通过字符串格式化拼接到 `vec_distance_l2(vc.embedding, '{emb_json}')`，仅做了简单的单引号替换。 |
| **Why it matters** | 若 embedding 来源被污染（如 fallback embedding、恶意 API 响应或本地文件导入），攻击者可注入任意 SQL。 |
| **Suggested fix** | 使用参数化查询：`vec_distance_l2(vc.embedding, ?)` 并将 `emb_json` 作为参数传入。若 sqlite-vec 版本不支持函数参数绑定，则应在 Python 层对向量做最小/最大值校验，并改用严格的白名单格式化（如 `json.dumps(list_of_floats)`）。 |

#### REV-008: 文件上传缺少大小限制与路径遍历风险
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | HIGH |
| **File** | `src/knowledge/router.py:60`、`src/knowledge/service.py:165-166` |
| **Rule** | 校验文件大小并净化文件名 |
| **What** | `upload_knowledge` 直接 `await file.read()` 读入内存，没有检查 `len(file_bytes) <= 1GB`；`_storage_path()` 将用户上传的 `filename` 直接拼接到存储路径中，未去除路径分隔符。 |
| **Why it matters** | 超大文件可导致 OOM；恶意文件名（如 `../../../passwd`）可能使加密文件写入预期目录之外（虽然目录前缀由服务端 UUID 控制，但相对路径仍可逃逸一到两层）。 |
| **Suggested fix** | 1) 读取文件前检查 `file.size` 或流式读取到临时文件并限制大小为 1GB；2) 使用 `Path(filename).name` 取纯文件名并过滤 `..` 与路径分隔符。 |

#### REV-009: URL 抓取与外部搜索存在 SSRF 风险
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | HIGH |
| **File** | `src/external/search.py:86-124`、`src/knowledge/extractor.py:100-120` |
| **Rule** | 对外部发起的 HTTP 请求进行 URL 白名单/黑名单校验 |
| **What** | `fetch_url()` 与 `extract_text_from_url()` 对用户传入的 URL 未做任何 SSRF 过滤（如禁止内网 IP、localhost、文件协议等）。 |
| **Why it matters** | 攻击者可通过提交 `http://169.254.169.254/latest/meta-data/` 或 `http://localhost:22/` 读取本地服务或云实例元数据。 |
| **Suggested fix** | 在发起请求前解析 URL，禁止 schema 非 `http/https`，并拒绝目标为私有 IP、localhost、回环地址的域名/IP。 |

#### REV-010: 导入备份时未校验存储路径导致路径遍历
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | HIGH |
| **File** | `src/system/service.py:324-349`、`src/system/service.py:185-188` |
| **Rule** | 不可信任数据中的路径必须经沙箱校验 |
| **What** | `import_backup()` 将 `metadata.json` 中的 `storage_path` 原样写入数据库；`export_backup()` 随后直接读取该路径打包到 ZIP。 |
| **Why it matters** | 恶意构造的备份文件可包含 `../../../etc/passwd` 等路径，导致导入/导出阶段读写系统任意文件。 |
| **Suggested fix** | 导入时校验 `storage_path` 必须在 `settings.files_dir` 之下，并拒绝包含 `..` 或绝对路径的条目；或导入附件时忽略原路径，按本地 `_storage_path()` 规则重新生成存储位置。 |

#### REV-011: CORS 配置过度宽松
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | LOW |
| **File** | `src/main.py:112-118` |
| **Rule** | 最小权限原则 |
| **What** | `CORSMiddleware` 设置为 `allow_origins=["*"]`。 |
| **Why it matters** | 本地单用户应用理论上只有我才能访问，开放任意来源增加了被本地其他网页通过 CSRF/XHR 调用的风险（虽然 JWT 保护降低了实际危害）。 |
| **Suggested fix** | 限制为 `["http://localhost", "http://127.0.0.1"]` 或根据实际前端地址动态配置。 |

### Patterns

#### REV-012: 流式响应中 delta 拼接未做 JSON 转义
| Field | Value |
|-------|-------|
| **Dimension** | Patterns |
| **Severity** | MEDIUM |
| **File** | `src/chat/service.py:313` |
| **Rule** | SSE payload 必须合法 JSON |
| **What** | `yield f'event: delta\ndata: {{"delta": "{delta}"}}\n\n'` 直接将 LLM 返回内容插入 JSON 字符串，未对引号、换行、反斜杠进行转义。 |
| **Why it matters** | 当流式内容包含 `"` 或 `\n` 时，客户端收到的 SSE 是一条非法 JSON，导致前端解析失败。 |
| **Suggested fix** | 使用 `json.dumps({"delta": delta})` 生成 payload，再拼接 SSE 前缀。 |

#### REV-013: 路由层存在大量重复的数据库开关模板代码
| Field | Value |
|-------|-------|
| **Dimension** | Patterns |
| **Severity** | MEDIUM |
| **File** | `src/knowledge/router.py`、`src/chat/router.py`、`src/research/router.py`、`src/system/router.py` 等 |
| **Rule** | 提取公共依赖或上下文管理器 |
| **What** | 几乎每个端点都手写 `db = await get_db(); try: ... finally: await db.close()`。 |
| **Why it matters** | 增加样板代码量，且一旦需要统一添加事务回滚或指标采集，修改成本高。 |
| **Suggested fix** | 在 `src/db/connection.py` 中提供一个 FastAPI 依赖（类似 `async with get_db_connection() as db`），让路由层通过 `Depends` 直接获取已打开的 connection。 |

### Tests

#### REV-014: 缺少搜索模块与核心服务的测试覆盖
| Field | Value |
|-------|-------|
| **Dimension** | Tests |
| **Severity** | MEDIUM |
| **File** | `tests/unit/`、`tests/integration/` |
| **Rule** | 关键算法与外部边界应有单元/集成测试 |
| **What** | `src/search/vec.py`、`src/search/fts.py`、`src/search/hybrid.py` 无任何测试；系统导入/导出、文件上传、置信度评估、用户画像更新亦无对应测试。 |
| **Why it matters** | 搜索是 RAG 核心链路，缺少测试意味着混合排序、向量写入、FTS 过滤的回归风险完全暴露。 |
| **Suggested fix** | 为 `hybrid_search`、`insert_embedding_chunks`、`insert_fts_chunks` 编写基于内存数据库的单元测试；为 `/api/knowledge/upload`、`/api/system/export`、`/api/system/import`、`/api/knowledge/{id}/evaluate-confidence` 补集成测试。 |

#### REV-015: 集成测试中对 SSE 断言不完整
| Field | Value |
|-------|-------|
| **Dimension** | Tests |
| **Severity** | LOW |
| **File** | `tests/integration/test_chat.py:54-55` |
| **Rule** | 流式测试应验证最终数据结构完整性 |
| **What** | `test_chat_stream` 仅检查响应文本中是否包含 `event: delta` 或 `event: done`，未解析事件行验证 JSON 有效性。 |
| **Why it matters** | 若 REV-012（delta 未转义）发生，当前测试无法拦截。 |
| **Suggested fix** | 按 `\n\n` 拆分 SSE 帧，使用 `json.loads()` 解析每帧 data 字段，验证存在 `event: delta` 帧及最后的 `event: done` 帧。 |

#### REV-016: 缺少对 worker 决策恢复与 pending_recheck 的自动化测试
| Field | Value |
|-------|-------|
| **Dimension** | Tests |
| **Severity** | MEDIUM |
| **File** | `tests/integration/test_research.py` |
| **Rule** | 异步状态机需覆盖主要状态转换 |
| **What** | `test_research_respond_not_awaiting` 仅覆盖了错误分支，没有测试 `awaiting_input -> running -> completed` 的完整决策链，也未测试 `pending_recheck` 恢复。 |
| **Why it matters** | worker 是 US3 的核心，状态转换 bug 会导致用户决策后任务卡住或重复执行。 |
| **Suggested fix** | 通过 mock `chat_completion` 与 `search_web`，构造一个必然进入 `awaiting_input` 的任务，验证 `respond` 后状态流转及最终 `completed`；再模拟 `is_llm_available() == False` 触发 `pending_recheck`，最后恢复并断言重新入队。 |

---

## Required Before Verification

以下问题必须在进入验证（Verify）阶段前修复：

1. **REV-002** — 删除 `init_db()` 中无条件 `DROP TABLE` 虚拟表的逻辑，防止每次重启丢失全部向量与全文索引。
2. **REV-007** — 消除 `src/search/vec.py` 中的 SQL 注入风险，将 embedding 数据通过参数绑定传入查询。
3. **REV-001** — 修复 `src/research/worker.py` 引用 `kn_service.KnowledgeCreate` 的 `AttributeError`，确保调研报告可正常保存到知识库。
4. **REV-008** — 为文件上传增加 `<= 1GB` 大小校验，并净化 `filename` 中的路径分隔符。
5. **REV-009** — 为所有的 URL 抓取入口增加 SSRF 校验（禁止非 http/https、私有 IP、localhost）。
6. **REV-010** — 导入备份时校验 `storage_path` 的合法性，拒绝路径遍历。

---

## Suggested Improvements

- **性能优化**：修复 REV-003（N+1 查询），在 100 条知识场景下确保 SC-005 的 <=2 秒目标稳定达成。
- **代码整洁**：统一提取 `safe_json_parse` 与 `fallback_embedding` 到公共模块（REV-005）；将 `import io` 移至文件顶部（REV-006）。
- **错误处理**：`src/main.py:121-127` 的全局异常处理器目前对所有异常返回 500，可考虑对 `HTTPException` 透传原状态码与详情，避免吞掉客户端错误信息。
- **CORS 收紧**：按 REV-011 限制为本地来源，降低本地横向调用风险。
- **数据库连接管理**：引入依赖注入统一封装 `get_db()` 的获取与关闭，减少所有 router 中的重复样板代码（REV-013）。

---

## Test Coverage Gap Analysis

| 模块/场景 | 当前测试 | 缺失 | 优先级 |
|-----------|----------|------|--------|
| 搜索（vec / fts / hybrid） | 无 | 单元测试：批量写入、混合排序公式、空查询容错 | P1 |
| 知识文件上传 | 无 | 集成测试：大小超限 422、路径净化、加密后文件存在 | P1 |
| 系统导出/导入/重置 | 无 | 集成测试：密码错误 400、metadata 校验、损坏文件跳过 | P1 |
| 置信度评估 | 无 | 集成测试：自动触发（delta>0.2）、手动触发 202 | P2 |
| 用户画像 | 无 | 单元测试：5 轮触发、JSON 解析容错 | P2 |
| Research worker | 基础 CRUD | SSE 流解析、决策恢复链、pending_recheck 恢复 | P1 |
| Chat SSE | 文本包含断言 | 逐帧 JSON 解析与 citation 事件结构校验 | P2 |

**建议**：在修复 CRITICAL/HIGH 问题的同时，至少补全 P1 级别缺失的测试，以保障回归安全。

---

## Review Checklist

- [ ] REV-001 已修复，调研报告保存到知识库功能可端到端跑通  
- [ ] REV-002 已修复，应用重启后向量与全文索引数据不丢失  
- [ ] REV-007 已修复，所有向量相关 SQL 均使用参数化查询  
- [ ] REV-008 已修复，文件上传有 1GB 上限且文件名已净化  
- [ ] REV-009 已修复，所有 URL 抓取入口均有 SSRF 防护  
- [ ] REV-010 已修复，导入备份时对 `storage_path` 做了沙箱校验  
- [ ] 新增 vec/fts/hybrid 单元测试并通过  
- [ ] 新增文件上传、系统导入导出集成测试并通过  
- [ ] 现有测试套件全部通过（`pytest tests/`）  
- [ ] 运行一次 `quickstart.md` 端到端流程，确认 US1~US3 主干可用  
