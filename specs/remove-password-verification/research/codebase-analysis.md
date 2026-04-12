# Codebase Analysis: 去除密码校验（本地个人部署模式）

> Generated: 2026-04-12 | Codebase: /home/myhql/code/PersonalKnowledgeAssistant

## Architecture Overview

本项目为基于 FastAPI 的单用户本地 AI 知识管理助手，采用前后端不分离的静态页面模式（SPA 路由由前端 `hashchange` 驱动，API 前缀为 `/api`）。

核心架构要点：

- **认证层**：JWT（python-jose）+ HTTPBearer + Argon2id 密码哈希。
- **主密钥（master_key）**：通过 `derive_master_key(password, salt)` 从用户密码和数据库 `system_config.salt` 派生 32 字节密钥，用于 AES-256-GCM 加密/解密附件文件。
- **主密钥缓存**：仅存在于 Python 进程内存的 `_master_key_cache: dict[str, bytes]`，以 JWT token 为键。服务重启后缓存清空，需重新登录才能解密文件。
- **数据层**：SQLite + aiotsqlite，数据库文件默认 `data/app.db`；向量检索由 `sqlite-vec` 虚拟表提供，全文检索由 FTS5 提供。
- **文件存储**：本地文件系统 `files/AB/CD/<item-id>/`，附件以 `.enc` 后缀加密存储。
- **部署脚本**：`deploy.py` 提供 `start/status/stop/restart` 及前台启动，纯 Python 标准库实现。

当前认证流程：
1. 首次访问 → `/api/system/status` 返回 `initialized: false` → 前端跳转 `#/init`
2. 初始化页面收集密码 → `POST /api/system/init` → 写入 `password_hash` 和 `salt`
3. 后续访问 → `#/login` → `POST /api/auth/login` → 校验 Argon2 哈希、派生 master_key、签发 JWT、缓存 master_key
4. 所有受保护路由通过 `get_current_user` 校验 Bearer Token，并检查 master_key 是否仍在缓存中
5. 上传附件时使用 `user.token` 取出缓存的 master_key 加密；下载时同理解密。

## Reusable Existing Code

| Component/Service | Location | How to Reuse |
|------------------|----------|--------------|
| Argon2id 密码工具 | `src/auth/crypto.py` | 保留 `hash_password/verify_password/derive_master_key`；无密码模式下不再调用 `derive_master_key`，但密码重置/初始化仍可复用 |
| JWT 签发与校验 | `src/auth/router.py` 和 `src/auth/dependencies.py` | `get_current_user` 中增加短路逻辑；`login` 增加可选密码分支 |
| 系统配置 CRUD | `src/system/service.py` | `load_config/update_config/reset_system` 可直接扩展新字段 |
| 数据库初始化 | `src/db/connection.py` | 新增 schema 版本无需改连接层，直接改 `schema.sql` |
| 部署脚本框架 | `deploy.py` | 增加子命令 `reset-password`，复用 `DeploymentConfig` 路径计算与进程管理 |
| 前端路由与存储 | `src/web/static/js/router.js`, `store.js`, `api.js` | `getToken()` 返回固定 no-auth token；路由守卫和 API 拦截器可复用 |

## Reference Implementations

| Feature | Location | Key Pattern |
|---------|----------|-------------|
| 登录并缓存 master_key | `src/auth/router.py` | `jwt.encode({"exp": ...}, secret) -> cache_master_key(token, master_key)` |
| 身份校验依赖 | `src/auth/dependencies.py` | `HTTPBearer(auto_error=False)` + `jwt.decode` + `get_cached_master_key(token)` |
| 系统初始化 | `src/system/router.py` (`/api/system/init`) | 检查 `initialized` 布尔标志，写入 `password_hash` + `salt` |
| 附件上传加密 | `src/knowledge/router.py` (`/api/knowledge/upload`) | `master_key = get_cached_master_key(user.token)` -> `encrypt_bytes(file_bytes, master_key)` |
| 附件下载解密 | `src/knowledge/router.py` (`/{item_id}/attachments/{attachment_id}/download`) | `decrypt_bytes(encrypted, master_key)` |
| 前端路由守卫 | `src/web/static/js/router.js` | `if (!route.public && !getToken()) redirect #/login` |
| 前端登录页 | `src/web/static/js/pages/login.js` | 提交 `apiPost('/auth/login', {password, remember_me})` |
| 前端初始化页 | `src/web/static/js/pages/init.js` | 提交 `apiPost('/system/init', {password})` |

