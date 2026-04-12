# Wireframes: 去除密码校验（本地个人部署模式）

> Related: [Product Spec](./product-spec.md) | [User Journey](./user-journey.md)
> Navigation: [Screen 1: 初始化向导](#screen-1-初始化向导) | [Screen 2: 登录页](#screen-2-登录页) | [Screen 3: 应用加载状态](#screen-3-应用加载状态)

---

## Screen 1: 初始化向导

**Purpose:** 系统首次启动时的初始化页面。用户在此选择是否启用密码保护，并完成基础配置。

### Layout (Desktop, centered card ~420px)

```
┌──────────────────────────────────────────┐
│  AI 知识管理助手                          │
│  ─────────────────────────────────────   │
│  欢迎使用！请选择访问方式                  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  ○ 启用密码保护                     │  │
│  │    适用于多人共用设备或公开网络     │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  ● 无需密码，直接访问  （默认）     │  │
│  │    适用于个人独立设备               │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ─── 密码设置 ───                        │
│  （以下输入框仅在「启用密码保护」时显示）  │
│                                          │
│  设置密码                                 │
│  ┌────────────────────────────────────┐  │
│  │  ••••••••                          │  │
│  └────────────────────────────────────┘  │
│                                          │
│  确认密码                                 │
│  ┌────────────────────────────────────┐  │
│  │  ••••••••                          │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [          开始使用          ]          │
│                                          │
└──────────────────────────────────────────┘
```

### Components
- **Title / Subtitle:** `AI 知识管理助手` + `欢迎使用！请选择访问方式`
- **Radio cards (2):** 单选卡片，选中态有边框高亮
- **Conditional password inputs:** 两个密码输入框，默认隐藏，仅在启用密码时显示
- **Primary button:** `开始使用`，居中大按钮

### States

| State | Visual |
|-------|--------|
| Default | 默认选中「无需密码」，密码区隐藏，按钮可用 |
| Password selected | 选中「启用密码保护」，密码区展开，自动聚焦第一个输入框 |
| Submitting | 按钮变灰并显示 spinner，禁用再次点击 |
| Error (password mismatch) | 确认密码框边框变红，下方提示 `两次输入的密码不一致` |
| Error (network) | Toast/alert: `初始化失败，请稍后重试` |

---

## Screen 2: 登录页

**Purpose:** 用户选择「启用密码保护」后的登录页面。极简设计，无用户名、无注册、无找回密码链接。

### Layout (Desktop, centered card ~360px)

```
┌─────────────────────────────┐
│                             │
│      AI 知识管理助手         │
│                             │
│      请输入密码以继续        │
│                             │
│  ┌───────────────────────┐  │
│  │  🔒 输入密码          │  │
│  └───────────────────────┘  │
│                             │
│  [        登录        ]     │
│                             │
│  ─────────────────────────  │
│  忘记密码？                 │
│  请运行终端命令重置：        │
│  python deploy.py reset-password  │
│                             │
└─────────────────────────────┘
```

### Components
- **Brand title:** 大字号应用名称
- **Subtitle:** `请输入密码以继续`
- **Password input:** 带锁图标的密码输入框，支持显示/隐藏切换
- **Login button:** 大按钮，Enter 键可提交
- **Help text:** 底部灰色小字，提示忘记密码时的 CLI 重置命令

### States

| State | Visual |
|-------|--------|
| Default | 密码框空，按钮可用 |
| Typing | 显示/隐藏密码 toggle 可点击 |
| Loading | 按钮内显示 spinner，禁用输入 |
| Error (wrong password) | 密码框轻微 shake + 边框变红 + 提示 `密码错误` |
| Error (session expired) | 从其他页面被踢回时，提示 `会话已过期，请重新登录` |

---

## Screen 3: 应用加载状态

**Purpose:** 应用在启动时检测认证状态的过渡页面。避免无密码模式下闪现登录页。

### Layout (Full viewport, centered content)

```
┌────────────────────────────────────┐
│                                    │
│                                    │
│                                    │
│         ⟳  加载中...               │
│                                    │
│      正在准备您的工作空间          │
│                                    │
│                                    │
│                                    │
│                                    │
│                                    │
│                                    │
│                                    │
│                                    │
└────────────────────────────────────┘
```

### Components
- **Spinner:** 居中旋转图标
- **Status text:** `加载中...` 或 `正在准备您的工作空间`

### Behavior
- 页面一出现即显示此 loading 状态
- 后台并行请求 `/api/system/status`
- 判断逻辑：
  - `initialized == false` → 跳转 `#/init`
  - `initialized == true && password_enabled == false` → 自动调用 `/api/auth/login`（空参数）获取固定 token → 进入主界面
  - `initialized == true && password_enabled == true && no token` → 跳转 `#/login`
  - `initialized == true && password_enabled == true && has token` → 进入主界面

### States

| State | Visual |
|-------|--------|
| Loading | 显示 spinner 和提示文字 |
| Timeout (>3s) | Spinner 下方增加提示 `若加载过久，请刷新页面重试` |
| Error (server unreachable) | 显示错误图标 + `无法连接到服务，请检查是否已启动` + [重试] 按钮 |

---

## CLI Wireframe: reset-password 终端交互

**Purpose:** 在终端中提供交互式密码重置，防止误触。

### Terminal Output

```
$ python deploy.py reset-password

⚠️  警告：此操作将永久删除所有本地数据！

以下文件/目录将被删除：
  - /home/user/ai-assistant/data/app.db
  - /home/user/ai-assistant/files/

此操作不可恢复。如果您忘记了密码，重置后需要重新初始化系统。

请输入 RESET 以确认删除，或按 Ctrl+C 取消：
> RESET

正在停止服务...
已删除 /home/user/ai-assistant/data/app.db
已删除 /home/user/ai-assistant/files/
✅ 重置完成。请重新运行启动脚本并完成初始化。
```

### Behavior
- 首行警告使用红色 ANSI 高亮（`\033[91m`）
- 列出将被删除的绝对路径
- 用户输入不是 `RESET` 时：输出 `操作已取消，未做任何更改。` 并退出
- 确认后依次执行：停止服务 → 删除数据库 → 删除附件目录 → 输出成功信息
