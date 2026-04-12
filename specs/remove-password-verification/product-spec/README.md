# Product Spec Index: 去除密码校验（本地个人部署模式）

> Status: DRAFT | Created: 2026-04-12 | Last updated: 2026-04-12
> Feature slug: `remove-password-verification`
> ← [Back to Feature Root](../README.md) | ← [Research](../research/README.md)

## What We're Building

为本地个人部署的 AI 知识助手提供可选的密码保护模式：首次启动时可选择「无需密码，直接访问」，启用后跳过所有登录校验；同时通过 CLI 脚本提供安全的「重置密码」能力，在二次确认后清空数据并恢复初始化状态。

## Document Map

| Document | Purpose | Detail Level | Status |
|----------|---------|--------------|--------|
| [product-spec.md](./product-spec.md) | 主 PRD — 目标、用户故事、功能需求、风险 | Standard | DRAFT |
| [user-journey.md](./user-journey.md) | 5 条核心用户旅程（首次启动无密码/有密码、日常访问、CLI 重置、取消操作） | Standard | DRAFT |
| [wireframes.md](./wireframes.md) | 3 个 Web 线框图 + CLI 交互草图（Text/ASCII） | Text/ASCII | DRAFT |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 默认策略 | 默认提供「无需密码」选项 | 与 Ollama、Jupyter 等本地个人工具一致，降低首次部署 friction |
| 无密码加密方案 | `SHA256(SECRET_KEY)` 作为固定 master_key | 无需改数据库结构，保证附件加解密连续工作 |
| 运行时切换 | v1 不支持「有/无密码」热切换 | master_key 变更会导致历史附件无法解密，超出 v1 范围 |
| 密码重置入口 | CLI 脚本 `reset-password` | 本地无邮件服务器，CLI 是最直接安全的恢复路径 |
| 二次确认强度 | 要求输入 `RESET` | 防止用户惯性回车误触 destructive action |

## Must Read

1. **Start here:** [product-spec.md](./product-spec.md)
2. **See flows:** [user-journey.md](./user-journey.md)
3. **See layouts:** [wireframes.md](./wireframes.md)
4. **Background research:** [../research/README.md](../research/README.md)