## Integration Points

| Layer | Location | Change Type | Description |
|-------|----------|-------------|-------------|
| 数据库 Schema | `src/db/schema.sql` | ALTER / ADD | 在 `system_config` 表增加 `password_enabled INTEGER DEFAULT 1` |
| 后端配置模型 | `src/config.py` | ADD | 可选：增加 `NO_AUTH_MODE` 环境变量作为覆盖开关，用于纯命令行强制无密码场景 |
| 认证依赖 | `src/auth/dependencies.py` | MODIFY | `get_current_user`：检查 `password_enabled` 标志，若为 `0` 则自动生成/返回一个固定的 `CurrentUser("no-auth")`，无需 Bearer Header |
| 登录接口 | `src/auth/router.py` | MODIFY | `POST /api/auth/login`：若 `password_enabled == 0`，直接返回 token（可固定值），并将一个固定的 master_key（或从固定 secret 派生）写入缓存 |
| 初始化接口 | `src/system/router.py` (`/api/system/init`) | MODIFY | `InitRequest` 中 `password` 改为可选；增加可选字段 `password_enabled: bool = True`；当 `password_enabled=False` 时，只写 `initialized=1`、`password_enabled=0`，不写 `password_hash`/`salt` |
| 系统状态接口 | `src/system/router.py` (`/api/system/status`) | MODIFY | 返回增加 `password_enabled` 字段，供前端判断是否需要跳登录页 |
| 系统配置查看/修改 | `src/system/router.py` | MODIFY | 允许当前用户（含 no-auth）修改配置；需考虑是否允许在“已初始化”状态下从有密码切换为无密码 |
| 导出/导入/重置 | `src/system/router.py` + `src/system/service.py` | MODIFY | 无密码模式下，`export_backup`/`import_backup`/`reset_system` 不再需要用户输入 `password` 进行校验，或直接跳过密码校验 |
| 知识上传接口 | `src/knowledge/router.py` (`/api/knowledge/upload`) | MODIFY | 无密码模式下，仍需 master_key 加密文件。可使用一个静态/环境变量派生的 master_key |
| 知识下载接口 | `src/knowledge/router.py` (`/api/knowledge/{item_id}/attachments/{attachment_id}/download`) | MODIFY | 无密码模式下从缓存或配置获取静态 master_key 解密 |
| 前端路由 | `src/web/static/js/router.js` | MODIFY | `resolve()` 中：若 `password_enabled == false` 且 `getToken()` 为空，自动设置固定 token，不再跳转 `#/login` |
| 前端初始化页 | `src/web/static/js/pages/init.js` | MODIFY | 增加“是否启用密码保护”复选框；不启用时隐藏密码输入框 |
| 前端登录页 | `src/web/static/js/pages/login.js` | MODIFY | 若后端返回 `password_enabled == false`，前端可自动调用 `apiPost('/auth/login', {})` 并保存 token |
| 前端全局入口 | `src/web/static/js/app.js` | MODIFY | `DOMContentLoaded` 时读取 `password_enabled` 状态，据此决定是否强制 `#/init` 或自动完成 no-auth 登录 |
| 部署脚本 | `deploy.py` | ADD | 新增 `reset-password` 子命令：停止服务 → 清空数据目录 → 更新数据库 `initialized=0, password_hash=NULL` → 提示用户重新初始化 |

## Codebase Constraints

