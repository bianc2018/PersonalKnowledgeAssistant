# User Journey: 去除密码校验（本地个人部署模式）

> Feature: remove-password-verification | Persona: 李明（个人用户）
> Related: [Product Spec](./product-spec.md) | [Wireframes](./wireframes.md)

---

## Journey 1: 首次启动 — 选择无需密码模式（Happy Path）

| Step | User Action | System Response | Emotion | Notes |
|------|-------------|-----------------|---------|-------|
| 1 | 下载/克隆项目，运行启动脚本 `python deploy.py start` | 脚本检测到数据库为空，启动服务并提示访问地址 | 😊 | 后台静默完成 |
| 2 | 打开浏览器访问 `http://localhost:8000` | 前端检测到 `initialized: false`，展示初始化向导 | 😊 | 不是登录页，是向导 |
| 3 | 在向导中看到「是否启用密码保护？」，默认选中「无需密码，直接访问」 | 单选卡片高亮当前选项，密码输入区隐藏 | 😊 | 默认降低 friction |
| 4 | 直接点击「开始使用」按钮 | 前端调用 `POST /api/system/init`（`password_enabled: false`），系统完成初始化 | 😊 | 无需输入任何密码 |
| 5 | 初始化成功 | 页面自动进入应用主界面，显示知识库首页 | 😊 | 全程无登录页 |

**Entry point:** 运行启动脚本后首次打开浏览器  
**Exit point:** 进入应用主界面并开始使用  
**Expected completion time:** 5–10 秒  
**Drop-off risk points:** 无（默认路径摩擦最低）

---

## Journey 2: 首次启动 — 选择启用密码保护

| Step | User Action | System Response | Emotion | Notes |
|------|-------------|-----------------|---------|-------|
| 1 | 运行启动脚本并打开浏览器 | 展示初始化向导 | 😐 | — |
| 2 | 在向导中选中「启用密码保护」 | 页面展开密码输入框和确认密码输入框 | 😐 | — |
| 3 | 输入密码并确认密码，点击「开始使用」 | 前端校验两次输入一致后提交 `POST /api/system/init`（`password_enabled: true, password: ...`） | 😐 | — |
| 4 | 系统返回初始化成功 | 页面跳转至登录页 | 😊 | 与现有行为一致 |
| 5 | 在登录页输入刚才设置的密码并登录 | 校验成功后进入主界面 | 😊 | 保留现有完整体验 |

**Entry point:** 运行启动脚本后首次打开浏览器  
**Exit point:** 从登录页进入主界面  
**Expected completion time:** 15–20 秒  
**Drop-off risk points:** 密码设置时的输入错误可能带来短暂挫败感

---

## Journey 3: 常规访问 — 无密码模式

| Step | User Action | System Response | Emotion | Notes |
|------|-------------|-----------------|---------|-------|
| 1 | 再次打开浏览器访问 `http://localhost:8000` | 前端应用加载，调用 `/api/system/status` 获取状态 | 😊 | — |
| 2 | （无需操作） | 系统返回 `initialized: true, password_enabled: false`；前端自动调用 `/api/auth/login` 获取固定 token 并存入缓存 | 😊 | 用户无感知 |
| 3 | （无需操作） | 路由守卫判断 token 已存在，直接渲染主界面 | 😊 | 无登录页闪跳 |

**Entry point:** 日常打开浏览器访问应用  
**Exit point:** 直接进入主界面  
**Expected completion time:** 2–3 秒  
**Drop-off risk points:** 若前端网络慢，loading 时间可能稍长，但不会影响最终体验

---

## Journey 4: 常规访问 — 有密码模式

| Step | User Action | System Response | Emotion | Notes |
|------|-------------|-----------------|---------|-------|
| 1 | 再次打开浏览器访问 `http://localhost:8000` | 前端检测到 `password_enabled: true` 且无有效 token | 😐 | 与现有行为一致 |
| 2 | 在登录页输入密码，点击登录 | 后端校验 Argon2 哈希，签发 JWT，派生 master_key 并缓存 | 😊 | 现有完整流程 |
| 3 | 登录成功 | 页面进入主界面 | 😊 | — |

