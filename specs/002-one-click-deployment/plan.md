# Implementation Plan: 一键部署功能

**Branch**: `002-one-click-deployment` | **Date**: 2026-04-07 | **Spec**: [spec.md](/home/myhql/code/PersonalKnowledgeAssistant/specs/002-one-click-deployment/spec.md)
**Input**: Feature specification from `/specs/002-one-click-deployment/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

为项目新增一个单一 Python CLI 部署脚本 `deploy.py`，实现从代码克隆到服务运行的"一键部署"。脚本自动完成环境检查、依赖安装、配置模板生成、数据库初始化（委托给应用启动流程）、端口冲突处理和前台服务启动。全程在终端输出清晰的步骤进度，并对错误场景（端口占用、网络中断、进程冲突）提供明确的反馈和处理策略。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Python 标准库（`subprocess`、`socket`、`sys`、`pathlib`），无需额外第三方依赖
**Storage**: N/A（部署脚本本身不持久化数据，仅操作项目既有文件：`.env`、数据库文件、日志目录）
**Testing**: pytest（单元测试）+ 容器化端到端测试
**Target Platform**: Linux / macOS 本地开发和单服务器部署
**Project Type**: cli-tool
**Performance Goals**: 从干净环境到服务成功启动 ≤ 5 分钟（spec SC-001）
**Constraints**: 脚本本身零额外依赖；不修改系统级配置；不引入后台守护进程机制
**Scale/Scope**: 单用户本地应用和单服务器环境，不支持多节点或容器编排平台

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

对照 `constitution.md` 验证以下条款。如有违反，MUST 在 Complexity Tracking 中记录理由。

- **语言统一**: 本 plan 及关联的 spec、tasks 文档是否使用简体中文？
  - **结果**: 通过。spec.md 与本 plan 均使用简体中文。
- **规划优先**: 当前功能是否有已完成的 spec.md 作为输入？需求变更是否同步到设计文档？
  - **结果**: 通过。spec.md 已完成，包含详细的功能需求、验收标准和 9 条澄清记录。
- **简洁设计**: 提出的技术方案是否为当前需求的最小必要复杂度？是否存在未加证明的额外抽象或依赖？
  - **结果**: 通过。部署脚本采用纯 Python 标准库实现，无额外 CLI 框架或系统守护进程依赖。数据库初始化委托给既有 `init_db()`，避免重复实现。
- **Git 纪律**: 本功能的文档和代码变更是否计划纳入 Git 小步提交？
  - **结果**: 通过。文档与脚本实现将遵循小步提交原则。
- **复用优先**: 是否已评估现有工具/库的可复用性？新增外部依赖的理由是否充分？
  - **结果**: 通过。脚本仅使用 Python 标准库，没有新增外部依赖。不引入 Typer/Click/Makefile/Docker 等额外工具，避免增加用户使用前负担。
- **安全与质量**: 是否已识别外部输入边界和必要的验证点？
  - **结果**: 通过。已识别的外部输入边界包括：终端命令行参数（暂无敏感参数）、`.env` 模板文件内容（由脚本生成，用户后续填写）、子进程调用中的路径和端口（内部生成，不直接执行用户输入）。必要的验证点包括：Python 版本校验、pip 可用性校验、端口可用性校验。
- **独立测试**: 各用户故事是否可以独立开发和独立测试？
  - **结果**: 通过。3 个 User Story（首次启动、更新后重新部署、失败反馈）均有明确的独立测试策略和验收场景。

## Project Structure

### Documentation (this feature)

```text
specs/002-one-click-deployment/
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
├── main.py              # FastAPI 应用入口（由 uvicorn 启动）
├── config.py            # 配置模型与加载（读取 .env）
├── db/
│   ├── connection.py    # 数据库初始化（lifespan 中调用）
│   └── schema.sql       # 数据库表结构
└── ...                  # 其他业务模块

tests/
├── unit/                # 单元测试
├── integration/         # 集成测试
└── contract/            # 契约/接口测试

deploy.py                # 一键部署 CLI 脚本（新增）
```

**Structure Decision**: 采用单项目结构。在根目录新增 `deploy.py` 作为部署入口，不改动原有 `src/` 和 `tests/` 的模块划分。部署脚本的单元测试可放在 `tests/unit/test_deploy.py`，端到端测试可通过容器或临时虚拟环境在 CI 中执行。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 无 | - | - |

## Constitution Check (Post-Design)

*Re-evaluated after Phase 1 design completion.*

- **语言统一**: data-model.md、quickstart.md、contracts/ 及本 plan 均使用简体中文。通过。
- **规划优先**: research.md 已解决所有 NEEDS CLARIFICATION；data-model.md 和 contracts/ 均基于 spec.md 生成，无未经文档化的设计变更。通过。
- **简洁设计**: 项目结构保持单项目，deploy.py 仅为一层编排脚本，无过度抽象；无新增外部依赖。通过。
- **Git 纪律**: 文档变更将纳入 Git 小步提交。通过。
- **复用优先**: contracts/ 中定义的 CLI 契约充分利用 Python 标准库特性，无重复造轮子。通过。
- **安全与质量**: data-model.md 中识别了部署配置实体的验证规则；contracts/ 中命令参数和错误输出边界均已定义。通过。
- **独立测试**: 3 个 User Story 对应的测试策略在 quickstart.md 中明确，可独立验证。通过。

**Phase 1 Gate**: PASS。无违反宪法条款的设计决策。