| Constraint | Source | Impact on Feature Design |
|------------|--------|--------------------------|
| master_key 必须存在才能加密/解密附件 | `src/knowledge/router.py`, `src/auth/crypto.py` | 即使无密码模式，也需要一个稳定的 master_key。建议：无密码时从固定环境变量 + 固定 salt 派生一个默认 master_key，或直接使用环境变量 `SECRET_KEY` 的 SHA-256 作为 master_key。否则已有加密文件将无法访问 |
| `_master_key_cache` 在进程内存，重启即失效 | `src/auth/crypto.py` | 无密码模式下可接受，因为每次启动后首次 API 调用会自动登录并重新填充缓存 |
| 单表单用户设计 (`system_config.id = 1`) | `src/db/schema.sql` | `password_enabled` 字段天然是全局开关，无需多租户考虑 |
| 前端使用 hash 路由 + localStorage/sessionStorage token | `src/web/static/js/router.js`, `store.js` | 无密码模式下 token 可写死（如 `"no-auth"`），前端存储层无需大改 |
| 导出/导入备份使用 master_key 加密 ZIP | `src/system/service.py` | 无密码模式下仍需 master_key；若用户后续从“有密码”切换为“无密码”，master_key 变化会导致旧备份无法解密。设计方案：切换模式时强制要求重新加密全部附件，或禁止切换 |
| 测试夹具 `auth_client` 假设必须 init + login | `tests/conftest.py` | 需要新增 `no_auth_client` 夹具，覆盖无密码模式的集成测试 |
| 附件存储路径可压缩为 `.gz` | `src/knowledge/archive.py` | 无密码模式下文件仍然加密，压缩逻辑不受影响 |

## Event / Message Patterns

| Event / Topic | Exact Identifier | Payload Interface | Source File | Notes |
|---------------|-----------------|-------------------|-------------|-------|
| N/A — no EDA patterns detected | | | | |

## Data Model Impact

1. **`system_config` 表变更**
   - 新增列：`password_enabled INTEGER NOT NULL DEFAULT 1 CHECK(password_enabled IN (0, 1))`
   - 保持 `password_hash` 和 `salt` 为 `NULLABLE`。
   - 当 `password_enabled = 0` 时，`password_hash` 和 `salt` 允许为 `NULL`。

2. **附件加密 master_key 来源变化**
   - 有密码：`derive_master_key(user_password, salt_from_db)`
   - 无密码：需要稳定的 key 来源。推荐方案：
     - `NO_AUTH_MASTER_KEY = hashlib.sha256(settings.secret_key.encode()).digest()`（32 bytes），保证同 `.env` 下每次启动一致。
     - 或者数据库中存一个 `no_auth_salt`，从空密码或固定字符串 + salt 派生。
   - 关键：确保即使无密码，用户删除 `.env` 或数据库后，旧加密文件会真正不可恢复——这在本地个人部署下是可接受的。

3. **模式切换风险**
   - 从“有密码”切到“无密码”：master_key 改变，旧附件无法解密。
   - 从“无密码”切到“有密码”：需要重新初始化/重新加密所有附件。
   - **建议**：初始化时选择一次，不支持运行时热切换；或在设置页提供“修改密码/重置加密”功能，实质是导出 → 清空 → 导入流程。

4. **重置密码功能的数据影响**
   - 部署脚本 `reset-password` 子命令需要：
     - `stop_service(config)`
     - 删除 `data/app.db` 或仅清空 `system_config` 及相关表
     - 删除 `files/` 目录（因为 master_key 将重置，旧加密文件无法解密）
     - 输出提示：数据已清空，请重新初始化系统。

## Technical Complexity

- **Overall:** 中等。核心难点不在于“去掉密码校验”本身，而在于 master_key 与附件加密的耦合关系：必须保证无密码模式下 stably 可解密。
- **New modules:** 0（全部在现有模块上修改）
- **Breaking change risk:** 中。若 `password_enabled` 默认值处理不当，会导致已有部署初始化状态异常。但 `DEFAULT 1` 可兼容旧数据（旧行视为启用密码）。
- **Estimated touch points:**
  - 后端：8~10 个文件（auth、system、knowledge routers + dependencies + crypto + schema + config）
  - 前端：4~6 个文件（router、store、api、pages/init/login/app.js）
  - 部署脚本：1 个文件（`deploy.py`）
  - 测试：2~3 个文件（新增 no-auth 模式集成测试）

