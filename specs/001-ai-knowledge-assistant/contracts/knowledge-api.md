# 知识库 API 契约

> 路径前缀: `/api/knowledge`

---

## 1. 创建知识（文本）

**POST** `/api/knowledge`

### 请求体

```json
{
  "title": "低空经济政策分析",
  "content": "2024 年以来，低空经济被写入多地政府工作报告...",
  "source_type": "text",
  "tags": ["_policy", "aviation"]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 标题（为空时后端自动摘要生成） |
| `content` | string | 是 | 纯文本内容，长度 ≥ 5 字符 |
| `source_type` | string | 是 | 固定为 `text` |
| `tags` | string[] | 否 | 标签名称列表，不存在时自动创建 |

### 成功响应 (201)

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "低空经济政策分析",
    "source_type": "text",
    "current_version_id": "660e8400-e29b-41d4-a716-446655440001",
    "tags": [
      { "id": "...", "name": "_policy", "color": null },
      { "id": "...", "name": "aviation", "color": null }
    ],
    "confidence": {
      "score_level": "medium",
      "score_value": 0.72,
      "rationale": "基于网络信息交叉验证，数据来源较为可靠。"
    },
    "is_deleted": false,
    "created_at": "2026-04-05T08:30:00Z",
    "updated_at": "2026-04-05T08:30:00Z"
  }
}
```

### 错误响应

- `VALIDATION_ERROR` (422): `content` 长度不足 5 字符。

---

## 2. 上传文件创建知识

**POST** `/api/knowledge/upload`

### 请求格式

`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | 附件文件，大小 ≤ 1GB |
| `title` | string | 否 | 标题，为空时使用文件名 |
| `tags` | string | 否 | 逗号分隔的标签名称 |

### 成功响应 (201)

与文本创建成功响应结构相同。`source_type` 为 `file`。

若文件提取失败：

```json
{
  "data": {
    "id": "...",
    "title": "example.pdf",
    "source_type": "file",
    "attachments": [
      {
        "id": "...",
        "filename": "example.pdf",
        "extraction_status": "failed",
        "extraction_error": "不支持的 PDF 加密格式"
      }
    ],
    "confidence": null,
    ...
  }
}
```

---

## 3. 添加网页链接

**POST** `/api/knowledge/url`

### 请求体

```json
{
  "url": "https://example.com/article",
  "title": "",
  "tags": ["待读"]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | HTTP(S) 链接 |
| `title` | string | 否 | 标题，为空时后端抓取网页后提取 |
| `tags` | string[] | 否 | 标签列表 |

### 成功响应 (201)

`source_type` 为 `url`。

---

## 4. 知识列表

**GET** `/api/knowledge?offset=0&limit=20&q=&tags=&include_deleted=false`

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `offset` | int | 0 | 分页偏移 |
| `limit` | int | 20 | 分页大小，最大 100 |
| `q` | string | "" | 关键词搜索（标题 + 内容全文检索） |
| `tags` | string | "" | 逗号分隔的标签名称过滤 |
| `include_deleted` | bool | false | 是否包含软删除条目 |

### 成功响应 (200)

```json
{
  "data": [
    {
      "id": "...",
      "title": "低空经济政策分析",
      "source_type": "text",
      "tags": [...],
      "confidence": { "score_level": "medium", ... },
      "version_count": 3,
      "is_deleted": false,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 100
  }
}
```

---

## 5. 获取知识详情

**GET** `/api/knowledge/{id}`

### 成功响应 (200)

```json
{
  "data": {
    "id": "...",
    "title": "...",
    "source_type": "text",
    "current_version": {
      "id": "...",
      "content_text": "...",
      "created_at": "..."
    },
    "versions": [
      { "id": "...", "created_at": "...", "created_by": "user_edit" }
    ],
    "attachments": [...],
    "tags": [...],
    "confidence": {
      "score_level": "high",
      "score_value": 0.88,
      "method": "web_verification",
      "rationale": "...",
      "evaluated_at": "..."
    },
    "is_deleted": false,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

---

## 6. 更新知识

**PATCH** `/api/knowledge/{id}`

### 请求体

```json
{
  "title": "更新后的标题",
  "content": "更新后的内容...",
  "tags": ["_policy"]
}
```

### 行为说明

- 若 `content` 发生显著变化（文本差异比例 > 20%），系统自动创建新版本并触发置信度重新评估。
- 若变化 ≤ 20% 且无其他字段更新，可选择仅修改当前版本的元数据（设计决策，MVP 阶段建议：任何 `content` 变更均生成新版本以保证可追溯）。

### 成功响应 (200)

返回更新后的知识详情。

---

## 7. 删除知识（软删除）

**DELETE** `/api/knowledge/{id}`

### 成功响应 (204)

无响应体。

### 行为说明

- 仅将 `is_deleted` 标记为 `true`，保留原始数据、附件和历史版本。
- 历史对话和调研报告中的引用仍然有效。

---

## 8. 手动触发置信度评估

**POST** `/api/knowledge/{id}/evaluate-confidence`

### 成功响应 (202)

```json
{
  "data": {
    "task_status": "queued",
    "message": "置信度评估任务已提交"
  }
}
```

---

## 9. 获取附件下载链接

**GET** `/api/knowledge/{id}/attachments/{attachment_id}/download`

### 成功响应 (200)

以 `application/octet-stream` 返回解密后的原始文件内容。

---

## 10. 标签列表

**GET** `/api/knowledge/tags`

### 成功响应 (200)

```json
{
  "data": [
    { "id": "...", "name": "_policy", "color": "#3b82f6", "item_count": 12 }
  ]
}
```
