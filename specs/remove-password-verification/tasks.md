# Task Breakdown: 去除密码校验（本地个人部署模式）

> Feature: `remove-password-verification` | Generated: 2026-04-12
> Based on: [plan.md](./plan.md) | [spec.md](./spec.md) | [product-spec.md](./product-spec/product-spec.md)

---

## Group A: Backend Foundation — 数据库与认证层改造

### A1. 数据库 Schema 变更
- [ ] **Task A1.1** 修改 `src/db/schema.sql`，为 `system_config` 表新增 `password_enabled INTEGER NOT NULL DEFAULT 1 CHECK(password_enabled IN (0, 1))`
  - **Covers:** FR-001
  - **AC:** 新创建的数据库包含该列；旧数据库在迁移后默认值为 `1`

### A2. Auth Crypto — 无密码模式稳定 master_key
- [ ] **Task A2.1** 在 `src/auth/crypto.py` 中新增 `get_no_auth_master_key()` 函数
  - **Covers:** FR-006
  - **AC:** 函数基于 `SHA256(settings.secret_key)` 返回 32 字节；同一 `SECRET_KEY` 下输出稳定

### A3. Auth Dependencies — 短路放行
- [ ] **Task A3.1** 修改 `src/auth/dependencies.py` 中的 `get_current_user`
  - **Covers:** FR-005
  - **AC:** 当 `password_enabled == false` 时，无需 `Authorization` Header 即可返回 `CurrentUser(token="no-auth")`；同时把固定 master_key 写入缓存

### A4. Auth Router — 无密码登录分支
- [ ] **Task A4.1** 修改 `src/auth/router.py` 中 `LoginRequest.password` 为可选（`str | None = None`）
  - **Covers:** FR-004
  - **AC:** Pydantic 允许空对象 `{}` 作为请求体
- [ ] **Task A4.2** 在 `login` 处理函数中增加 `password_enabled == false` 分支
  - **Covers:** FR-004
  - **AC:** 该分支返回固定 token `"no-auth"` 和 1 年有效期；并将固定 master_key 写入缓存
  - **AC:** 有密码模式下的现有逻辑完全保留且正常工作

### A5. System Router — 初始化与状态接口改造
- [ ] **Task A5.1** 修改 `src/system/router.py`：`InitRequest` 增加可选 `password_enabled: bool = False`，`password` 改为可选
  - **Covers:** FR-002
  - **AC:** 当 `password_enabled=true` 且未提供 `password` 时返回 400 错误
  - **AC:** 当 `password_enabled=false` 时，`password_hash` 和 `salt` 存储为 `NULL`
- [ ] **Task A5.2** 修改 `src/system/router.py`：`GET /api/system/status` 返回增加 `password_enabled` 字段
  - **Covers:** FR-003
  - **AC:** 返回值包含布尔值 `password_enabled`

### A6. System Service — 备份导出/导入兼容
- [ ] **Task A6.1** 检查并修改 `src/system/service.py` 中 `export_backup` / `import_backup`，在无密码模式下跳过密码校验
  - **Covers:** FR-011
  - **AC:** 无密码模式下导出/导入不再要求输入密码即可执行

---

## Group B: Frontend Adaptation — 前端初始化向导与自动登录

### B1. 初始化页面改造
- [ ] **Task B1.1** 修改 `src/web/static/js/pages/init.js`，增加「启用密码保护」/「无需密码，直接访问」单选卡片
  - **Covers:** FR-007, US-01 AC-01
  - **AC:** 默认选中「无需密码，直接访问」
  - **AC:** 选中「启用密码保护」时展开密码输入框和确认密码输入框
  - **AC:** 前端校验：两次密码必须一致且非空（仅在启用密码时）
- [ ] **Task B1.2** 修改 init 表单提交逻辑，根据选项携带 `password_enabled` 和可选的 `password`
  - **Covers:** FR-007, US-01 AC-02/AC-03
  - **AC:** `password_enabled=false` 时请求体可省略 `password`

### B2. 应用入口自动登录
- [ ] **Task B2.1** 修改 `src/web/static/js/app.js`，在应用启动时先请求 `/api/system/status`
  - **Covers:** FR-008, US-01 AC-02
  - **AC:** 若 `password_enabled=false`，自动调用 `/api/auth/login`（空参数）获取 token 并存入存储
  - **AC:** 成功后直接进入主界面，不闪现登录页
  - **AC:** 若 `password_enabled=true` 且无 token，仍跳转 `#/login`

### B3. 路由守卫适配
- [ ] **Task B3.1** 验证 `src/web/static/js/router.js` 在已有 no-auth token 时不再拦截
  - **Covers:** FR-008
  - **AC:** no-auth 模式下可直接访问所有受保护路由

---

## Group C: CLI / Deployment Script — 重置密码

