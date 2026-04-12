# Research Index: 去除密码校验（本地个人部署模式）

> Generated: 2026-04-12 | Feature: remove-password-verification
> Input richness: 6/8 | Interview mode: CONFIRM
> Research dimensions: competitors ✅ · UX/UI ✅ · codebase ✅

## Executive Summary

本次调研分析了 8 个本地自托管工具在认证策略上的设计差异，发现知识管理/内容管理类工具普遍强制密码（如 Immich、Memos），而开发者工具则原生支持无密码（如 Ollama、Jupyter）。核心洞察是：**没有任何竞品同时满足"原生可选密码 + 关闭后保留完整 Web 功能 + 启动脚本级密码重置"这三点**，这构成了显著的差异化机会。

代码层面，当前系统的核心挑战不在于"去掉密码校验"本身，而在于 `master_key`（由密码派生）与附件 AES-256-GCM 加密深度耦合。无密码模式下必须提供一个稳定的替代 master_key 来源（推荐基于 `SECRET_KEY` 的 SHA-256 派生），否则现有加密文件将无法访问。

## Key Findings

| Dimension | Top Insight |
|-----------|-------------|
| 🏆 Competitors | 本地工具呈现两极分化：Ollama/Jupyter 默认无密码；Immich/Vaultwarden 认证不可妥协。知识管理赛道缺少原生可选密码的官方实现。 |
| 🎨 UX/UI | 最佳实践：首次启动向导明确选择「启用密码」或「直接访问」；CLI 重置使用大写 `RESET` 二次确认；Web 端不提供无效的「忘记密码」链接。 |
| 🔧 Codebase | FastAPI + JWT + Argon2 架构清晰，改动集中在 `auth/dependencies.py`、`system/router.py` 和前端路由守卫；需新增 `password_enabled` 字段和固定 no-auth master_key。 |
| 🔒 Constraints | `master_key` 是附件加密的必要条件；不支持"有密码 ↔ 无密码"热切换（会导致旧附件无法解密），建议在初始化时一次性选择。 |

## Research Documents

| Document | Status | Key Insight |
|----------|--------|-------------|
| [competitors.md](./competitors.md) | ✅ | 竞品在本地无密码策略上分化严重，知识管理类存在明显空白，启动脚本级重置密码更是无人实现。 |
| [ux-patterns.md](./ux-patterns.md) | ✅ | 推荐 CLI 引导 + Web 向导双通道、`/api/auth/status` 状态接口、默认不启用密码策略。 |
| [codebase-analysis.md](./codebase-analysis.md) | ✅ | 约 13~19 个文件需改动，复杂度中等；关键是 master_key 稳定来源和模式切换风险。 |

## Synthesis: Recommended Approach

1. **默认无密码**：首次启动时默认提供「无需密码，直接访问」选项，降低个人用户首次部署门槛。这直接对标 Ollama 的「localhost 零认证」体验。
2. **可选密码保护**：用户仍可在首次向导或后续设置中选择启用密码，启用后恢复现有 JWT + Argon2 认证流程。
3. **稳定 no-auth master_key**：无密码模式下使用 `hashlib.sha256(settings.secret_key.encode()).digest()` 作为固定 master_key，确保附件加密/解密在不输入密码时仍能正常工作。
4. **启动脚本重置密码**：在 `deploy.py` 中新增 `reset-password` 子命令，交互式要求输入 `RESET` 二次确认，然后清空数据库和 `files/` 目录，回到未初始化状态。
5. **不支持运行时热切换**：由于 master_key 会变化导致旧附件无法解密，建议「有密码 / 无密码」作为初始化时的一次性选择；后续更改需走"导出 → 重置 → 导入"流程。

## Open Questions for Product Spec

1. **前端技术细节**：当前前端使用什么框架/库（原生 JS / Vue / Alpine）？`getToken()` 和路由守卫的具体实现在哪个文件？
2. **初始化流程**：当前首次访问时是直接跳到 `#/init` 还是由后端返回 `initialized: false` 后前端再跳转？
3. **设置页存在性**：当前 Web 界面是否有「系统设置」页面？如果有，在哪里添加「安全」分组最合适？
4. **备份兼容性**：无密码模式下导出的备份 ZIP，当用户后续重置密码后重新初始化，是否仍可导入？（取决于 master_key 是否一致——若 SECRET_KEY 不变则可以）
5. **部署方式覆盖**：除 `deploy.py` 外，项目是否支持 Docker、systemd 等其他部署方式？这些入口是否也需要暴露"重置密码"能力？

## Red Flags / Risks Identified

| 风险 | 严重程度 | 说明 |
|------|----------|------|
| **master_key 变更导致历史附件无法解密** | 高 | 若用户从"有密码"切到"无密码"，master_key 改变后旧文件变为乱码。方案：禁止热切换，或要求重新加密全部附件。 |
| **固定 no-auth token 被滥用** | 低 | 由于 `no-auth` token 是写死的，若前端 localStorage 被恶意脚本读取，理论上可构造请求。但本地单用户场景下该风险可接受。 |
| **重置密码=清空数据被误触** | 中 | 必须通过强交互确认（如输入 `RESET`）和 ANSI 红色高亮警告来降低误操作概率。 |
| **旧测试夹具假设必须 login** | 低 | `tests/conftest.py` 中的 `auth_client` fixture 需要补充 `no_auth_client`，确保回归覆盖。 |
