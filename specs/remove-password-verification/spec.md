# Spec: 去除密码校验（本地个人部署模式）

> **Product Forge Feature** | Generated: 2026-04-12
> Feature slug: `remove-password-verification` | SpecKit mode: classic
>
> **Source artifacts:**
> - Product Spec: [product-spec/README.md](./product-spec/README.md)
> - Research: [research/README.md](./research/README.md)
> - Review log: [review.md](./review.md)

---

## Overview

### What We're Building

为本地个人部署的 AI 知识助手提供可选的密码保护模式：首次启动时可选择「无需密码，直接访问」，启用后跳过所有登录校验；同时通过 CLI 脚本提供安全的「重置密码」能力，在二次确认后清空数据并恢复初始化状态。

### Why We're Building It

个人用户在本地（个人电脑、NAS、家庭服务器）自托管 AI 知识助手时，每次访问都需要输入密码登录。由于用户通常是系统的唯一使用者，这种强制密码校验变成了不必要的操作负担。此外，一旦忘记密码，没有官方恢复入口，普通用户往往束手无策。

### Research Backing

This spec is backed by a full research phase covering:
- **Competitor analysis:** 本地工具在认证策略上两极分化。Ollama/Jupyter 默认无密码；Immich/Vaultwarden 认证不可妥协。知识管理/内容管理类工具（如 Memos、Nextcloud）普遍强制密码，存在明显空白。
- **UX/UI patterns:** 最佳实践是首次启动向导中明确选择「启用密码保护」或「无需密码直接访问」；CLI 重置使用强二次确认（如输入 `RESET`）；Web 端不放置无效的「忘记密码」链接。
- **Codebase analysis:** 当前系统的 `master_key` 由密码派生，用于 AES-256-GCM 附件加密。无密码模式下需要一个稳定的替代 `master_key` 来源（推荐基于 `SECRET_KEY` 的 SHA-256 派生），否则现有加密机制将失效。

> Deep-dive: [research/README.md](./research/README.md)

---

## Prerequisites

| Priority | Feature | Status | Relationship | What's Needed |
|----------|---------|--------|--------------|---------------|
| P1 | 001-ai-knowledge-assistant | ✅ done | complements | 核心后端系统（FastAPI + SQLite + 加密附件）已完整实现，本 feature 在其上扩展可选密码 |
| P2 | 002-one-click-deployment | ✅ done | complements | 部署脚本 `deploy.py` 已提供 start/status/stop/restart，本 feature 需在其上增加 `reset-password` 子命令 |

---

## Goals

### Primary Goal

个人用户在本地首次部署时，能够无 friction 地进入应用主界面，无需强制输入密码。

### Secondary Goals

1. 保留可选的密码保护能力，供有多人设备或公开网络需求的用户选择。
2. 提供官方 CLI 密码重置入口，解决用户忘记密码后的恢复问题。
3. 确保无密码模式下附件加密/解密机制仍然正常工作，数据不以明文存储。

### Non-Goals (v1 scope)

1. 运行时热切换「有密码 / 无密码」— v1 不支持在设置中动态切换。
2. 多用户支持 — 仍针对单用户本地部署。
3. Web 端「忘记密码」链接 / 邮件找回。
4. 远程访问或公网部署的特殊处理。
5. 细粒度网络白名单（如 Home Assistant 的 trusted_networks）。
6. 为无密码模式单独设计一套 UI 皮肤或主题。

---

## Users

### Primary Persona

**李明** — 个人知识管理爱好者 / 独立开发者
- **场景：** 在自己的笔记本电脑或家庭 NAS 上部署 AI 知识助手
- **Key need:** 打开浏览器就能立即使用工具，不被登录流程打断；万一忘记密码也能通过简单方式恢复

---

## User Stories

> Full user journey flows: [product-spec/user-journey.md](./product-spec/user-journey.md)

### Must Have (MVP)