## Current Tech Capabilities

- Python 3.11 + FastAPI 已具备条件路由和依赖注入，适合在 `get_current_user` 中做短路。
- `pydantic` 模型支持字段可选化（`password: str | None = None`），利于改 `InitRequest`。
- `sqlite-vec` 和 `aiosqlite` 不要求认证层改动，完全解耦。
- 前端基于原生 JS + Alpine.js + Tailwind，无构建步骤，改动直接生效。
- `deploy.py` 是纯 Python 标准库脚本，扩展子命令非常轻量。

## Implementation Guidance

1. **分阶段实施建议**
   - **阶段 A（后端 + 数据库）**：
     1. `schema.sql` 增加 `password_enabled`。
     2. `src/auth/dependencies.py` 增加 no-auth 短路：读取 `system_config.password_enabled`，为 0 时返回 `CurrentUser(token="no-auth")`。
     3. `src/auth/crypto.py` 增加 `get_no_auth_master_key()`：基于 `settings.secret_key` 派生固定 32 字节 key。
     4. `src/auth/router.py` 的 `login` 增加分支：若 `password_enabled == 0`，直接返回固定 token 并把固定 master_key 写入缓存。
     5. `src/system/router.py` 的 `init` 支持 `password` 可选、`password_enabled` 可选；`status` 返回 `password_enabled`。
     6. `src/system/service.py` 的 `export_backup` / `import_backup` / `reset_system` 兼容无密码场景（跳过密码校验）。
   - **阶段 B（前端）**：
     1. `init.js` 增加复选框和条件密码输入。
     2. `app.js` 检测 `password_enabled == false` 时自动完成 no-auth 登录（写死 token）。
     3. `router.js` 在 `password_enabled == false` 时不再强制跳转 `#/login`。
     4. `login.js` 可保留，用于有密码模式；无密码模式下用户不会到达此页（由 `app.js` 自动处理）。
   - **阶段 C（部署脚本）**：
     1. `deploy.py` 增加 `reset-password` 子命令。
     2. 实现交互式二次确认（`input()`），然后调用 `stop_service`、删除数据库和文件目录、输出成功信息。
   - **阶段 D（测试）**：
     1. `conftest.py` 新增 `no_auth_client` fixture：init 时 `password_enabled=False`，不提交密码。
     2. 补充无密码模式下的 knowledge CRUD、附件上传下载测试。

2. **关于 master_key 的关键设计决策**
   - 推荐：无密码模式下固定 master_key = `hashlib.sha256(settings.secret_key.encode()).digest()`。
   - 这样无需新增数据库存储，也不会暴露 master_key 到环境变量明文。
   - 若用户换 `SECRET_KEY`，旧附件无法解密——等同于“丢失密码”，在个人本地部署语义下合理。

3. **需额外注意的安全边界**
   - 无密码模式下 `/api/system/export` 不再需要密码，但备份 ZIP 仍用固定 master_key 加密。若用户把备份文件分享给他人，接收方只要知道 `SECRET_KEY` 即可解密。应在 UI 提示“无密码模式下备份文件的加密强度依赖于 SECRET_KEY，请勿共享”。

4. **测试覆盖 checklist**
   - [ ] 无密码 init 成功，status 返回 `password_enabled: false`
   - [ ] 无密码模式下 `/api/auth/login` 无需密码返回 token
   - [ ] 无密码模式下不带 Authorization Header 可访问 `/api/system/config`
   - [ ] 无密码模式下附件上传/下载正常
   - [ ] 有密码模式现有测试全部通过（回归）
   - [ ] `deploy.py reset-password` 流程单元测试（模拟输入 + 文件断言）
