# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供本仓库的工作指导。

## 项目工作规则

### 1. 语言要求
- **所有回复和文档使用简体中文**
- 代码注释可根据上下文使用中文或英文
- 技术术语可保留英文（如 API、HTTP、JSON 等）

### 2. Git 工作流
- **所有代码和文档变更必须使用 Git 管理**
- 每次变更确认无误后应当进行本地提交（`git commit`）
- **不要自动推送到远程仓库**（`git push` 需要用户明确授权）
- 遵循小步提交原则，保持提交粒度合理
- 提交信息应简洁清晰地描述变更内容


### 3. 开发习惯
- 先规划，后编码
- 保持代码简洁，避免过度设计
- 优先使用现有工具和库，避免重复造轮子

## Active Technologies
- Python 3.11+ + FastAPI（Web 框架 + SSE 支持）、sqlite-vec（向量/全文检索）、aiosqlite（异步 SQLite）、httpx（HTTP 客户端，含外部 AI/搜索调用）、cryptography（AES-256-GCM 加密）、argon2-cffi（Argon2id 密钥派生）、pydantic（数据校验与序列化） (001-ai-knowledge-assistant)
- SQLite（主存储）+ sqlite-vec（向量/全文索引）+ 本地文件系统（原始媒体文件，按 `files/AB/CD/<item-id>/` 两级目录组织） (001-ai-knowledge-assistant)
- Python 3.11+ + FastAPI（Web 框架 + SSE）、sqlite-vec（向量/全文检索）、aiosqlite（异步 SQLite）、httpx（HTTP 客户端，含外部 AI/搜索调用）、cryptography（AES-256-GCM 加密）、argon2-cffi（Argon2id 密钥派生）、pydantic（数据校验与序列化） (001-ai-knowledge-assistant)
- Python 3.11+ + Python 标准库（`subprocess`、`socket`、`sys`、`pathlib`），无需额外第三方依赖 (002-one-click-deployment)
- N/A（部署脚本本身不持久化数据，仅操作项目既有文件：`.env`、数据库文件、日志目录） (002-one-click-deployment)

## Recent Changes
- 001-ai-knowledge-assistant: Added Python 3.11+ + FastAPI（Web 框架 + SSE 支持）、sqlite-vec（向量/全文检索）、aiosqlite（异步 SQLite）、httpx（HTTP 客户端，含外部 AI/搜索调用）、cryptography（AES-256-GCM 加密）、argon2-cffi（Argon2id 密钥派生）、pydantic（数据校验与序列化）
