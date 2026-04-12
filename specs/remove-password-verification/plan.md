# Technical Plan: 去除密码校验（本地个人部署模式）

> Feature: `remove-password-verification` | SpecKit Mode: classic
> Created: 2026-04-12 | Based on: [spec.md](./spec.md)

---

## 1. Goals & Scope

### Primary Goal
为本地个人部署用户移除强制密码校验的 friction，同时保留可选的安全增强路径。

### What This Plan Covers
- 后端认证层改造（`password_enabled` 标志、无密码短路、固定 master_key）
- 前端初始化向导和自动登录逻辑
- 部署脚本 `reset-password` 子命令
- 全量回归测试 + 无密码模式新增测试

### Out of Scope (v1)
- 运行时热切换「有/无密码」
- 多用户体系
- Web 端密码找回
- 公网/远程访问特殊策略

---

## 2. Architecture Design

### 2.1 Auth Flow — Password Enabled (Existing, Preserved)

```
Browser → GET /api/system/status
          ← { initialized: true, password_enabled: true }
Browser → #/login
User → POST /api/auth/login { password }
Backend → Argon2 verify → derive master_key → JWT encode
        → cache_master_key(token, master_key)
          ← { token, expires_in }
Browser → use token for all subsequent requests
```

### 2.2 Auth Flow — Password Disabled (New)

```
Browser → GET /api/system/status
          ← { initialized: true, password_enabled: false }
Browser → POST /api/auth/login {}   (auto-triggered by frontend)
Backend → detect password_enabled == false
        → return fixed token "no-auth"
        → cache_master_key("no-auth", get_no_auth_master_key())
          ← { token: "no-auth", expires_in: 31536000 }
Browser → use fixed token for all subsequent requests
```

### 2.3 No-Auth Master Key Derivation

```python
import hashlib
from src.config import get_settings

def get_no_auth_master_key() -> bytes:
    settings = get_settings()
    return hashlib.sha256(settings.secret_key.encode()).digest()  # 32 bytes
```

**Rationale:**
- 不需要新增数据库列来存储 no-auth key
- 同 `.env` 下每次启动结果一致，保证附件可解密
- 如果用户更换 `SECRET_KEY`，旧附件不可解密——这在个人本地部署语义下等同于"丢失密码"

