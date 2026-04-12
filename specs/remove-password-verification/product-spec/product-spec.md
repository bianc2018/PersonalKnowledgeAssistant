# Product Spec: 去除密码校验（本地个人部署模式）

> Status: DRAFT | Version: 1.0 | Date: 2026-04-12
> Feature: `remove-password-verification` | Size: Medium
>
> **Related documents:** [User Journey](./user-journey.md) | [Wireframes](./wireframes.md) | [Research →](../research/README.md)

## 1. Overview

### Problem Statement

个人用户在本地（个人电脑、NAS、家庭服务器）自托管 AI 知识助手时，每次访问都需要输入密码登录。由于用户通常是系统的唯一使用者，这种强制密码校验变成了不必要的操作负担。此外，一旦忘记密码，没有官方恢复入口，普通用户往往束手无策。

### Solution Summary

为本地个人部署场景提供可选的密码保护模式：
1. **首次启动时可选择是否启用密码**（不启用则跳过所有密码校验，默认开放访问）
2. **启用密码时保留现有 JWT + Argon2 校验逻辑**
3. **启动脚本增加"重置密码"选项**，经用户二次确认后清理当前数据并重置密码（无需旧密码验证）

### Background & Research

Key findings from research phase:
- **Competitors:** 本地工具在认证策略上两极分化。Ollama/Jupyter 默认无密码；Immich/Vaultwarden 认证不可妥协。知识管理/内容管理类工具（如 Memos、Nextcloud）普遍强制密码，存在明显空白。
- **UX/UI:** 最佳实践是首次启动向导中明确选择「启用密码保护」或「无需密码直接访问」；CLI 重置使用强二次确认（如输入 `RESET`）；Web 端不放置无效的「忘记密码」链接。
- **Technical:** 当前系统的 `master_key` 由密码派生，用于 AES-256-GCM 附件加密。无密码模式下需要一个稳定的替代 master_key 来源（推荐基于 `SECRET_KEY` 派生），否则现有加密机制将失效。

> Full research available in [research/README.md](../research/README.md)

---

## 2. Users & Personas

### Primary Persona

**姓名：** 李明  
**角色：** 个人知识管理爱好者 / 独立开发者  
**场景：** 在自己的笔记本电脑或家庭 NAS 上部署 AI 知识助手，用于管理个人笔记、研究资料和灵感  
**目标：** 打开浏览器就能立即使用工具，不被登录流程打断；万一忘记密码也能通过简单方式恢复  
**痛点：**
- 每次打开 `localhost` 都要先输入密码，感觉自己"在防自己"
- 曾经忘记密码，不得不上网查如何删除 SQLite 数据库文件
- 对比 Obsidian、Ollama 等本地工具，自己的知识助手"不够顺"

---

## 3. User Stories

### Must Have (MVP)

- [ ] **US-01** 作为本地部署的个人用户，我希望在首次初始化时可以选择"无需密码，直接访问"，以便减少每次使用时的 friction。  
  **AC-01:** Web 初始化向导提供「启用密码保护」和「无需密码，直接访问」两个单选选项。  
  **AC-02:** 选择「无需密码」后，系统完成初始化，后续访问不再要求登录。  
  **AC-03:** 选择「启用密码保护」后，系统保持现有行为，要求输入密码并完成初始化。

- [ ] **US-02** 作为已经启用了密码保护的用户，我希望能够通过启动脚本重置密码并清空数据，以便在忘记密码时能够重新获得访问权限。  
  **AC-01:** 启动脚本（如 `deploy.py` 或等效脚本）提供 `reset-password` 子命令。  
  **AC-02:** 触发后脚本显示红色高亮警告，列出将被删除的数据/文件路径。  
  **AC-03:** 用户必须输入大写 `RESET` 进行二次确认，确认后才执行删除和重置。  
  **AC-04:** 重置完成后，系统回到未初始化状态，用户可重新设置密码或选择无密码模式。

### Should Have

- [ ] **US-03** 作为无密码模式下的用户，我希望系统仍能正常加密和解密附件文件，以便数据不因关闭密码保护而裸奔。  
  **AC-01:** 无密码模式下，系统使用稳定来源的 master_key 继续执行 AES-256-GCM 加密/解密。  
  **AC-02:** 附件上传、下载、备份导出/导入在无密码模式下均能正常工作。

### Could Have (Future)

- [ ] **US-04** 作为用户，我希望在无密码模式下仍能在设置页中「开启密码保护」，以便后续需要时增强安全性。（*注：由于 master_key 变更会导致历史附件无法解密，v1 暂不支持运行时切换*）

---

## 4. Feature Breakdown

### 4.1 后端：可选密码认证模式

