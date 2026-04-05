# Blocking Cross-Document Consistency Checklist: AI 知识管理助手

**Purpose**: 聚焦会直接导致实现冲突或接口不兼容的高优先级跨文档一致性问题，必须在编码前明确决议
**Created**: 2026-04-05
**Feature**: [../spec.md](../spec.md)

**Note**: 本清单从 `consistency.md` 中拆分出的阻塞级冲突项，优先解决。

---

## Critical Conflicts

- [x] CHK001 - 知识版本生成触发条件在 `spec.md §FR-008`、`data-model.md §2.2` 与 `knowledge-api.md §6` 三处是否已统一为单一规则？当前存在 ">20% 才触发" 与 "任何 content 变更均生成新版本" 的表述冲突。 [Consistency, Blocking, CHK011] → **已解决**：`spec.md` 已更新，任何 `content` 变更均生成新版本。
- [x] CHK002 - 置信度重新评估的触发阈值是否在全部文档中一致：即 "仅当 content_delta > 0.2 或被用户手动请求时触发"，并已消除 "任何变更均重新评估" 的歧义？ [Consistency, Blocking, CHK006] → **已解决**：`spec.md` 已更新。
- [x] CHK003 - `MessageCitation` 的字段命名在 `data-model.md §2.10`（`citation_index`）与 `chat-api.md §3`（`index`）之间是否已统一为单一命名？ [Consistency, Blocking, CHK013] → **已解决**：`chat-api.md` 已统一为 `citation_index`。
- [x] CHK004 - `ResearchTask` 的状态枚举是否在 `data-model.md §2.12`、`data-model.md §5.1` 状态机图、`research-api.md §4` SSE 事件说明中均完整包含 `pending_recheck`？ [Consistency, Blocking, CHK014] → **已解决**：`data-model.md §5.1` 与 `research-api.md §4` 均已补充。
- [x] CHK005 - `pending_recheck` 状态的外部服务恢复后流转规则（`pending_recheck → queued`）是否在 spec、data-model、research-api 中一致定义，无 "直接执行" 与 "重新排队" 的冲突？ [Consistency, Blocking, CHK014] → **已解决**：`spec.md FR-014` 与 `## Clarifications` 已明确。
- [x] CHK006 - 外部搜索源的控制层级是否在 `spec.md §FR-006a`、`system-api.md §4`、`research.md §4` 中无职责重叠：`privacy_settings.allow_web_search` 作为总开关，`llm_config.enable_search` 仅控制是否优先尝试 LLM 自带搜索，`search_config` 作为独立搜索 API 配置，三者的优先级与边界是否已澄清？ [Consistency, Blocking, CHK012] → **已解决**：`spec.md ## Clarifications` 已明确。
- [x] CHK007 - 系统重置后的初始化流程在 `system-api.md §8`、`spec.md §FR-025`、`quickstart.md §7.2` 中是否一致：重置后是否必须立即重新调用 `/api/system/init` 才能恢复可用状态？ [Consistency, Blocking, CHK015, CHK038] → **已解决**：`spec.md` 与 `system-api.md` 已明确重置后需重新调用 `/api/system/init`。

## Ambiguities That Block API Contracts

- [x] CHK008 - `awaiting_input` 状态下用户未响应的超时时间与自动处理规则（如超时后转为 `failed` 或保持等待）是否在 spec 或 API 契约中被精确定义？ [Gap, Blocking, CHK003] → **已解决**：MVP 阶段不设自动超时，任务保持 `awaiting_input` 直到用户提交决策或手动取消，`spec.md` 与 `research-api.md` 已同步。
- [x] CHK009 - `llm_connected: true` 的判定标准是 "配置存在" 还是 "实时可用性探测成功"，是否在 `system-api.md §3` 或相关文档中唯一确定？ [Clarity, Blocking, CHK030] → **已解决**：`spec.md ## Clarifications` 已明确配置存在且非空即视为连接。
- [x] CHK010 - `retry_settings` 的配置模型是否在 `data-model.md §2.15` 中完整覆盖了指数退避策略参数（初始间隔、退避倍数、最大重试次数），以匹配 `spec.md §FR-022` 的 "1s → 2s → 4s" 行为描述？ [Completeness, Blocking, CHK033] → **已解决**：`spec.md ## Clarifications` 已明确固定采用 1s→2s→4s 退避，不额外暴露配置项。

## Notes

- 以上项目若存在未解决的冲突，实现时可能产生数据库 Schema 与 API 契约不兼容、状态机遗漏分支、或配置语义歧义。
- 解决后建议同步更新 `spec.md`、`data-model.md` 与 `contracts/` 中的冲突点，然后勾选本清单。
