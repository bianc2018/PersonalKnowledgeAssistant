# Feature: 去除密码校验（本地个人部署模式）

> Created: 2026-04-12 | Status: Phase 4 — Bridge Complete
> Slug: `remove-password-verification`

## Lifecycle Status

| Phase | Status | Documents |
|-------|--------|-----------|
| 0. Problem Discovery | ✅ Complete | [problem-discovery/](./problem-discovery/) |
| 1. Research | ✅ Complete | [research/](./research/README.md) |
| 2. Product Spec | ✅ Complete | [product-spec/](./product-spec/README.md) |
| 3. Revalidation | ✅ Approved | [review.md](./review.md) |
| 4. SpecKit Bridge | ✅ Complete | [spec.md](./spec.md) |
| 5. Plan | ⏳ Pending | [plan.md](./plan.md) |
| 5B. Tasks | ⏳ Pending | [tasks.md](./tasks.md) |
| 5C. Pre-Impl Review | ⏳ Pending | [pre-impl-review.md](./pre-impl-review.md) |
| 6. Implementation | ⏳ Pending | — |
| 6B. Code Review | ⏳ Pending | [code-review.md](./code-review.md) |
| 7. Verification | ⏳ Pending | [verify-report.md](./verify-report.md) |
| 8A. Test Plan | ⏳ Pending | [testing/](./testing/) |
| 8B. Test Run | ⏳ Pending | [test-report.md](./test-report.md) |
| 9. Release Readiness | ⏳ Pending | [release-readiness.md](./release-readiness.md) |

## Quick Start

1. **Read the research:** [research/README.md](./research/README.md)
2. **Read the spec:** [product-spec/product-spec.md](./product-spec/product-spec.md)
3. **See the journeys:** [product-spec/user-journey.md](./product-spec/user-journey.md)
4. **See the wireframes:** [product-spec/wireframes.md](./product-spec/wireframes.md)

## Feature Description

为本地个人部署的 AI 知识助手提供可选的密码保护模式：
- 首次启动时可选择「无需密码，直接访问」或「启用密码保护」
- 不启用密码时跳过所有 JWT/Argon2 校验，同时通过固定 master_key 保证附件加密正常
- 启动脚本增加 `reset-password` 子命令，允许用户在忘记密码时通过 CLI 安全重置（二次确认后清空数据）