**描述：** 在数据库层引入 `password_enabled` 标志，改造认证依赖和登录/初始化接口以支持无密码模式。

**关键交互：**
- `system_config` 表新增 `password_enabled INTEGER DEFAULT 1`
- `GET /api/system/status` 返回增加 `password_enabled` 字段
- `POST /api/system/init` 的 `password` 字段改为可选，新增 `password_enabled` 参数
- `POST /api/auth/login` 在 `password_enabled == false` 时直接返回固定 token
- `get_current_user` 依赖在 `password_enabled == false` 时短路，返回固定 `CurrentUser`

**边界情况：**
- 旧数据库（无 `password_enabled` 列）兼容：默认值 `1`，视为启用密码
- 无密码模式下不带 `Authorization` 的请求需正常放行
- 无密码模式下导出/导入备份不再要求输入密码进行校验

### 4.2 后端：无密码模式下的稳定 master_key

**描述：** 即使不启用密码，附件加密/解密仍需 master_key。无密码模式下使用基于 `SECRET_KEY` 派生的固定 master_key。

**关键交互：**
- 新增 `get_no_auth_master_key()` 函数，基于 `SHA256(settings.secret_key)` 生成 32 字节 key
- `login` 在无密码模式下将固定 master_key 写入缓存
- 上传/下载附件时，`get_cached_master_key` 在无密码模式下返回固定 master_key

**边界情况：**
- 若用户修改 `.env` 中的 `SECRET_KEY`，旧附件将无法解密——与个人本地部署下"丢失密码"语义一致

### 4.3 前端：初始化向导支持选择

**描述：** Web 初始化页面增加「是否启用密码保护」的单选，并根据选择条件展示密码输入框。

**关键交互：**
- 页面加载后默认选中「无需密码，直接访问」
- 选中「启用密码保护」时，显示密码输入框和确认密码输入框
- 提交时根据选项携带 `password_enabled` 和可选的 `password`

**边界情况：**
- 密码输入框需做前端校验（两次一致、非空）

### 4.4 前端：无密码模式下的自动登录

**描述：** 前端启动时检测 `password_enabled`，若为 false 则自动写入固定 token 并进入主界面，不再跳转登录页。

**关键交互：**
- 应用启动时调用 `/api/system/status` 和 `/api/auth/status`（或等效接口）获取认证状态
- `password_enabled == false` 时自动调用 `/api/auth/login`（可空参数）获取 token 并跳入主界面
- 路由守卫在有固定 token 后不再拦截

**边界情况：**
- 避免登录页先闪现再跳转：应在 loading/skeleton 期间完成判断

### 4.5 CLI：启动脚本重置密码

**描述：** 在现有部署脚本中增加 `reset-password` 子命令，提供交互式数据清空和密码重置能力。

**关键交互：**
- 命令入口：`python deploy.py reset-password`
- 输出红色警告："此操作将永久删除所有本地数据，包括数据库和附件文件。"
- 列出将被删除的具体路径（如 `data/app.db`、`files/`）
- 要求用户输入 `RESET` 确认（不区分大小写或强制大写均可）
- 确认后：停止服务 → 删除数据库和附件目录 → 输出成功信息

**边界情况：**
- 用户输入非 `RESET` 时取消操作，不做任何修改
- 服务未运行时直接执行删除并提示

---

## 5. Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-001 | 数据库 `system_config` 表支持 `password_enabled` 标志 | Must | 默认 `1`，兼容旧数据 |
| FR-002 | `/api/system/init` 支持可选密码和 `password_enabled` 参数 | Must | `password_enabled=False` 时可省略 `password` |
| FR-003 | `/api/system/status` 返回 `password_enabled` | Must | 供前端判断认证状态 |
| FR-004 | `/api/auth/login` 在 `password_enabled=False` 时允许空密码登录 | Must | 返回固定 token |
| FR-005 | `get_current_user` 在 `password_enabled=False` 时短路放行 | Must | 返回固定 `CurrentUser` |
| FR-006 | 无密码模式下使用 `SHA256(SECRET_KEY)` 作为稳定 master_key | Must | 保证附件加解密正常工作 |
| FR-007 | 前端初始化页支持「启用密码」/「无需密码」单选 | Must | 默认选中「无需密码」 |
| FR-008 | 前端在无密码模式下自动获取 token 并跳过登录页 | Must | 避免登录页闪现 |
| FR-009 | 启动脚本提供 `reset-password` 子命令 | Must | 需停止服务并清空数据 |
| FR-010 | `reset-password` 要求输入 `RESET` 二次确认 | Must | 防止误触 |
| FR-011 | 无密码模式下导出/导入备份跳过密码校验 | Should | 与正常模式体验一致 |
| FR-012 | 所有现有集成测试在无密码新增后仍通过 | Must | 回归保护 |

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | 认证状态判断 `< 100ms`；无密码模式下首屏加载与有密码模式无差异 |
| Accessibility | 初始化向导表单有清晰的 `<label>` 关联；错误提示不仅依赖颜色 |
| Security | 无密码模式不泄露 master_key；`reset-password` 的二次确认不可绕过；固定 token 和 master_key 仅用于本地单用户场景 |
| Compatibility | 不对现有已初始化数据库产生破坏性变更；旧用户默认仍为有密码模式 |
| Maintainability | 改动集中在 `auth/`、`system/`、`knowledge/` 路由和前端 `pages/init.js`、`app.js`、`router.js` |

