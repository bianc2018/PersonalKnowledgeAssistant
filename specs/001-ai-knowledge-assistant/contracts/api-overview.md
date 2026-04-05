# API 契约总览

> 生成日期: 2026-04-05 | 关联 Plan: [plan.md](../plan.md) | 关联 Data Model: [../data-model.md](../data-model.md)

---

## 1. API 设计原则

- **协议**: HTTPS（开发环境可用 HTTP）
- **格式**: JSON
- **认证**: 所有非公开端点通过 `Authorization: Bearer <token>` 进行鉴权
- **错误格式**: 统一返回 `{"error": {"code": "ERROR_CODE", "message": "人类可读说明"}}`
- **分页**: 列表接口默认支持 `?offset=0&limit=20`

## 2. 端点分组

| 分组 | 基础路径 | 契约文档 |
|------|----------|----------|
| 知识库 | `/api/knowledge` | [knowledge-api.md](./knowledge-api.md) |
| 对话 | `/api/chat` | [chat-api.md](./chat-api.md) |
| 调研 | `/api/research` | [research-api.md](./research-api.md) |
| 系统 | `/api/system` | [system-api.md](./system-api.md) |

## 3. 通用响应模式

### 3.1 成功响应（单对象）

```json
{
  "data": { ... }
}
```

### 3.2 成功响应（列表）

```json
{
  "data": [ ... ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 100
  }
}
```

### 3.3 错误响应

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "内容长度必须至少为 5 个字符"
  }
}
```

### 3.4 常见错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| `UNAUTHORIZED` | 401 | 未登录或 Token 无效 |
| `FORBIDDEN` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `VALIDATION_ERROR` | 422 | 请求参数校验失败 |
| `RATE_LIMITED` | 429 | 请求过于频繁 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 外部服务不可用 |

## 4. 认证流程

1. **登录**: `POST /api/auth/login`
   - 请求: `{ "password": "..." }`
   - 响应: `{ "token": "jwt-token" }`
2. **后续请求**: 所有受保护端点需在 Header 中携带 `Authorization: Bearer jwt-token`
3. **Token 过期**: 返回 401，前端引导用户重新登录
