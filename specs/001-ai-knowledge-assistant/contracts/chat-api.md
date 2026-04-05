# 对话 API 契约

> 路径前缀: `/api/chat`

---

## 1. 获取会话列表

**GET** `/api/chat/conversations?offset=0&limit=20`

### 成功响应 (200)

```json
{
  "data": [
    {
      "id": "conv-001",
      "title": "关于低空经济的讨论",
      "message_count": 8,
      "last_message_at": "2026-04-05T09:00:00Z",
      "created_at": "2026-04-05T08:00:00Z"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 5
  }
}
```

---

## 2. 创建新会话

**POST** `/api/chat/conversations`

### 请求体

```json
{
  "title": "新会话"
}
```

### 成功响应 (201)

```json
{
  "data": {
    "id": "conv-002",
    "title": "新会话",
    "created_at": "2026-04-05T10:00:00Z",
    "updated_at": "2026-04-05T10:00:00Z"
  }
}
```

---

## 3. 获取会话消息

**GET** `/api/chat/conversations/{conversation_id}/messages`

### 成功响应 (200)

```json
{
  "data": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "低空经济有哪些政策支持？",
      "created_at": "2026-04-05T08:01:00Z"
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "根据您知识库中的《低空经济政策分析》，目前有以下几个政策支持方向：\n\n1. 空域管理改革 ...（内容省略）\n\n[1] 低空经济政策分析",
      "citations": [
        {
          "index": 1,
          "item_id": "item-001",
          "item_title": "低空经济政策分析",
          "chunk_text": "2024 年以来，低空经济被写入多地政府工作报告..."
        }
      ],
      "created_at": "2026-04-05T08:01:05Z"
    }
  ]
}
```

---

## 4. 发送消息（流式/非流式）

**POST** `/api/chat/conversations/{conversation_id}/messages`

### 请求体

```json
{
  "content": "给我讲讲低空经济的趋势",
  "stream": true
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | string | 是 | 用户消息内容 |
| `stream` | boolean | 否 | 是否使用 SSE 流式返回，默认 `false` |

### 非流式成功响应 (200)

```json
{
  "data": {
    "id": "msg-003",
    "role": "assistant",
    "content": "...",
    "citations": [...],
    "created_at": "..."
  }
}
```

### 流式响应 (SSE)

当 `stream=true` 时，接口返回 `text/event-stream`。

```text
content-type: text/event-stream

id: 1
event: delta
data: {"delta": "根据"}

id: 2
event: delta
data: {"delta": "您的知识库"}

id: 3
event: citation
data: {"citations": [{"index": 1, "item_id": "...", "item_title": "..."}]}

id: 4
event: done
data: {}
```

### 事件类型

| 事件名 | 说明 |
|--------|------|
| `delta` |  assistant 回复的增量文本 |
| `citation` |  引用来源信息（通常在生成结束时推送一次） |
| `done` |  生成完成 |
| `error` |  生成过程中发生错误 |

### 行为说明

- 系统基于用户问题执行 RAG 检索：先通过 sqlite-vec 做向量相似度搜索，再通过 FTS5 做关键词补充，合并召回相关文本片段。
- 若知识库中无相关内容，助手必须明确告知用户，而非编造答案。
- 回答生成时会注入 `UserProfile` 中的兴趣和知识水平，调整回答深度。

---

## 5. 删除会话

**DELETE** `/api/chat/conversations/{conversation_id}`

### 成功响应 (204)

无响应体。级联删除该会话下的所有消息和引用记录。
