# Phase 0 Research: 一键部署功能

> 生成日期: 2026-04-07 | 关联 Spec: [spec.md](./spec.md) | 关联 Plan: [plan.md](./plan.md)

---

## 1. 部署脚本整体架构

**Decision**: 采用单一 Python CLI 脚本 `deploy.py`（位于项目根目录），基于 Python 标准库实现，不引入额外第三方依赖。

**Rationale**:
- 标准库足以覆盖环境检查、文件操作、子进程调用和终端输出，无需增加用户在使用脚本前安装其他 CLI 框架（如 Click/Typer）的负担。
- 单一脚本的可读性高，便于用户理解部署流程；也能直接通过 `python deploy.py` 执行，符合 spec FR-001 的"单一命令"要求。
- 部署脚本的职责是编排步骤，而非替换操作系统包管理器；复杂的环境准备（如系统级 Python 安装）不在本功能范围内。

**Alternatives considered**:
- Makefile / shell 脚本：跨平台兼容性差（Windows 支持弱），且错误处理和进度输出不如 Python 灵活。
- Docker Compose：虽然能一键启动，但引入了额外的 Docker 依赖，违反"最小必要复杂度"原则，且 spec 明确限定为本地开发和单服务器环境。
- Typer/Click：会增加用户在运行脚本前需要安装的依赖，与"开箱即用"的目标冲突。

---

## 2. 前置条件检查策略

**Decision**: 在 `deploy.py` 中内建 `check_prerequisites()` 函数，按顺序检查以下项目，任一失败即输出明确错误并退出：
1. Python 解释器版本 ≥ 3.11
2. `pip` 命令可用（或 `python -m pip`）
3. `socket` 模块可用（用于端口检测，标准库已包含）

**Rationale**:
- 本项目的运行时依赖已经非常简单，仅需 Python + pip；其余所有依赖（FastAPI、sqlite-vec 等）均通过 pip 安装。
- `socket` 是 Python 标准库的一部分，无需额外检查系统工具即可实现端口占用检测。
- 检查失败的提示信息应包含修复建议（如"请安装 Python 3.11 或更高版本"）。

---

## 3. 依赖安装与网络容错

**Decision**: 使用 `subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])` 安装依赖，网络失败时最多自动重试 3 次，每次间隔 2 秒。

**Rationale**:
- `python -m pip` 比直接调用 `pip` 更可靠，能确保使用当前解释器对应的包管理器。
- 3 次重试 + 固定间隔是处理瞬时网络波动的最小有效策略；更复杂的指数退避对本场景收益有限。
- 重试耗尽后输出完整 pip 错误日志的最后一屏，帮助用户定位问题。

---

## 4. 配置文件缺失处理

**Decision**: 若 `.env` 文件不存在，`deploy.py` 自动在项目根目录生成 `.env.example` 并重命名为 `.env` 的提示文本，然后暂停并退出，引导用户填写必要字段后再重新运行脚本。

**Rationale**:
- 环境配置（如 API Key）具有高度敏感性，不适合由脚本自动随机生成或硬编码。
- 生成模板并暂停是最安全且用户可控的方案，符合 spec FR-007 的明确要求。
- 模板中应包含所有 `Settings` 模型中定义的字段注释，但敏感字段留空。

---

## 5. 数据库初始化机制

**Decision**: 数据库初始化不直接由 `deploy.py` 操作数据库文件，而是委托给 FastAPI 应用启动流程：
- `src/main.py` 的 `lifespan` 中已经调用 `init_db()`。
- `deploy.py` 在启动 uvicorn 前确保 `data/` 目录存在即可。

**Rationale**:
- 与 spec 澄清结果一致（Q8）：由 FastAPI 应用在启动时自动执行 `init_db()`。
- 避免部署脚本与数据库 schema 产生强耦合；schema 演进时只需维护 `src/db/schema.sql`。
- `init_db()` 会安全处理虚拟表（`IF NOT EXISTS` / `DROP IF EXISTS`  Recreation），重复启动不会破坏数据。

