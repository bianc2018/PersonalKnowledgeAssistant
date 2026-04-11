# 全项目 QA 验收报告

**验收时间**: 2026-04-11  
**验收分支**: `001-ai-knowledge-assistant`  
**Ollama 地址**: `http://192.168.1.3:11434/v1`  
**LLM 模型**: `qwen3.5:latest`  
**Embedding 模型**: `nomic-embed-text:latest` (768 维)  
**Web 搜索**: 已启用

---

## 1. 自动化测试

| 测试套件 | 结果 |
|---------|------|
| 单元 / 集成测试 (`pytest tests/`) | **31/31 通过** |
| 端到端扩展 QA (手动脚本) | **12/12 通过** |

---

## 2. 端到端功能验证

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 前端首页访问 | PASS | `/` 返回 SPA 页面 |
| 系统初始化 | PASS | `POST /api/system/init` 创建管理员 |
| 用户登录 | PASS | `POST /api/auth/login` 返回有效 JWT |
| 系统状态 | PASS | LLM/Embedding 均检测为可用 |
| 知识创建（文本） | PASS | 创建成功并生成 768 维嵌入 |
| 知识列表查询 | PASS | 返回包含标签与置信度的列表 |
| 聊天对话 + RAG | PASS | 回答引用知识库片段，带 `[1]` 标注 |
| 研究任务创建 | PASS | `POST /api/research` 返回 202 |
| 研究任务轮询 / 自动完成 | PASS | 任务历经 `awaiting_input` 后自动完成 |
| 研究报告保存到知识库 | PASS | `POST /api/research/{id}/save` 成功 |
| 系统数据导出 | PASS | `POST /api/system/export` 返回附件 |
| 静态资源访问 | PASS | `/static/js/app.js` 正常 |
| 附件下载 404 | PASS | 非法附件 ID 返回 404 |

---

## 3. 运行中发现并修复的关键问题

### P0 - 向量维度不匹配
- **根因**: `src/db/schema.sql` 硬编码 `FLOAT[1536]`，且 `src/db/connection.py` 的 SQL 引用了未初始化的形参 `embedding_dim` 而非实际变量 `dim`。
- **修复**: 删除 schema.sql 中的硬编码 `vec_chunks` 定义，并修正 connection.py 的动态建表语句。

### P0 - Research 工作流 Schema 不一致
- **根因**: `run_research_task` 中的 SQL 引用了 `research_tasks.updated_at` 和 `research_citations.created_at`，但 schema 未定义这两列。
- **修复**: 从对应 SQL 中移除不存在的数据库字段。

### P1 - Research 任务在 `awaiting_input` 后无法继续
- **根因**: `respond_to_task` 在唤醒阻塞工作线程的同时，又将同一任务重新入队，导致两个工作线程并发执行同一任务；且重新入队的任务因状态检查 Guard 被直接丢弃。
- **修复**: 移除 `respond_to_task` 中多余的 `submit_task`，仅通过 Event 唤醒原工作线程。

### P1 - `section_type` CHECK 约束失败
- **根因**: LLM 生成的大纲偶尔包含 schema 允许值之外的 `type`（如 `overview`）。
- **修复**: 在写入 `research_sections` 前对 `section_type` 进行校验，非法值回退为 `summary`。

### P1 - Ollama 连接配置失效
- **根因**: 嵌套 `BaseSettings`（`LLMConfig`、`EmbeddingConfig`）未继承父级 `.env` 配置，导致 `base_url` 和 `model` 为空；且空 `api_key` 被 `AsyncOpenAI` 拒绝。
- **修复**: 为嵌套配置显式设置 `model_config`（含 `env_prefix`），并在 `api_key` 为空时使用 `"not-needed"` 占位符。

---

## 4. 环境说明

Ollama 服务器 (`192.168.1.3:11434`) 上的 `qwen3.5:latest` 响应较慢，单条 `chat.completions` 请求平均耗时约 60-120 秒。为保证 QA 通过，验收脚本将 `TIMEOUT_SECONDS` 临时调整为 180 秒、`RETRY_TIMES` 调整为 1 次。在日常使用中，若 Ollama 性能提升，可恢复默认值（30 秒 / 3 次重试）。

---

## 5. 结论

全项目 QA 验收 **通过**。后端 API、RAG 聊天、研究任务工作流、导出与前端静态资源均功能正常。所有阻塞性问题已在本次验收中定位并修复，相关代码已提交至当前分支。