---

## 7. Out of Scope (v1)

以下功能明确不在 v1 范围内：

1. **运行时热切换「有密码 / 无密码」** — 由于 master_key 变更会导致历史附件无法解密，v1 不支持在设置中动态切换。
2. **多用户支持** — 本功能仍针对单用户本地部署，不引入用户管理体系。
3. **Web 端「忘记密码」链接 / 邮件找回** — 个人本地部署无邮件服务器，密码重置统一通过 CLI 脚本完成。
4. **远程访问或公网部署的特殊处理** — 默认假设为 localhost / 内网单用户场景。
5. **细粒度网络白名单（如 Home Assistant 的 trusted_networks）** — v1 不做 IP 段级别的认证绕过。
6. **为无密码模式单独设计一套 UI 皮肤或主题** — 复用现有 UI，仅在初始化页和登录逻辑上改动。

---

## 8. Success Criteria

1. **功能完整：** 个人用户首次部署时，可在初始化向导中选择「无需密码，直接访问」，选择后后续打开浏览器不再要求登录。
2. **数据安全：** 无密码模式下，附件上传、下载、备份导出/导入仍能正常加密/解密，数据不以明文裸奔。
3. **恢复可用：** 用户可运行启动脚本 `reset-password`，在二次确认后清空数据并重置为未初始化状态。
4. **向后兼容：** 现有已启用密码的部署不受任何影响，默认行为保持不变。
5. **测试覆盖：** 新增无密码模式的集成测试，且所有原有测试 100% 通过。

---

## 9. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| master_key 变更导致历史附件无法解密（若未来支持热切换） | 不适用（v1 已排除热切换） | High | v1 禁止运行时切换；未来若支持需设计全量重新加密流程 |
| 固定 no-auth token 在理论上存在被本地恶意脚本利用的风险 | Low | Low | 本地单用户场景下该风险可接受；不面向公网部署 |
| 用户误触 `reset-password` 导致数据丢失 | Low | High | 强制输入 `RESET` 二次确认 + 红色高亮警告 + 列出将被删除的文件路径 |
| 旧数据库迁移时 `password_enabled` 默认值异常导致认证失效 | Low | Medium | 默认值设为 `1`（启用密码），与旧行为完全一致 |
| 前端在无密码模式下仍闪现登录页 | Medium | Low | 在应用初始化 loading 阶段完成状态判断，确定后再渲染首屏 |

---

## 10. Open Questions

1. 当前 Web 前端具体使用什么技术栈？（原生 JS + Alpine.js？Vue？）`router.js`、`store.js` 的具体实现在哪几个文件？
2. 当前是否有现成的「系统设置」页面？如果有，安全相关配置的 UI 分组名称是什么？
3. `deploy.py` 之外，项目是否还有 `start.sh`、`docker-compose.yml` 等其他部署入口需要同步支持 `reset-password`？
4. 无密码模式下，调用 `/api/auth/login` 时请求体传空对象 `{}` 是否会被 Pydantic 模型拒绝？是否需要在模型层将 `password` 设为可选？

---

## 11. Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| 默认提供「无需密码」选项 | Ollama、Jupyter 等本地个人工具的主流做法，可显著降低首次部署 friction | 2026-04-12 |
| 无密码模式下使用 `SHA256(SECRET_KEY)` 作为固定 master_key | 无需新增数据库存储，保证附件加密连续工作，且与个人本地部署边界一致 | 2026-04-12 |
| v1 不支持运行时热切换「有/无密码」 | master_key 变更会导致已加密附件无法解密，实现热切换需全量重新加密，复杂度超出 v1 范围 | 2026-04-12 |
| 密码重置走 CLI 脚本而非 Web 页面 | 本地个人部署无邮件服务器，CLI 是最直接、最安全的恢复路径 | 2026-04-12 |
| `reset-password` 要求输入 `RESET` 而非简单的 `y/n` | 防止用户由于惯性按回车键误触 destructive action | 2026-04-12 |
