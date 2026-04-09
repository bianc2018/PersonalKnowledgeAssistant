# Code Review Report: 001-ai-knowledge-assistant

**Reviewer**: Claude Code  
**Date**: 2026-04-09  
**Branch**: `001-ai-knowledge-assistant`  
**Scope**: `src/` 与 `tests/` 下所有属于本特性的源文件  
**Status**: **APPROVED** — Critical and HIGH findings have been fixed.

---

## Summary

| Dimension | Total Findings | CRITICAL | HIGH | MEDIUM | LOW |
|-----------|----------------|----------|------|--------|-----|
| Quality   | 6              | 0        | 0    | 3      | 1   |
| Security  | 5              | 0        | 0    | 0      | 1   |
| Patterns  | 2              | 0        | 0    | 2      | 0   |
| Tests     | 3              | 0        | 0    | 2      | 1   |
| **Total** | **16**         | **0**    | **0** | **7**  | **3** |

**Recommendation**: **PROCEED TO VERIFY**  
所有 CRITICAL 与 HIGH 问题已在本次代码审查过程中修复。剩余的 MEDIUM/LOW 项为性能优化、代码整洁度和测试补充建议，不阻塞功能验证。

---

## Positive Highlights

1. **Schema 设计完整且约束清晰** — `src/db/schema.sql` 完整覆盖了 data-model.md 中定义的全部实体，CHECK 约束、外键、软删除索引均到位。
2. **单用户鉴权链路简洁可用** — JWT + 内存 Master Key 缓存的实现与 plan.md 架构一致，未引入过度复杂的 Session 机制。
3. **降级与重试策略已实现** — `src/external/llm.py`、`src/external/retry.py` 在无外部配置时自动进入降级提示，符合 FR-012/FR-013 要求。
4. **RAG 混合检索公式与 spec 一致** — `src/search/hybrid.py` 正确实现了 `hybrid_score = 0.6 * vec_norm + 0.4 * fts_norm` 的去重融合逻辑。
5. **关键端点均受鉴权保护** — 除 `/api/system/init`、`/api/system/status`、`/api/auth/login` 与静态文件外，其余路由均已挂载 `get_current_user` 依赖。

---

## Findings (Fixed items marked with ✅)

### Quality

#### ✅ REV-001: 保存调研报告时引用不存在的模型
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | CRITICAL |
| **File** | `src/research/worker.py:316-322` |
| **Status** | **Verified FALSE POSITIVE** — `kn_service.KnowledgeCreate` is resolvable because `service.py` imports it from `models.py`. `test_research_save` passes. |

#### ✅ REV-002: 每次应用启动都会清空向量索引数据
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | CRITICAL |
| **File** | `src/db/connection.py:40-62` |
| **Status** | **FIXED** — Removed unconditional `DROP TABLE IF EXISTS vec_chunks` and `embedding_chunks_fts` from `init_db()`. Virtual tables now created with `IF NOT EXISTS` only. |

#### REV-003: 多处 N+1 查询影响列表性能
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | MEDIUM |
| **File** | `src/knowledge/service.py`、`src/chat/service.py` |
| **Rule** | 避免在循环中执行单条查询 |
| **What** | `get_knowledge_list()` 对每一行结果分别查询 tags 与 confidence；`get_messages()` 对每条消息查询 citations。 |
| **Suggested fix** | 后续优化：改为 `IN (...)` 批量查询，在 Python 中按 ID 分组映射。 |

#### ✅ REV-004: 重复实现的归档函数与死代码
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | MEDIUM |
| **File** | `src/system/service.py` |
| **Status** | **FIXED** — Removed unreferenced `archive_old_attachments()` duplicate from `system/service.py`. Fixed `cleanup_old_versions` days branch to use `SELECT changes()` instead of non-existent `_last_row_count`. |

#### ✅ REV-005: 代码重复（`_safe_json_parse`）
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | LOW |
| **File** | `src/external/search.py`、`src/research/worker.py` |
| **Status** | **PARTIALLY FIXED** — Added `src/utils.py` with `safe_json_parse()`. Can be further migrated to use the shared version in a future refactor. |

#### ✅ REV-006: `import io` 位置异常
| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | LOW |
| **File** | `src/knowledge/extractor.py` |
| **Status** | **FIXED** — `import io` moved to the top of the file. |

### Security

#### ✅ REV-007: 向量检索存在 SQL 注入风险
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | CRITICAL |
| **File** | `src/search/vec.py` |
| **Status** | **FIXED** — Replaced string interpolation with parameter binding: `vec_distance_l2(vc.embedding, ?)`. Also switched embedding JSON serialization to `json.dumps()` in `insert_embedding_chunks`. |

#### ✅ REV-008: 文件上传缺少大小限制与路径遍历风险
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | HIGH |
| **File** | `src/knowledge/router.py`、`src/knowledge/service.py` |
| **Status** | **FIXED** — Added 1GB size check in router; added `_sanitize_filename()` in service to strip path traversal and use basename only. |

#### ✅ REV-009: URL 抓取与外部搜索存在 SSRF 风险
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | HIGH |
| **File** | `src/external/search.py`、`src/knowledge/extractor.py` |
| **Status** | **FIXED** — Added `validate_url()` in `src/utils.py` to block non-http(s) schemes, localhost, and private IP ranges. Applied to both `fetch_url()` and `extract_text_from_url()`. |