### 2.4 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (SPA)                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ init.js     │  │ login.js    │  │ app.js / router.js  │ │
│  │ (wizard)    │  │ (password)  │  │ (auth state guard)  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼────────────────────┼────────────┘
          │                │                    │
          └────────────────┴────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  FastAPI    │
                    │  /api/*     │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐        ┌────▼────┐       ┌────▼────┐
   │ auth/   │        │ system/ │       │ knowledge│
   │ router  │        │ router  │       │ router   │
   │ deps    │        │ service │       │ (upload/ │
   │ crypto  │        │         │       │ download)│
   └────┬────┘        └────┬────┘       └────┬─────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │  SQLite     │
                    │  aiosqlite  │
                    └─────────────┘
```

---

## 3. Data Model Changes

### 3.1 Schema Migration

**File:** `src/db/schema.sql`

```sql
-- Add to system_config table definition
password_enabled INTEGER NOT NULL DEFAULT 1 CHECK(password_enabled IN (0, 1))
```

**Compatibility:**
- 现有已初始化数据库的行会自动获得 `password_enabled = 1`
- `password_hash` 和 `salt` 在 `password_enabled = 0` 时允许为 `NULL`

### 3.2 Runtime Access Pattern

```python
# Pseudo-code for config access
async def is_password_enabled(db) -> bool:
    async with db.execute(
        "SELECT password_enabled FROM system_config WHERE id = 1"
    ) as cursor:
        row = await cursor.fetchone()
        return bool(row[0]) if row else True
```

---

## 4. API Changes

### 4.1 `POST /api/system/init`

**Current Request Model:**
```python
class InitRequest(BaseModel):
    password: str
```

**New Request Model:**
```python
class InitRequest(BaseModel):
    password: str | None = None
    password_enabled: bool = False
```

**Validation Logic:**
```python
if body.password_enabled and not body.password:
    raise HTTPException(400, "Password is required when password protection is enabled")
if not body.password_enabled:
    body.password = None  # ensure no password hash is stored
```

**Storage Logic:**
- `password_enabled = 1` → store `password_hash`, `salt` as before
- `password_enabled = 0` → store `NULL` for `password_hash` and `salt`

### 4.2 `GET /api/system/status`

**Current Response:**
```json
{ "initialized": true }
```

**New Response:**
```json
{
  "initialized": true,
  "password_enabled": false
}
```

### 4.3 `POST /api/auth/login`

**Current Request Model:**
```python
class LoginRequest(BaseModel):
    password: str
    remember_me: bool = False
```

**New Request Model:**
```python
class LoginRequest(BaseModel):
    password: str | None = None
    remember_me: bool = False
```

**New Login Logic:**
```python
async def login(body: LoginRequest):
    settings = get_settings()
    db = await get_db()
    try:
        row = await db.fetchone(
            "SELECT password_enabled, password_hash, salt FROM system_config WHERE id = 1"
        )
        if not row or row[0] is None:
            raise HTTPException(403, "System not initialized")

        password_enabled, password_hash, salt = row

        if not password_enabled:
            # No-auth mode: return fixed token
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
            token = "no-auth"
            cache_master_key(token, get_no_auth_master_key())
            return LoginResponse(data=LoginData(token=token, expires_in=31536000))

        # Password mode: existing logic
        if not body.password or not verify_password(body.password, password_hash):
            raise HTTPException(401, "Incorrect password")

        master_key = derive_master_key(body.password, salt)
        expires_at = datetime.now(timezone.utc) + timedelta(days=...)
        token = jwt.encode({"exp": expires_at}, settings.secret_key, algorithm="HS256")
        cache_master_key(token, master_key)
        return LoginResponse(...)
    finally:
        await db.close()
```

### 4.4 `get_current_user` Dependency

**New Logic in `src/auth/dependencies.py`:**
```python
async def get_current_user(credentials=Depends(security)):
    settings = get_settings()
    db = await get_db()
    try:
        row = await db.fetchone(
            "SELECT password_enabled FROM system_config WHERE id = 1"
        )
        password_enabled = bool(row[0]) if row else True

        if not password_enabled:
            # Ensure no-auth master key is always cached
            cache_master_key("no-auth", get_no_auth_master_key())
            return CurrentUser(token="no-auth")

        # Existing JWT validation + master_key cache check
        ...
    finally:
        await db.close()
```

### 4.5 Protected Routes — No Changes Required

All existing protected routes (`/api/knowledge/*`, `/api/chat/*`, `/api/research/*`) continue to use `get_current_user`. The dependency handles the auth bypass transparently.

---

## 5. Frontend Changes

### 5.1 `src/web/static/js/pages/init.js`

**UI Changes:**
- Add two radio cards:
  - `enable_password` (value: `true`)
  - `no_password` (value: `false`, selected by default)
- Conditional display of password fields:
  - Hidden when `no_password` selected
  - Shown when `enable_password` selected
- Client-side validation:
  - If `enable_password`: password must be non-empty and match confirmation

**API Integration:**
```javascript
const payload = {
    password_enabled: selectedOption === 'enable_password',
    password: selectedOption === 'enable_password' ? passwordValue : undefined
};
await apiPost('/system/init', payload);
```

### 5.2 `src/web/static/js/app.js` (or equivalent entry point)

**New Boot Sequence:**
```javascript
async function boot() {
    showLoading();
    const status = await apiGet('/system/status');

    if (!status.initialized) {
        redirect('#/init');
        return;
    }

    if (!status.password_enabled) {
        // Auto-login for no-auth mode
        const loginRes = await apiPost('/auth/login', {});
        storeToken(loginRes.data.token);
        mountApp();
        return;
    }

    // Password mode: existing logic
    const token = getToken();
    if (!token) {
        redirect('#/login');
    } else {
        mountApp();
    }
}
```

### 5.3 `src/web/static/js/router.js`

**Change to Route Guard:**
```javascript
function requireAuth() {
    const token = getToken();
    if (!token) {
        // If we're in no-auth mode, app.js should have already set the token
        // This fallback handles edge cases
        redirect('#/login');
    }
}
```

No major changes required — the guard still checks for token presence. The key difference is that `app.js` ensures the token is pre-populated in no-auth mode before routing.

---

## 6. CLI / Deployment Script Changes

### 6.1 `deploy.py` — New `reset-password` Subcommand

**Command Interface:**
```bash
python deploy.py reset-password
```

**Implementation Sketch:**
```python
def cmd_reset_password(config: DeploymentConfig) -> int:
    print("\033[91m⚠️  警告：此操作将永久删除所有本地数据！\033[0m\n")
    print("以下文件/目录将被删除：")
    print(f"  - {config.data_dir / 'app.db'}")
    print(f"  - {config.files_dir}")
    print("\n此操作不可恢复。")

    confirmation = input("请输入 RESET 以确认删除，或按 Ctrl+C 取消：\n> ").strip()
    if confirmation != "RESET":
        print("操作已取消，未做任何更改。")
        return 0

    # Stop service if running
    if is_running(config):
        stop_service(config)
        print("正在停止服务...")

    # Delete database
    db_path = config.data_dir / "app.db"
    if db_path.exists():
        db_path.unlink()
        print(f"已删除 {db_path}")

    # Delete attachments
    if config.files_dir.exists():
        import shutil
        shutil.rmtree(config.files_dir)
        print(f"已删除 {config.files_dir}")

    print("\033[92m✅ 重置完成。请重新运行启动脚本并完成初始化。\033[0m")
    return 0
```

**Edge Cases:**
- Service not running → proceed with file deletion
- Files already deleted by user → print "已不存在，跳过" and continue
- Non-interactive environment (piped input) → `input()` will read from stdin; if no `RESET`, cancel safely

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Module | Target | Cases |
|--------|--------|-------|
| `src/auth/crypto.py` | `get_no_auth_master_key()` | Deterministic output for same `SECRET_KEY`; 32 bytes length |
| `src/auth/dependencies.py` | `get_current_user` | Returns `CurrentUser("no-auth")` when `password_enabled=0`; raises 401 when `password_enabled=1` and no token |

### 7.2 Integration Tests

**New Fixture in `tests/conftest.py`:**
```python
@pytest.fixture
async def no_auth_client():
    # Initialize with password_enabled=False
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/api/system/init", json={"password_enabled": False})
        yield client
```

**Test Cases:**

| ID | Scenario | Expected |
|----|----------|----------|
| IT-001 | No-auth init → status returns `password_enabled: false` | ✅ |
| IT-002 | No-auth login with empty body → returns `no-auth` token | ✅ |
| IT-003 | Access `/api/system/config` without `Authorization` in no-auth mode | 200 OK |
| IT-004 | Upload attachment in no-auth mode → download decrypts correctly | ✅ |
| IT-005 | Existing password-mode tests continue to pass | 100% regression |

### 7.3 E2E Scenarios

| ID | Flow |
|----|------|
| E2E-001 | Uninitialized → select no-password → init → upload file → download file |
| E2E-002 | Password enabled → forget password → `deploy.py reset-password` with `RESET` → re-initialize |

---

## 8. Implementation Milestones

### Milestone A: Backend Foundation
1. [ ] Update `src/db/schema.sql` — add `password_enabled`
2. [ ] Add `get_no_auth_master_key()` to `src/auth/crypto.py`
3. [ ] Modify `src/auth/dependencies.py` — no-auth短路
4. [ ] Modify `src/auth/router.py` — no-auth login branch
5. [ ] Modify `src/system/router.py` — init/status endpoints

### Milestone B: Frontend Adaptation
6. [ ] Update `src/web/static/js/pages/init.js` — radio + conditional password
7. [ ] Update `src/web/static/js/app.js` — auto-login for no-auth mode
8. [ ] Verify `router.js` works with pre-populated no-auth token

### Milestone C: CLI Reset Password
9. [ ] Add `reset-password` subcommand to `deploy.py`
10. [ ] Add unit test for `cmd_reset_password` with mocked input

### Milestone D: Testing & Regression
11. [ ] Add `no_auth_client` fixture
12. [ ] Add integration tests for no-auth init, login bypass, attachment encrypt/decrypt
13. [ ] Run full test suite, resolve any regressions

---

## 9. Risks & Rollback

| Risk | Mitigation |
|------|------------|
| Old DB migration breaks | `DEFAULT 1` ensures backward compatibility; tested in IT-005 |
| Frontend flashes login page | Boot sequence uses loading state; no-auth token is fetched before routing |
| `reset-password` deletes wrong files | Use `DeploymentConfig` resolved paths; list paths for user confirmation |
| `no-auth` token leaks | Acceptable in single-user local context; documented in spec |

**Rollback Strategy:**
- All changes are additive (new column, new branch in auth logic)
- If critical issue found, reverting to pre-feature state requires:
  1. Revert git commits
  2. Run DB migration rollback (remove `password_enabled` column, or simply ignore it)

---

## 10. Constitution Compliance Check

对照 [Constitution v1.1.0](../.specify/memory/constitution.md) 进行合规验证：

| 原则/条款 | 状态 | 说明 |
|-----------|------|------|
| **1. 语言统一** | ✅ | 本文档及所有关联文档均使用简体中文 |
| **2. 规划优先** | ✅ | 在编码之前已完成 spec.md、research、product-spec |
| **3. 简洁设计** | ✅ | 无新增抽象层或外部依赖；全部在现有模块上扩展 |
| **4. Git 纪律** | ✅ | 所有变更将按小步提交纳入 Git；不自动推送 |
| **5. 复用优先** | ✅ | 复用现有 Argon2/JWT/SQLite 基础设施，未引入新依赖 |
| **6. 契约优先于实现** | ✅ | API 契约（init/login/status）已明确写入 spec.md，实现必须与之一致 |
| **7. 系统级探测双重验证** | ⚠️ | `deploy.py reset-password` 的停止服务逻辑需同时检测端口和 PID 文件（参照 002-one-click-deployment 的改进经验） |

**安全与质量：**
- ✅ 输入验证：`InitRequest` 对 `password_enabled` 和 `password` 做了联合校验
- ✅ 漏洞防护：无 SQL 注入风险（参数化查询）、无 XSS（纯后端改动）、无命令注入（`deploy.py` 使用 Python 标准路径操作）
- ✅ 错误处理：仅在系统边界（HTTP API、CLI 输入）添加校验

**开发工作流：**
- ✅ speckit 驱动：遵循 `spec → plan → tasks → implement`
- ✅ 独立测试：每个 milestone 可独立验证

---

## 11. Complexity Tracking

| 新增复杂度 | 理由 | 是否必要 |
|-----------|------|----------|
| `password_enabled` 数据库列 | 支持运行时查询认证策略 | 是 |
| `get_no_auth_master_key()` 函数 | 保证无密码模式下附件加密连续性 | 是 |
| 固定 token `"no-auth"` | 简化前端状态管理，避免大规模重构 | 是 |
| `deploy.py reset-password` | 提供官方密码恢复路径 | 是 |