- [ ] **US-01** 作为本地部署的个人用户，我希望在首次初始化时可以选择"无需密码，直接访问"，以便减少每次使用时的 friction。
  - **AC-01:** Web 初始化向导提供「启用密码保护」和「无需密码，直接访问」两个单选选项。
  - **AC-02:** 选择「无需密码」后，系统完成初始化，后续访问不再要求登录。
  - **AC-03:** 选择「启用密码保护」后，系统保持现有行为，要求输入密码并完成初始化。
  - **Wireframe ref:** [初始化向导](./product-spec/wireframes.md#screen-1-初始化向导)

- [ ] **US-02** 作为已经启用了密码保护的用户，我希望能够通过启动脚本重置密码并清空数据，以便在忘记密码时能够重新获得访问权限。
  - **AC-01:** 启动脚本（`deploy.py`）提供 `reset-password` 子命令。
  - **AC-02:** 触发后脚本显示红色高亮警告，列出将被删除的数据/文件路径。
  - **AC-03:** 用户必须输入大写 `RESET` 进行二次确认，确认后才执行删除和重置。
  - **AC-04:** 重置完成后，系统回到未初始化状态，用户可重新设置密码或选择无密码模式。
  - **Wireframe ref:** [CLI 重置交互](./product-spec/wireframes.md#cli-wireframe-reset-password-终端交互)

### Should Have

- [ ] **US-03** 作为无密码模式下的用户，我希望系统仍能正常加密和解密附件文件，以便数据不因关闭密码保护而裸奔。
  - **AC-01:** 无密码模式下，系统使用稳定来源的 `master_key` 继续执行 AES-256-GCM 加密/解密。
  - **AC-02:** 附件上传、下载、备份导出/导入在无密码模式下均能正常工作。

### Could Have (Future)

- [ ] **US-04** 作为用户，我希望在无密码模式下仍能在设置页中「开启密码保护」，以便后续需要时增强安全性。（*注：由于 master_key 变更会导致历史附件无法解密，v1 暂不支持运行时切换*）

---

## Functional Requirements

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-001 | 数据库 `system_config` 表支持 `password_enabled` 标志，默认 `1` | Must | US-01 |
| FR-002 | `/api/system/init` 支持可选密码和 `password_enabled` 参数 | Must | US-01 |
| FR-003 | `/api/system/status` 返回 `password_enabled` 字段 | Must | US-01 |
| FR-004 | `/api/auth/login` 在 `password_enabled=False` 时允许空密码登录并返回固定 token | Must | US-01 |
| FR-005 | `get_current_user` 在 `password_enabled=False` 时短路放行 | Must | US-01 |
| FR-006 | 无密码模式下使用 `SHA256(SECRET_KEY)` 作为稳定 master_key | Must | US-03 |
| FR-007 | 前端初始化页支持「启用密码」/「无需密码」单选，默认「无需密码」 | Must | US-01 |
| FR-008 | 前端在无密码模式下自动获取 token 并跳过登录页 | Must | US-01 |
| FR-009 | 启动脚本提供 `reset-password` 子命令 | Must | US-02 |
| FR-010 | `reset-password` 要求输入 `RESET` 二次确认 | Must | US-02 |
| FR-011 | 无密码模式下导出/导入备份跳过密码校验 | Should | US-03 |
| FR-012 | 所有现有集成测试在无密码新增后仍通过 | Must | 回归保护 |

---

## Non-Functional Requirements

| Category | Requirement | Source |
|----------|-------------|--------|
| Performance | 认证状态判断 `< 100ms`；无密码模式下首屏加载与有密码模式无差异 | research/codebase-analysis |
| Accessibility | 初始化向导表单有清晰的 `<label>` 关联；错误提示不仅依赖颜色 | research/ux-patterns |
| Security | 无密码模式不泄露 master_key；`reset-password` 的二次确认不可绕过；固定 token 仅用于本地单用户场景 | product-spec |
| Compatibility | 不对现有已初始化数据库产生破坏性变更；旧用户默认仍为有密码模式 | product-spec |
| Maintainability | 改动集中在 `auth/`、`system/`、`knowledge/` 路由和前端 `pages/init.js`、`app.js`、`router.js` | research/codebase-analysis |

## NFR Measurement Contract

> Every NFR must have a corresponding measurable signal. Without this, the NFR cannot be verified.

| NFR | How to Measure | Signal / Query | Threshold |
|-----|----------------|----------------|-----------|
| 认证状态判断 `< 100ms` | `/api/system/status` 响应时间 | 本地测试直接读取 SQLite，P95 响应时间 | ≤ 100ms |
| 无密码模式首屏加载无差异 | `window.performance.timing` 或 Lighthouse | 有密码 vs 无密码模式的 `DOMContentLoaded` 时间差 | ≤ 200ms |
| 旧数据库兼容性 | 回归测试 | 运行所有现有集成测试 | 100% 通过 |
| 前端错误提示可访问性 | 手动检查 + axe-core | 所有错误状态具备文本说明且颜色对比度 ≥ 4.5:1 | 0 违规 |

---

## Technical Context

> Detailed analysis: [research/codebase-analysis.md](./research/codebase-analysis.md)

### Integration Points

| Layer | Location | Change Type | Description |
|-------|----------|-------------|-------------|
| DB Schema | `src/db/schema.sql` | ALTER | `system_config` 增加 `password_enabled INTEGER DEFAULT 1` |
| Auth Dependency | `src/auth/dependencies.py` | MODIFY | `get_current_user` 检查 `password_enabled`，为 `0` 时返回固定 `CurrentUser` |
| Login API | `src/auth/router.py` | MODIFY | 无密码时直接返回固定 token 并把固定 master_key 写入缓存 |
| Init API | `src/system/router.py` | MODIFY | `InitRequest` 增加可选 `password_enabled`，`password` 改为可选 |
| Status API | `src/system/router.py` | MODIFY | 返回增加 `password_enabled` |
| Knowledge Upload | `src/knowledge/router.py` | MODIFY | 无密码模式下使用固定 master_key 加密 |
| Knowledge Download | `src/knowledge/router.py` | MODIFY | 无密码模式下使用固定 master_key 解密 |
| Frontend Router | `src/web/static/js/router.js` | MODIFY | `password_enabled == false` 时不再跳转 `#/login` |
| Frontend Init | `src/web/static/js/pages/init.js` | MODIFY | 增加单选和条件密码输入 |
| Frontend App Entry | `src/web/static/js/app.js` | MODIFY | 自动完成 no-auth 登录 |
| Deploy Script | `deploy.py` | ADD | `reset-password` 子命令 |

### Reusable Components

| Component | Location | How to Reuse |
|-----------|----------|--------------|
| Argon2id password tools | `src/auth/crypto.py` | 保留 `hash_password` / `verify_password` / `derive_master_key` |
| JWT encode/decode | `src/auth/router.py`, `dependencies.py` | 复用现有 JWT 逻辑，仅增加短路分支 |
| System config CRUD | `src/system/service.py` | 直接扩展读取/更新 `password_enabled` |
| Deploy script framework | `deploy.py` | 增加子命令，复用 `DeploymentConfig` 路径计算 |

### New Modules Required

无新增独立模块；全部在现有模块上扩展。

### Data Model Impact

1. `system_config` 表新增 `password_enabled INTEGER NOT NULL DEFAULT 1 CHECK(password_enabled IN (0, 1))`
2. `password_hash` 和 `salt` 在 `password_enabled = 0` 时允许为 `NULL`
3. 无密码模式下固定 master_key 来源于 `SHA256(settings.secret_key)`，无需新增 DB 列

### Codebase Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| master_key 必须存在才能加密/解密附件 | `src/knowledge/router.py`, `src/auth/crypto.py` | 无密码时必须提供稳定的替代 master_key |
| `_master_key_cache` 在进程内存，重启即失效 | `src/auth/crypto.py` | 无密码模式下可接受，每次启动后自动重新填充 |
| 单表单用户设计 (`system_config.id = 1`) | `src/db/schema.sql` | `password_enabled` 天然是全局开关 |
| 前端 hash 路由 + localStorage token | `src/web/static/js/router.js` | 无密码模式下 token 可写死为 `"no-auth"` |

---

## Acceptance Criteria

Each user story's AC is listed above. Additionally, the feature is considered complete when:

1. All Must Have user stories are implemented and tested
2. All wireframes match the implemented UI within acceptable deviation
3. Performance NFRs are met as measured by local API response time and Lighthouse
4. Accessibility requirements pass manual inspection (label association, color contrast, keyboard navigation)
5. Existing integration tests 100% pass without regression
6. New no-auth mode integration tests cover init, login bypass, protected route access, and attachment encryption/decryption

---

## Success Metrics

Primary KPI: 个人部署用户首次初始化完成率（选择无密码或有密码后成功进入主界面的比例）— Target: ≥ 95%

Secondary KPIs:
- 用户因密码问题在 GitHub/issue 中投诉的频率 — Target: 降至 0（本 feature 发布后不再新增相关投诉）
- 首次打开浏览器到主界面的时间（无密码模式）— Target: ≤ 5 秒

---

## Testing Specification

### Coverage Targets

| Module / Service | Target Coverage | Test Type |
|-----------------|----------------|-----------|
| `src/auth/` | ≥ 80% | unit / integration |
| `src/system/router.py` | ≥ 80% | integration |
| `src/knowledge/router.py` (attachment paths) | ≥ 80% | integration |
| `deploy.py` | ≥ 60% | unit (mock) |

### Critical Test Cases

| # | Scenario | Input | Expected Output | Type |
|---|----------|-------|----------------|------|
| TC-001 | 无密码模式初始化成功 | `POST /api/system/init` with `password_enabled: false` | `initialized: true`, `password_enabled: false` | integration |
| TC-002 | 无密码模式下访问受保护路由 | `GET /api/system/config` without `Authorization` header | 200 OK | integration |
| TC-003 | 无密码模式下附件上传加密正常 | Upload file with `password_enabled: false` | File saved as `.enc`, decryptable via download | integration |
| TC-004 | 旧数据默认启用密码 | Query existing `system_config` row after schema migration | `password_enabled: 1` | unit |
| TC-005 | CLI 重置二次确认失败 | Input `no` to `reset-password` prompt | No files deleted, exit code 0 | unit (mock) |

### E2E Scenarios

| TC-ID | Scenario | Entry Point | Exit Condition |
|-------|----------|------------|----------------|
| TC-E2E-001 | 首次部署选择无密码并上传附件 | 未初始化状态 → 选择「无需密码」→ 进入主界面 → 上传附件 → 下载附件 | 全程无需密码，附件可正常解密 |
| TC-E2E-002 | 启用密码后忘记密码，通过 CLI 重置恢复 | 已启用密码但忘记密码 → 运行 `reset-password` → 输入 `RESET` → 重新初始化 | 数据库和文件清空，可重新配置 |

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| master_key 变更导致历史附件无法解密（若未来支持热切换） | High | v1 禁止运行时切换；未来若支持需设计全量重新加密流程 |
| 固定 no-auth token 被本地恶意脚本利用 | Low | 本地单用户场景下可接受；不面向公网部署 |
| 用户误触 `reset-password` 导致数据丢失 | High | 强制输入 `RESET` 二次确认 + 红色高亮警告 + 列出将被删除的文件路径 |
| 旧数据库迁移时 `password_enabled` 默认值异常 | Medium | 默认值为 `1`（启用密码），与旧行为完全一致 |
| 前端在无密码模式下仍闪现登录页 | Low | 在应用初始化 loading 阶段完成状态判断，确定后再渲染首屏 |

---

## Wireframes Reference

> Visual wireframes: [product-spec/wireframes.md](./product-spec/wireframes.md)

Key screens:
- **初始化向导:** 单选卡片（默认「无需密码」）+ 条件密码输入框
- **登录页:** 极简密码输入，底部提示 CLI 重置命令
- **应用加载状态:** 居中 spinner，后台判断认证状态后跳转，避免登录页闪现

---

## Open Questions

1. 当前 Web 前端具体使用什么技术栈？`router.js`、`store.js` 的具体实现在哪几个文件？
2. 当前是否有现成的「系统设置」页面？安全相关配置的 UI 分组名称是什么？
3. `deploy.py` 之外，是否还有 `start.sh`、`docker-compose.yml` 等其他部署入口需同步支持 `reset-password`？
4. 无密码模式下，Pydantic `LoginRequest` 模型是否允许空对象 `{}`？是否需将 `password` 设为可选？