---

## 6. 端口冲突与动态分配

**Decision**: 默认端口 8000；启动前使用 `socket.socket().bind(('', port))` 检测端口是否可用。若被占用，依次尝试 8001、8002……直到找到可用端口，并在终端明确告知用户实际使用的端口。

**Rationale**:
- 标准库 `socket` 提供了跨平台的端口可用性检测能力，无需引入外部网络工具。
- 线性递增探测（8000 → 8001 → …）逻辑简单、可预期，也便于测试验证。
- 端口号必须在部署脚本输出中醒目展示，确保用户知道如何访问服务。

---

## 7. 服务运行模式

**Decision**: `deploy.py` 通过 `subprocess.run()` 前台启动 `uvicorn src.main:app --host 127.0.0.1 --port <port>`，日志直接输出到终端，用户通过 Ctrl+C 停止服务。

**Rationale**:
- 前台运行最符合开发场景的直觉；用户能直接看到应用启动日志和运行状态。
- 单服务器本地部署不需要将服务注册为系统守护进程，`systemd`/`supervisor` 等方案超出本功能范围。
- 子进程结束后，`deploy.py` 也随之退出。

---

## 8. 进程冲突检测

**Decision**: 在启动 uvicorn 前，检测默认端口（及后续动态分配端口）是否已有 uvicorn/FastAPI 进程在监听。若检测到应用已在运行，输出错误信息要求用户手动停止现有进程后再重新执行 `deploy.py`。

**Rationale**:
- 与 spec 澄清结果一致（Q5）：不允许自动重启或启动多实例。
- 检测方式优先使用"端口占用检测"（因为服务前台运行时绑定端口是确定性行为），辅助通过 `ps` / `lsof` 等工具检查 uvicorn 进程（若可用）。
- 这种策略简单且可靠，避免了维护 PID 文件带来的文件生命周期同步问题。

---

## 9. 实时进度输出

**Decision**: `deploy.py` 在终端以步骤列表形式输出进度，每个步骤显示 `[OK]` / `[FAIL]` / `[SKIP]` 状态，最后汇总。

**Rationale**:
- 文本进度输出是实现成本最低、兼容性最好的方案，无需引入 `rich`、`tqdm` 等第三方库。
- 清晰的步骤标识符（如 `[1/5] 检查环境`、`[2/5] 安装依赖`）让用户能准确跟踪当前阶段， failure 时也便于定位问题步骤。

---

## 10. 测试策略

**Decision**: 使用 `pytest` 对 `deploy.py` 中的纯函数（环境检查、端口探测、配置模板生成）进行单元测试；通过 GitHub Actions 或本地干净容器执行端到端测试。

**Rationale**:
- `deploy.py` 包含较多 IO 和子进程调用，完整端到端测试在 CI 容器中运行最可靠。
- 可单元测试的逻辑应抽离为独立函数（如 `is_port_available(port)`、`check_python_version()`），以提高可测试性。

---

## 11. 总结

本研究阶段确认以下关键技术选择：

1. **脚本形式**：单一 `deploy.py`，纯标准库实现。
2. **前置检查**：Python 3.11+、pip、`socket` 可用性。
3. **依赖安装**：`python -m pip install -r requirements.txt`，失败重试 3 次。
4. **配置缺失**：自动生成 `.env` 模板并暂停。
5. **数据库初始化**：委托给 FastAPI `lifespan` 中的 `init_db()`。
6. **端口冲突**：默认 8000，线性探测动态分配。
7. **运行模式**：前台 `uvicorn` 子进程，Ctrl+C 停止。
8. **进程冲突**：检测到已有实例时要求用户手动停止。
9. **进度输出**：文本步骤列表，带 `[OK]/[FAIL]` 标记。
10. **测试**：单元测试 + 容器端到端测试。

无剩余 NEEDS CLARIFICATION。