**Entry point:** 日常打开浏览器访问应用  
**Exit point:** 从登录页进入主界面  
**Expected completion time:** 5–8 秒  
**Drop-off risk points:** 忘记密码时无路可走（由 Journey 5 解决）

---

## Journey 5: 忘记密码 — CLI 重置

| Step | User Action | System Response | Emotion | Notes |
|------|-------------|-----------------|---------|-------|
| 1 | 在终端运行 `python deploy.py reset-password` | 脚本检查当前服务状态 | 😤 | 已无法登录，情绪偏负面 |
| 2 | 看到红色高亮警告：「此操作将永久删除所有本地数据，包括数据库和附件文件」 | 脚本列出将被删除的路径（`data/app.db`、`files/`） | 😤 | 明确后果 |
| 3 | 阅读警告后，输入 `RESET` 确认 | 脚本验证输入为 `RESET` | 😐 | 强确认防止误触 |
| 4 | 系统执行：停止服务 → 删除数据库 → 删除附件目录 | 终端输出每项删除的进度 | 😐 | 数据已清空 |
| 5 | 重置完成 | 脚本输出成功信息：「数据已清空，请重新运行启动脚本并完成初始化。」 | 🙂 | 重新获得控制权 |
| 6 | 重新运行 `python deploy.py start` | 回到 Journey 1 或 Journey 2 的初始化向导 | 🙂 | 新的开始 |

**Entry point:** 用户忘记密码，无法访问系统  
**Exit point:** 系统回到未初始化状态，用户可重新配置  
**Expected completion time:** 20–40 秒  
**Drop-off risk points:** 用户在看到「删除所有数据」警告后可能犹豫，但这是预期行为

---

## Alternative Paths

### Path A: 用户在 CLI 重置时取消操作

| Step | Action | Outcome |
|------|--------|---------|
| 1 | 运行 `python deploy.py reset-password` | 显示警告和确认提示 |
| 2 | 输入的不是 `RESET`（如 `no`、`n`、空回车） | 脚本输出「操作已取消，未做任何更改。」 |
| 3 | 退出脚本 | 系统一切如初 |

### Path B: 用户通过 Docker / systemd 等非交互方式启动

| Step | Action | Outcome |
|------|--------|---------|
| 1 | 使用非 `deploy.py` 的方式启动 | 由 Web 端初始化向导兜底 |
| 2 | 首次访问时展示 Web 初始化向导 | 用户可直接选择「无需密码，直接访问」 |

---

## Error Scenarios

| Scenario | Trigger | Recovery |
|----------|---------|----------|
| 初始化提交两次密码不一致 | 用户输入错误 | 前端拦截，显示「两次输入的密码不一致」 |
| 网络异常导致 `/api/system/init` 失败 | 后端服务未就绪 | 显示 Toast 错误：「初始化失败，请检查服务是否正常运行」 |
| 无密码模式下 `/api/auth/login` 被异常调用 | 前端逻辑 bug | 后端正常返回固定 token，不影响功能 |
| CLI 重置时数据文件已被手动删除 | 用户提前删过 | 脚本继续执行剩余清理，输出提示：「某些文件已不存在，跳过」 |

---

## Journey Metrics

| Journey | Entry Point | Exit Point | Completion Time | Drop-off Risk |
|---------|-------------|------------|-----------------|---------------|
| 首次启动（无密码） | 运行脚本后打开浏览器 | 进入主界面 | 5–10s | 极低 |
| 首次启动（有密码） | 运行脚本后打开浏览器 | 登录后进入主界面 | 15–20s | 低 |
| 日常访问（无密码） | 打开浏览器 | 进入主界面 | 2–3s | 极低 |
| 日常访问（有密码） | 打开浏览器 | 登录后进入主界面 | 5–8s | 低 |
| 忘记密码后 CLI 重置 | 运行 `reset-password` | 回到未初始化状态 | 20–40s | 中（用户可能因警告而犹豫） |
