# Tasks: 一键部署功能

**Input**: Design documents from `/specs/002-one-click-deployment/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included for deployment script reliability and to support the independent test criteria defined in spec.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Review existing project structure and confirm no structural changes are needed

- [x] T001 [P] Verify existing project structure matches plan.md (`src/`, `tests/`, `requirements.txt`, `.env` if present)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core `deploy.py` structure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Create `deploy.py` skeleton at repository root with step runner, progress formatter (`[N/5] ... [STATUS]`), and main flow orchestration
- [x] T003 Define `DeploymentConfig` dataclass and step execution utilities inside `deploy.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 首次一键启动服务 (Priority: P1) 🎯 MVP

**Goal**: 开发者从代码仓库克隆项目后，只需执行单一命令，即可自动完成环境准备、依赖安装、数据库初始化并启动服务

**Independent Test**: 在干净的机器或容器环境中执行 `python deploy.py`，验证服务是否能在 5 分钟内成功启动并可通过浏览器/接口访问

### Implementation for User Story 1

- [x] T004 [P] [US1] Implement `check_python_version()` in `deploy.py` (requires >= 3.11, prints actionable error on failure)
- [x] T005 [P] [US1] Implement `check_pip_available()` in `deploy.py` (tries `python -m pip`, prints actionable error on failure)
- [x] T006 [US1] Implement `install_dependencies()` in `deploy.py` (runs `pip install -r requirements.txt`, retries up to 3 times with 2s delay, prints last error)
- [x] T007 [US1] Implement `ensure_env_file()` in `deploy.py` (generates `.env` template matching `src/config.py` fields if missing, then pauses with clear instructions)
- [x] T008 [US1] Implement `find_available_port()` in `deploy.py` (probes 8000, 8001, 8002... using `socket.bind`, returns first available port)
- [x] T009 [US1] Implement `start_service()` in `deploy.py` (foreground `subprocess.run` launching `uvicorn src.main:app --host 127.0.0.1 --port <port>`)
- [x] T010 [P] [US1] Add `ensure_directories()` in `deploy.py` (creates `data/` and `logs/` if missing)
- [x] T011 [US1] Wire US1 steps into `deploy.py` main flow with progress output and final URL message

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - 更新后重新部署 (Priority: P2)

**Goal**: 当代码有更新时，开发者执行同一命令即可重新构建并部署最新版本，无需手动清理旧环境或重启服务

**Independent Test**: 在已部署的环境中拉取新代码后再次执行 `python deploy.py`（先停止旧服务），验证服务是否平滑更新至新版本且数据不丢失

### Implementation for User Story 2

- [x] T012 [US2] Implement `is_service_running()` in `deploy.py` (detects if the application is already listening on the target port using `socket.connect` or process probes)
- [x] T013 [US2] Wire re-deployment guard into `deploy.py` main flow: if `is_service_running()` returns true, print error and exit without corrupting data

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - 部署失败时的清晰反馈 (Priority: P3)

**Goal**: 当部署过程中出现错误（如缺少依赖、端口占用、配置缺失）时，系统应给出明确的错误提示和可行的解决建议

**Independent Test**: 故意制造部署失败场景（如删除必要配置文件或占用服务端口），执行 `python deploy.py`，验证输出的错误信息是否明确且可指导修复

### Implementation for User Story 3

- [x] T014 [US3] Implement `format_error()` in `deploy.py` with actionable suggestions for each failure category (Python version, pip missing, network failure, config missing, port conflict, process conflict)
- [x] T015 [US3] Add per-step error context in `deploy.py` so that any step failure prints: the step name, the root cause, and a concrete fix suggestion matching `contracts/cli-contract.md`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Testing, documentation, and cross-cutting reliability improvements

- [x] T016 [P] Add unit tests for `check_python_version`, `check_pip_available`, `find_available_port`, and `ensure_env_file` in `tests/unit/test_deploy.py`
- [x] T017 Add end-to-end validation script for `deploy.py` in `tests/integration/test_deploy_e2e.py` (uses subprocess to verify happy path and guarded re-deploy)
- [x] T018 Run quickstart.md validation: execute each scenario in a clean environment and fix discrepancies
- [x] T019 Review `deploy.py` against `contracts/cli-contract.md` and fix any output format or exit code mismatches

---

## Phase 7: Daemon Mode & Subcommands (Scope Change CR-001)

**Purpose**: Add background daemon mode, status query, and restart capability with zero extra dependencies

### User Story 4 — Background Daemon

- [ ] T020 [P] [US4] Implement `daemonize()` using `os.fork()` + `os.setsid()` + second fork inside `deploy.py`
- [ ] T021 [US4] Implement PID file helpers (`read_pid_file`, `write_pid_file`, `remove_pid_file`, `is_pid_alive`, `cleanup_stale_pid`) in `deploy.py`
- [ ] T022 [US4] Implement `start` subcommand flow in `deploy.py`: environmental checks → install deps → ensure `.env` → find port → daemonize → start uvicorn with stdout/stderr redirected to `logs/deploy.log`
- [ ] T025 [US4] Redirect daemon stdout/stderr to `logs/deploy.log` using `subprocess.DEVNULL` and log file dup2 or `Popen(stdout=..., stderr=...)`

### User Story 5 — Status

- [ ] T023 [P] [US5] Implement `status` subcommand in `deploy.py`: print running (pid + port + url) or stopped state

### User Story 6 — Restart

- [ ] T024 [US6] Implement `restart` subcommand in `deploy.py`: stop old process (SIGTERM wait 5s → SIGKILL), clean PID file, then start new daemon

### Testing & Validation

- [ ] T026 [P] Update unit tests for PID helpers and stale PID detection in `tests/unit/test_deploy.py`
- [ ] T027 Add daemon workflow integration test in `tests/integration/test_deploy_daemon.py` (start → status → restart → status)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) and after US1 core functions exist (T002-T003 foundation ready)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) and after US1/US2 functions exist (error handling wraps all prior logic)

### Within Each User Story

- Models/utilities before service logic
- Service logic before wiring into main flow
- Core implementation before integration/polish
- Story complete before moving to next priority

### Parallel Opportunities

- T004 and T005 can be implemented in parallel (different helper functions, no shared state)
- T010 and T016 can run in parallel (different files)
- All unit test tasks in Polish phase can run in parallel

---

## Parallel Example: User Story 1

```bash
# Implement environment checks in parallel:
Task: "Implement check_python_version() in deploy.py"
Task: "Implement check_pip_available() in deploy.py"
Task: "Add ensure_directories() for data/ and logs/ in deploy.py"

# After checks are done, proceed to dependency install and port detection:
Task: "Implement install_dependencies() with retry logic in deploy.py"
Task: "Implement find_available_port() in deploy.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `python deploy.py` in a clean environment and verify service starts
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (core deployment logic)
   - Developer B: User Story 2 (process conflict detection)
   - Developer C: User Story 3 (error messages)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files or independent functions, no runtime dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
