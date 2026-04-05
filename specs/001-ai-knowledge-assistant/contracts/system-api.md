# 系统 API 契约

> 路径前缀: `/api/system`

---

## 1. 用户登录

**POST** `/api/auth/login`

### 请求体

```json
{
  "password": "your_secure_password"
}
```

### 成功响应 (200)

```json
{
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

### 错误响应

- `UNAUTHORIZED` (401): 密码错误。

---

## 2. 初始化系统（首次使用）

**POST** `/api/system/init`

### 请求体

```json
{
  "password": "your_secure_password"
}
```

### 字段说明

- 密码必须 ≥ 8 位，且同时包含英文字母和阿拉伯数字。

### 成功响应 (201)

```json
{
  "data": {
    "message": "系统初始化完成"
  }
}
```

### 错误响应

- `VALIDATION_ERROR` (422): 密码强度不足。

---

## 3. 获取系统状态

**GET** `/api/system/status`

### 成功响应 (200)

```json
{
  "data": {
    "initialized": true,
    "version": "0.1.0",
    "llm_connected": true,
    "search_source_available": "search_api",
    "embedding_available": true,
    "knowledge_count": 128,
    "storage_used_bytes": 2147483648
  }
}
```

---

## 4. 获取系统配置

**GET** `/api/system/config`

### 成功响应 (200)

```json
{
  "data": {
    "llm_config": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-****",
      "model": "gpt-4o",
      "enable_search": false
    },
    "embedding_config": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-****",
      "model": "text-embedding-3-small"
    },
    "search_config": {
      "provider": "tavily",
      "api_key": "tvly-****",
      "base_url": ""
    },
    "privacy_settings": {
      "allow_full_content": false,
      "allow_web_search": true,
      "allow_log_upload": false
    },
    "retry_settings": {
      "retry_times": 3,
      "timeout_seconds": 30
    },
    "storage_settings": {
      "archive_threshold_gb": 10.0,
      "research_concurrency_limit": 2,
      "version_retention_policy": null
    },
    "log_settings": {
      "level": "INFO",
      "retention_days": 30
    }
  }
}
```

**注意**：敏感字段（如 `api_key`）在后端存储时加密，返回时做掩码处理（如 `sk-****`）。

---

## 5. 更新系统配置

**PUT** `/api/system/config`

### 请求体

部分更新即可，未提供的字段保持原值。

```json
{
  "llm_config": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-new-key",
    "model": "gpt-4o"
  },
  "privacy_settings": {
    "allow_web_search": true
  }
}
```

### 成功响应 (200)

返回更新后的完整配置。

---

## 6. 导出知识库

**POST** `/api/system/export`

### 请求体

```json
{
  "password": "your_secure_password"
}
```

### 成功响应 (200)

返回 `application/zip` 二进制流。ZIP 包结构：

```text
export-2026-04-05.zip
├── metadata.json
├── files/
│   └── AB/
│       └── CD/
│           └── <item-id>/
│               └── original.pdf.enc
└── README.txt
```

### `metadata.json` 示例

```json
{
  "version": "1.0",
  "export_at": "2026-04-05T10:00:00Z",
  "embedding_model": "text-embedding-3-small",
  "items": [
    {
      "id": "item-001",
      "title": "...",
      "versions": [...],
      "tags": [...]
    }
  ]
}
```

---

## 7. 导入知识库

**POST** `/api/system/import`

### 请求格式

`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | 由本系统导出的 ZIP 压缩包 |

### 成功响应 (200)

```json
{
  "data": {
    "imported_items": 50,
    "skipped_files": [
      {
        "path": "files/AB/CD/item-xyz/corrupted.pdf.enc",
        "reason": "解密失败，文件可能已损坏"
      }
    ],
    "message": "导入完成。已跳过 1 个损坏文件，详见列表。"
  }
}
```

### 行为说明

- **顶层校验**：首先校验 `metadata.json` 的结构和版本兼容性；若顶层校验失败，整体中止导入并返回错误。
- **单文件容错**：仅当顶层校验通过后，损坏或不支持的内部文件才会被安全跳过并继续导入。
- 若 embedding 模型标识与当前配置不一致，自动触发重新计算嵌入向量。
- 导入完成后以汇总报告形式提示用户被跳过的文件及原因。

---

## 8. 重置系统（忘记密码）

**POST** `/api/system/reset`

### 成功响应 (200)

```json
{
  "data": {
    "message": "系统已重置。所有本地加密数据已清除，请重新初始化并导入备份。"
  }
}
```

### 行为说明

- 清除数据库和加密文件（保留空的数据库结构）。
- 系统回到未初始化状态，**必须重新调用 `/api/system/init`** 设置密码后才能恢复可用。
- 明确提示原始加密数据不可恢复（符合 spec FR-025）。