### C1. deploy.py 新增 reset-password 子命令
- [ ] **Task C1.1** 在 `deploy.py` 中新增 `reset-password` 子命令入口
  - **Covers:** FR-009, US-02 AC-01
  - **AC:** 命令可通过 `python deploy.py reset-password` 调用
- [ ] **Task C1.2** 实现 `reset-password` 的交互式确认逻辑
  - **Covers:** FR-010, US-02 AC-02/AC-03
  - **AC:** 输出红色 ANSI 警告并列出将被删除的数据/文件路径
  - **AC:** 仅当用户输入 `RESET` 时才继续；否则输出「操作已取消」并退出
- [ ] **Task C1.3** 实现 `reset-password` 的数据清理逻辑
  - **Covers:** FR-009, US-02 AC-04
  - **AC:** 若服务在运行，先调用 `stop_service`
  - **AC:** 删除 `data/app.db` 和 `files/` 目录（若已不存在则提示跳过）
  - **AC:** 最终输出成功信息，提示用户重新初始化

---

## Group D: Testing & Regression — 测试覆盖

### D1. 单元测试
- [ ] **Task D1.1** 为 `get_no_auth_master_key()` 添加单元测试
  - **Covers:** FR-006
  - **AC:** 验证输出长度 32 字节；同一 `SECRET_KEY` 下多次调用结果一致；不同 `SECRET_KEY` 结果不同
- [ ] **Task D1.2** 为 `get_current_user` no-auth 分支添加单元/集成测试
  - **Covers:** FR-005
  - **AC:** `password_enabled=0` 时无 Header 返回 `CurrentUser("no-auth")` 且缓存中有 master_key

### D2. 集成测试 — 无密码模式全流程
- [ ] **Task D2.1** 在 `tests/conftest.py` 中新增 `no_auth_client` fixture
  - **Covers:** 测试基础设施
  - **AC:** fixture 初始化时 `password_enabled=False`，不提交密码
- [ ] **Task D2.2** 编写无密码初始化集成测试
  - **Covers:** FR-002, FR-003, US-01 AC-02
  - **AC:** `POST /api/system/init` 后 `GET /api/system/status` 返回 `password_enabled: false`
- [ ] **Task D2.3** 编写无密码登录绕过集成测试
  - **Covers:** FR-004, FR-005, US-01 AC-02
  - **AC:** `POST /api/auth/login` 空参数返回 `"no-auth"` token；不带 `Authorization` 访问 `/api/system/config` 返回 200
- [ ] **Task D2.4** 编写无密码模式下附件加解密集成测试
  - **Covers:** FR-006, US-03 AC-01/AC-02
  - **AC:** 上传文件保存为 `.enc`；通过下载接口可正确解密原文件内容

### D3. 集成测试 — 回归与兼容性
- [ ] **Task D3.1** 运行全部现有集成测试并修复回归问题
  - **Covers:** FR-012
  - **AC:** 所有已有测试 100% 通过

### D4. CLI 测试
- [ ] **Task D4.1** 为 `deploy.py reset-password` 添加单元测试（mock 输入/文件系统）
  - **Covers:** FR-009, FR-010
  - **AC:** 输入 `RESET` 时正确删除文件；输入其他内容时不删除任何文件并返回 0

---

## Task Coverage Matrix

### Must Have User Stories Coverage

| User Story | Covered By Tasks |
|------------|------------------|
| US-01 | A1.1, A5.1, A5.2, B1.1, B1.2, B2.1, B3.1, D2.2, D2.3 |
| US-02 | C1.1, C1.2, C1.3, D4.1 |

### Should Have User Stories Coverage

| User Story | Covered By Tasks |
|------------|------------------|
| US-03 | A2.1, A6.1, D1.1, D2.4 |

### Functional Requirements Coverage

| FR | Covered By Tasks |
|----|------------------|
| FR-001 | A1.1 |
| FR-002 | A5.1, D2.2 |
| FR-003 | A5.2, D2.2 |
| FR-004 | A4.1, A4.2, D2.3 |
| FR-005 | A3.1, D1.2, D2.3 |
| FR-006 | A2.1, D1.1, D2.4 |
| FR-007 | B1.1 |
| FR-008 | B2.1, B3.1 |
| FR-009 | C1.1, C1.3, D4.1 |
| FR-010 | C1.2, D4.1 |
| FR-011 | A6.1 |
| FR-012 | D3.1 |

---

## Dependency Order

建议按以下顺序执行任务组：

1. **Group A** (Backend Foundation) — 必须先完成，为前端和测试提供 API 基础
2. **Group B** (Frontend Adaptation) — 依赖后端 API 已就绪
3. **Group C** (CLI Reset Password) — 可并行于 Group B，无强依赖
4. **Group D** (Testing & Regression) — 最后执行，验证全部功能

---

## Summary

- **Total tasks:** 21
- **Task groups:** 4
- **Must Have stories covered:** 2/2 (US-01, US-02)
- **Should Have stories covered:** 1/1 (US-03)
- **Functional requirements covered:** 12/12
