# Documentation Gap & Clarity Checklist: AI 知识管理助手

**Purpose**: 聚焦需求文档中缺失的定义、边界模糊项与可度量性不足的问题，从 `consistency.md` 拆分以便分阶段补齐
**Created**: 2026-04-05
**Feature**: [../spec.md](../spec.md)

**Note**: 本清单记录非阻塞但应在实现前或实现过程中澄清的文档缺口。

---

## Data Model & Architecture Gaps

- [x] CHK001 - 调研任务队列与并发控制所需的实体或配置字段（如队列深度、并发上限）是否在 `data-model.md` 中有明确定义，以支撑 `spec.md §FR-023` 的队列需求？ [Gap, CHK001] → **已解决**：`data-model.md §2.15` 在 `storage_settings` 中增加 `research_concurrency_limit`（默认 2）。
- [x] CHK002 - `SystemConfig` 中是否包含用于限制调研任务并发数的外部 API 调用配额字段，以兑现 `spec.md §FR-023` 的"以配额为并发上限"要求？ [Gap, CHK002] → **已解决**：改为由 `research_concurrency_limit` 直接控制并发上限，`spec.md` 与 `system-api.md` 已同步。
- [x] CHK003 - 当 Embedding 模型配置发生变更后，已有 `KnowledgeVersion` 的向量重新计算触发条件与执行策略是否在需求中被覆盖？ [Gap, CHK019] → **已解决**：MVP 阶段不自动全量重算，提供"重建索引"手动入口或惰性重算，`spec.md FR-011` 与 `## Clarifications` 已明确。
- [x] CHK004 - `version_retention_policy` 的合法取值范围（数量/时间/磁盘阈值）及其生效后的清理行为是否在 `spec.md §FR-016` 或 `data-model.md §2.15` 中被精确枚举？ [Clarity, CHK010] → **已解决**：`spec.md FR-016` 明确 `{type,value}` 结构及清理行为；`data-model.md §2.15` 已同步注释。

## API & Behavior Clarity

- [x] CHK005 - RAG 混合检索（向量 + FTS5）的合并排序策略是否在所有引用文档中给出可执行的分数融合规则，而不仅是"加权排序"的定性描述？ [Clarity, CHK004] → **已解决**：`spec.md FR-003` 已明确 `hybrid_score = 0.6 * vec_norm + 0.4 * fts_norm`。
- [x] CHK006 - `UserProfile` 更新的具体触发条件："每 5 轮对话"的计数方式与"新领域"判定标准是否在 `spec.md §FR-005` 或 `data-model.md §2.11` 中被量化到可直接实现的程度？ [Clarity, CHK007] → **已解决**：`spec.md ## Clarifications` 已明确"新领域"判定为领域标签不在用户历史集合中。
- [x] CHK007 - "端到端查询响应 ≤2 秒"在 `spec.md §SC-005` 中的测量边界是否明确：是否包含 LLM 首 token 时间？流式场景下从请求到首字节是否计入该 2 秒？ [Clarity, CHK008] → **已解决**：`spec.md SC-005` 已明确测量边界为 TTFB，不包含 LLM 逐字生成耗时。
- [x] CHK008 - 知识库导出范围中的"相关元数据"是否在 `spec.md §FR-010`、`system-api.md §6` 中被精确枚举（是否包含 Conversation、ResearchTask、SystemConfig、UserProfile）？ [Clarity, CHK005, CHK009] → **已解决**：`spec.md ## Clarifications` 已明确导出范围，不包含 Conversation、Message、ResearchTask 和运行日志。
- [x] CHK009 - 导出 ZIP 包本身是否需要加密、导出密码与当前系统密码的关联规则是否在 `spec.md §FR-010` 或 `system-api.md §6` 中被定义？ [Gap, CHK023] → **已解决**：`spec.md FR-010` 已明确导出 ZIP 使用当前系统密码 AES-256-GCM 加密，旧密码不兼容。
- [x] CHK010 - 用户修改密码后，历史备份 ZIP 的解密策略（新旧密码兼容性）是否在 `spec.md §FR-017` 或 `system-api.md §6/7` 中被定义？ [Gap, CHK020] → **已解决**：`spec.md FR-010` 已明确旧备份需使用导出时的密码解密，不维护跨密码版本兼容性。

## Edge Cases & Coverage

- [x] CHK011 - 软删除知识条目的附件下载接口行为（是否仍然可用、是否继续占用归档压缩配额）是否在 `spec.md §FR-021` 或 `knowledge-api.md §9` 中被覆盖？ [Gap, CHK021] → **已解决**：`spec.md Edge Cases` 已明确软删除后附件仍可下载且正常计入归档配额。
- [x] CHK012 - 当 `ResearchTask.search_source_used` 为 null（任务尚未开始或失败）时，界面向用户展示当前搜索源类型的替代规范或缺省文案是否被定义？ [Gap, CHK022] → **已解决**：`spec.md Edge Cases` 及 `research-api.md` 已明确缺省展示为"搜索源：未确定"/"搜索源：未开始"。
- [x] CHK013 - 导入 ZIP 时 `metadata.json` 版本不兼容或顶层结构校验失败的整体回滚策略（而非单文件跳过）是否在 `spec.md §FR-011` 或 `system-api.md §7` 中被定义？ [Edge Case, CHK027] → **已解决**：`spec.md FR-011` 与 `system-api.md §7` 已明确顶层校验失败则整体中止导入。
- [x] CHK014 - 附件文件提取失败后的"明确提示"要求在 API 响应格式或前端行为中是否有具体的规范定义（超出仅返回 `extraction_status: failed`）？ [Edge Case, CHK025] → **已解决**：`spec.md Edge Cases` 已明确 API 返回 `extraction_error`，前端直接展示错误文本。
- [x] CHK015 - 本地 LLM 模式下调研任务的超时和重试策略（是否仍沿用外部 API 的 3 次指数退避）是否在 `spec.md §FR-013` 中被独立定义？ [Edge Case, CHK026] → **已解决**：`spec.md Edge Cases` 已明确重试策略一致，超时默认 60 秒。

## Non-Functional & Compliance

- [x] CHK016 - HTTP 爬虫在抓取外部网页时遵守 `robots.txt`、请求频率限制、User-Agent 声明的伦理与法律边界是否在 `spec.md §FR-006a` 或相关需求中被明确约束？ [Non-Functional, CHK028] → **已解决**：`spec.md Edge Cases` 已明确频率 ≤1 次/秒、User-Agent 及仅抓取用户提交 URL。
- [x] CHK017 - 主密钥在内存中的缓存周期、Session 失效条件、以及服务重启后必须重新鉴权的要求是否在 `spec.md §FR-017` 或安全相关设计中被量化？ [Non-Functional, CHK029] → **已解决**：`spec.md FR-017` 已明确主密钥缓存于服务端内存，服务重启后自动失效。
- [x] CHK018 - 调研任务降级至本地模型所需的模型能力基线（如最小上下文长度、是否必须具备搜索工具支持）是否作为需求假设或约束被文档化？ [Assumption, CHK031] → **已解决**：`spec.md Assumptions` 已明确本地模型最低支持 4096 tokens，不要求搜索工具。

## Notes

-  clearance 顺序建议：先完成 `consistency-blocking.md` 中的冲突决议，再逐步补充本清单中的文档缺口。
- 部分 "Gap" 项若在设计时已达成口头共识，建议直接写入 `spec.md` 或 `data-model.md` 的 Clarifications 章节，再勾选本清单。
