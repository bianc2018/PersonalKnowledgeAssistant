# Implementation Plan: AI 知识管理助手

**Branch**: `001-ai-knowledge-assistant` | **Date**: 2026-04-05 | **Spec**: [spec.md](/home/myhql/code/PersonalKnowledgeAssistant/specs/001-ai-knowledge-assistant/spec.md)
**Input**: Feature specification from `/specs/001-ai-knowledge-assistant/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

实现一个本地运行的 AI 驱动个人知识管理助手。核心能力包括：用户通过文本、文件或网页链接添加知识条目；系统自动提取多媒体内容的可搜索文本；支持基于自然语言的对话式知识查询（RAG），并标注引用来源；支持异步生成结构化领域调研报告（通过 SSE 实时推送进度）；对知识条目进行置信度评估并可视化展示。系统采用 SQLite + sqlite-vec + FTS5 作为本地存储与检索方案，原始媒体文件按两级目录组织并存于本地文件系统，采用 AES-256-GCM 加密保护。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI（Web 框架 + SSE）、sqlite-vec（向量/全文检索）、aiosqlite（异步 SQLite）、httpx（HTTP 客户端，含外部 AI/搜索调用）、cryptography（AES-256-GCM 加密）、argon2-cffi（Argon2id 密钥派生）、pydantic（数据校验与序列化）
**Storage**: SQLite（主存储）+ sqlite-vec（向量/全文索引）+ 本地文件系统（原始媒体文件，按 `files/AB/CD/<item-id>/` 两级目录组织）
**Testing**: pytest
**Target Platform**: Linux 桌面/服务器本地服务，通过浏览器访问
**Project Type**: web-service
**Performance Goals**: 知识库包含 100 条知识时，查询和展示端到端响应时间 ≤2 秒
**Constraints**: 单文件大小 ≤1GB；本地优先，默认不发送完整知识到外部 AI；外部服务不可用时核心功能保持可用
**Scale/Scope**: 单用户个人应用，MVP 阶段不检测重复内容，暂不排除多用户协作和移动端原生应用

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

对照 `constitution.md` 验证以下条款。如有违反，MUST 在 Complexity Tracking 中记录理由。

- **语言统一**: 本 plan 及关联的 spec、tasks 文档是否使用简体中文？
  - **结果**: 通过。spec.md 与本 plan 均使用简体中文。
- **规划优先**: 当前功能是否有已完成的 spec.md 作为输入？需求变更是否同步到设计文档？
  - **结果**: 通过。spec.md 已完成并包含详细的功能需求、验收标准和澄清记录。
- **简洁设计**: 提出的技术方案是否为当前需求的最小必要复杂度？是否存在未加证明的额外抽象或依赖？
  - **结果**: 通过。技术栈选择了成熟且针对需求的最小组合：FastAPI 提供 Web + SSE，SQLite + sqlite-vec 满足本地向量/全文检索，cryptography + argon2-cffi 满足文件加密需求。无未经验证的抽象层。
- **Git 纪律**: 本功能的文档和代码变更是否计划纳入 Git 小步提交？
  - **结果**: 通过。所有文档和后续代码变更将遵循小步提交原则。
- **复用优先**: 是否已评估现有工具/库的可复用性？新增外部依赖的理由是否充分？
  - **结果**: 通过。所有主要依赖均为经过验证的现有方案：FastAPI 替代自研 HTTP/SSE 服务器；sqlite-vec 替代专用向量数据库；aiosqlite 替代同步 SQLite 封装；httpx 替代 requests 以支持异步；cryptography 和 argon2-cffi 为 Python 生态主流安全库。无重复造轮子。
- **安全与质量**: 是否已识别外部输入边界和必要的验证点？
  - **结果**: 通过。已识别的外部输入边界包括：用户上传的文本/文件/URL、外部 AI/搜索 API 响应、导入的 ZIP 备份、JWT Token、用户密码。必要的验证点包括：内容最小长度校验（≥5 字符）、文件大小限制（≤1GB）、标签长度/空白校验、导入元数据校验、SQL 注入防护（参数化查询）、XSS 防护（正确转义输出）。
- **独立测试**: 各用户故事是否可以独立开发和独立测试？
  - **结果**: 通过。4 个 User Story（知识管理、对话查询、调研报告、置信度评估）均具备独立的验收场景和可测试的边界。

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
├── config.py            # 配置模型与加载
├── auth/
│   ├── router.py        # 登录/鉴权路由
│   ├── dependencies.py  # JWT 校验依赖
│   └── crypto.py        # 密码派生、文件加解密
├── knowledge/
│   ├── router.py        # 知识条目 CRUD、搜索、导入导出
│   ├── service.py       # 知识业务逻辑
│   ├── models.py        # 知识相关 Pydantic 模型
│   └── extractor.py     # 多媒体文本提取封装
├── chat/
│   ├── router.py        # 对话/SSE 路由
│   ├── service.py       # RAG 检索与回答生成
│   └── models.py        # 对话相关 Pydantic 模型
├── research/
│   ├── router.py        # 调研任务路由
│   ├── service.py       # 调研流程编排
│   ├── models.py        # 调研相关 Pydantic 模型
│   └── worker.py        # 异步调研任务执行
├── profile/
│   ├── service.py       # 用户画像提取与更新
│   └── models.py        # UserProfile 模型
├── db/
│   ├── connection.py    # aiosqlite 连接管理
│   ├── schema.sql       # 数据库表结构
│   └── migrations/      # 数据库迁移脚本
├── search/
│   ├── vec.py           # sqlite-vec 向量操作
│   ├── fts.py           # FTS5 全文检索操作
│   └── hybrid.py        # 混合检索与排序
├── external/
│   ├── llm.py           # LLM API 客户端
│   ├── search.py        # 搜索 API 客户端 + 爬虫回退
│   └── retry.py         # 重试与退避策略
└── tasks/
    └── queue.py         # 调研任务队列与并发控制

tests/
├── unit/                # 单元测试
├── integration/         # 集成测试
└── contract/            # 契约/接口测试
```

**Structure Decision**: 采用单项目结构（Option 1）。按业务领域（knowledge、chat、research、profile、auth）划分模块，所有模块共享同一 FastAPI 应用。db/ 集中管理数据库连接与 schema，search/ 集中管理检索能力，external/ 集中管理外部服务调用。 tests/ 按测试类型分层，与 src/ 平行放置。

## Constitution Check (Post-Design)

*Re-evaluated after Phase 1 design completion.*

- **语言统一**: data-model.md、quickstart.md、contracts/ 及本 plan 均使用简体中文。通过。
- **规划优先**: research.md 已解决所有 NEEDS CLARIFICATION；data-model.md 和 contracts/ 均基于 spec.md 生成，无未经文档化的设计变更。通过。
- **简洁设计**: 项目结构采用单项目领域分层，无过度抽象的 ORM 层或微服务拆分；依赖清单与 research.md 决策一致。通过。
- **Git 纪律**: 文档变更将纳入 Git 小步提交。通过。
- **复用优先**: contracts/ 中定义的 API 契约充分利用 FastAPI 原生特性（Pydantic、SSE、StaticFiles），无重复造轮子。通过。
- **安全与质量**: data-model.md 中识别了输入验证规则（VAL-001 ~ VAL-006）；contracts/ 中认证、加密、导出导入边界均已定义。通过。
- **独立测试**: 4 个 User Story 对应的 API 契约和测试策略在 quickstart.md 中明确，可独立验证。通过。

**Phase 1 Gate**: PASS。无违反宪法条款的设计决策。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 无 | - | - |

