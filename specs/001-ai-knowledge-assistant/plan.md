# Implementation Plan: AI 知识管理助手

**Branch**: `001-ai-knowledge-assistant` | **Date**: 2026-04-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-knowledge-assistant/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

实现一个本地运行的 AI 驱动的个人知识管理助手。核心能力包括：知识库管理（文本/文件/链接入库）、基于个人知识库的对话式查询（带来源引用）、异步领域调研报告生成（支持人机交互决策）、知识置信度评估。系统以本地 Web 服务形式运行，用户通过浏览器单用户登录访问，采用 SQLite + sqlite-vec 进行本地持久化，原始媒体文件存储于本地文件系统并按两级目录组织。

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI（Web 框架 + SSE 支持）、sqlite-vec（向量检索）、aiosqlite（异步 SQLite）、httpx（HTTP 客户端，含外部 AI/搜索调用）、cryptography（AES-256-GCM 加密）、argon2-cffi（Argon2id 密钥派生）、pydantic（数据校验与序列化）  
**Storage**: SQLite（主存储）+ sqlite-vec（向量索引）+ FTS5（全文索引）+ 本地文件系统（原始媒体文件，按 `files/AB/CD/<item-id>/` 两级目录组织）  
**Testing**: pytest + pytest-asyncio + httpx（用于 ASGI 应用测试）  
**Target Platform**: 本地运行于 Linux/macOS/Windows，用户通过现代浏览器访问  
**Project Type**: web-service（本地单用户 Web 应用）  
**Performance Goals**: 知识库 100 条时端到端查询响应 ≤2 秒；调研报告在提交后 5 分钟内完成  
**Constraints**: 单文件 ≤1GB；离线时基础功能保持可用；外部 AI 调用需遵循用户隐私策略开关  
**Scale/Scope**: 单用户个人知识库，MVP 阶段不检测重复内容，排除多用户协作与移动端原生应用

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

对照 `constitution.md` 验证以下条款。如有违反，MUST 在 Complexity Tracking 中记录理由。

- **语言统一**: 本 plan 及关联 spec 均使用简体中文。技术术语保留英文原称。
- **规划优先**: 输入 spec.md 已完成且包含详细的功能需求、验收标准和边界说明。
- **简洁设计**: 技术方案为单仓库 Python Web 应用，无微服务或过度分层；依赖均为直接支持需求（FastAPI 负责 Web 与 SSE，sqlite-vec 负责 spec 要求的向量/全文检索，cryptography/argon2-cffi 负责 spec 要求的加密与密钥派生）。无未加证明的抽象。
- **Git 纪律**: 本文档及后续代码变更均计划纳入 Git，遵循小步提交原则。
- **复用优先**: 采用 FastAPI、sqlite-vec、httpx 等成熟开源库，避免自行实现 Web 框架、向量检索或加密原语。
- **安全与质量**: 已识别的外部输入边界包括：用户上传内容长度（≥5 字符）、导入 ZIP 包的文件校验、用户密码强度（登录与密钥派生）、外部 AI API 响应的容错处理、HTTP 爬虫的 URL 白名单/超时限制。
- **独立测试**: 4 个用户故事均有明确的独立测试标准（添加并查询知识、对话引用知识、异步调研报告生成、置信度评估展示）。

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-knowledge-assistant/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── main.py              # FastAPI 应用入口
├── config.py            # 配置定义与加载（Pydantic Settings）
├── db/
│   ├── connection.py    # SQLite + sqlite-vec 连接与迁移
│   ├── models.py        # SQL 表结构定义（通过 SQLAlchemy Core 或直接 SQL）
│   └── migrations/      # 数据库迁移脚本
├── api/
│   ├── routes/
│   │   ├── knowledge.py # 知识库 CRUD、搜索、删除
│   │   ├── chat.py      # 对话查询、会话管理
│   │   ├── research.py  # 调研任务提交、SSE 进度推送
│   │   └── system.py    # 配置、状态、导出/导入
│   ├── schemas/
│   │   └── ...          # Pydantic 请求/响应模型
│   ├── dependencies.py  # 认证依赖、数据库会话注入
│   └── sse.py           # SSE 推送工具
├── services/
│   ├── knowledge_service.py    # 知识条目业务逻辑
│   ├── chat_service.py         # RAG 对话生成
│   ├── research_service.py     # 异步调研报告生成
│   ├── confidence_service.py   # 置信度评估
│   ├── embedding_service.py    # 嵌入向量生成与管理
│   ├── extraction_service.py   # 多媒体文本提取（OCR、转录）
│   └── storage_service.py      # 本地文件存储（含加密读写）
├── ai/
│   ├── client.py        # 兼容 OpenAI API 的 LLM 调用封装
│   ├── search.py        # 搜索源适配（LLM 自带搜索 / Tavily / HTTP 爬虫）
│   └── prompts.py       # 系统提示词模板
├── security/
│   ├── auth.py          # 单用户密码鉴权（JWT / Session）
│   └── crypto.py        # AES-256-GCM + Argon2id
├── tasks/
│   └── queue.py         # 调研任务队列与并发控制
├── web/
│   └── static/          # 前端静态资源（HTML/JS/CSS）
└── utils/
    └── ...              #日志、校验等通用工具

tests/
├── unit/                # 单元测试（服务层、工具函数）
├── integration/         # 集成测试（API 路由、数据库交互）
└── contract/            # 契约测试（外部 AI/搜索适配接口）
```

**Structure Decision**: 采用单后端项目结构（Option 1）。前端以轻量静态页面形式直接由 FastAPI 的 `staticfiles` 托管，MVP 阶段无需独立前端工程。服务端按功能模块划分为 `api/`（路由与入口）、`services/`（核心业务逻辑）、`db/`（持久化）、`ai/`（外部 AI 交互）、`security/`（认证与加密），保持清晰且不过度分层。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

当前 Constitution Check 无违规，无需记录复杂度说明。