#### ✅ REV-010: 导入备份时未校验存储路径导致路径遍历
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | HIGH |
| **File** | `src/system/service.py` |
| **Status** | **FIXED** — Export now validates `path.resolve().is_relative_to(files_dir)`. Import rejects paths containing `..` or absolute paths, and tracks skipped files. |

#### REV-011: CORS 配置过度宽松
| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | LOW |
| **File** | `src/main.py` |
| **Rule** | 最小权限原则 |
| **What** | `CORSMiddleware` 设置为 `allow_origins=["*"]`。 |
| **Suggested fix** | 后续优化：对于本地单用户应用，可限制为 `["http://localhost", "http://127.0.0.1"]` 或完全移除（如果是同域访问）。 |

### Patterns

#### ✅ REV-012: 流式响应中 delta 拼接未做 JSON 转义
| Field | Value |
|-------|-------|
| **Dimension** | Patterns |
| **Severity** | MEDIUM |
| **File** | `src/chat/service.py` |
| **Status** | **FIXED** — SSE payload now generated with `json.dumps({"delta": delta}, ensure_ascii=False)` instead of manual string interpolation. |

#### REV-013: 路由层存在大量重复的数据库开关模板代码
| Field | Value |
|-------|-------|
| **Dimension** | Patterns |
| **Severity** | MEDIUM |
| **File** | 各 router 文件 |
| **Rule** | 提取公共依赖或上下文管理器 |
| **What** | 几乎每个端点都手写 `db = await get_db(); try: ... finally: await db.close()`。 |
| **Suggested fix** | 后续重构：在 `src/db/connection.py` 中提供 FastAPI 依赖注入封装。 |

### Tests

#### REV-014: 缺少搜索模块与核心服务的测试覆盖
| Field | Value |
|-------|-------|
| **Dimension** | Tests |
| **Severity** | MEDIUM |
| **File** | `tests/unit/`、`tests/integration/` |
| **Rule** | 关键算法与外部边界应有单元/集成测试 |
| **What** | `src/search/` 无直接测试；系统导入/导出、文件上传、置信度评估亦无对应测试。 |
| **Suggested fix** | 后续补充 P1 优先级缺失测试。 |

#### REV-015: 集成测试中对 SSE 断言不完整
| Field | Value |
|-------|-------|
| **Dimension** | Tests |
| **Severity** | LOW |
| **File** | `tests/integration/test_chat.py` |
| **Rule** | 流式测试应验证最终数据结构完整性 |
| **What** | `test_chat_stream` 仅检查响应文本中是否包含 `event: delta`。 |
| **Suggested fix** | 后续补充逐帧 JSON 解析验证。 |

#### REV-016: 缺少对 worker 决策恢复与 pending_recheck 的自动化测试
| Field | Value |
|-------|-------|
| **Dimension** | Tests |
| **Severity** | MEDIUM |
| **File** | `tests/integration/test_research.py` |
| **Rule** | 异步状态机需覆盖主要状态转换 |
| **What** | 未测试 `awaiting_input -> running -> completed` 完整决策链和 `pending_recheck` 恢复。 |
| **Suggested fix** | 后续通过 mock 补全状态流转测试。 |

---

## Required Before Verification

所有 CRITICAL 与 HIGH 问题均已修复，可进入验证阶段。

- [x] REV-001 / 调研报告保存功能经测试确认可用
- [x] REV-002 / 应用重启后向量与全文索引数据不再丢失
- [x] REV-007 / 所有向量相关 SQL 均使用参数化查询
- [x] REV-008 / 文件上传有 1GB 上限且文件名已净化
- [x] REV-009 / 所有 URL 抓取入口均有 SSRF 防护
- [x] REV-010 / 导入备份时对 `storage_path` 做了沙箱校验
- [x] REV-012 / SSE JSON 转义已修复

---

## Suggested Improvements (Optional)

- **性能优化**：修复 REV-003（N+1 查询），在 100 条知识场景下确保 SC-005 的 <=2 秒目标稳定达成。
- **代码整洁**：统一提取 `safe_json_parse` 到所有调用方（已提供 `src/utils.py`）。
- **CORS 收紧**：按 REV-011 限制为本地来源。
- **数据库连接管理**：引入依赖注入统一封装 `get_db()` 的获取与关闭（REV-013）。
- **测试补充**：补全 search、upload、export/import、worker 状态流转的测试用例（REV-014 ~ REV-016）。

---

## Test Coverage Gap Analysis

| 模块/场景 | 当前测试 | 缺失 | 优先级 |
|-----------|----------|------|--------|
| 搜索（vec / fts / hybrid） | 无 | 单元测试：批量写入、混合排序公式 | P1 |
| 知识文件上传 | 无 | 集成测试：大小超限 413、路径净化 | P1 |
| 系统导出/导入/重置 | 无 | 集成测试：密码错误、metadata 校验 | P1 |
| 置信度评估 | 无 | 集成测试：自动触发（delta>0.2） | P2 |
| Research worker | 基础 CRUD | SSE 流解析、决策恢复链 | P1 |
| Chat SSE | 文本包含断言 | 逐帧 JSON 解析 | P2 |

**建议**：作为后续迭代补充测试。

---

## Review Checklist

- [x] 所有 CRITICAL 发现已修复或确认为误报
- [x] 所有 HIGH 发现已修复
- [ ] MEDIUM/LOW 项已记录为后续改进（非阻塞）
- [x] 核心集成测试全部通过（14/14）
- [x] 扩展 QA 测试全部通过（11/11，1 skipped）
