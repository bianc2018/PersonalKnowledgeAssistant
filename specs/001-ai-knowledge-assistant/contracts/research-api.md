# 调研 API 契约

> 路径前缀: `/api/research`

---

## 1. 提交调研任务

**POST** `/api/research`

### 请求体

```json
{
  "topic": "低空经济政策分析",
  "scope_description": "重点关注 2024-2025 年国家级和地方级的支持政策"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `topic` | string | 是 | 调研主题，不能为空 |
| `scope_description` | string | 否 | 范围描述，帮助聚焦调研方向 |

### 成功响应 (202)

```json
{
  "data": {
    "id": "task-001",
    "topic": "低空经济政策分析",
    "status": "queued",
    "progress_percent": 0,
    "created_at": "2026-04-05T10:00:00Z"
  }
}
```

---

## 2. 获取任务列表

**GET** `/api/research?offset=0&limit=20`

### 成功响应 (200)

```json
{
  "data": [
    {
      "id": "task-001",
      "topic": "低空经济政策分析",
      "status": "completed",
      "progress_percent": 100,
      "search_source_used": "search_api",
      "created_at": "...",
      "started_at": "...",
      "completed_at": "..."
    },
    {
      "id": "task-002",
      "topic": "人工智能发展趋势",
      "status": "awaiting_input",
      "progress_percent": 35,
      "pending_question": {
        "question": "您希望重点关注哪个细分领域？",
        "options": ["生成式 AI", "机器人", "自动驾驶"]
      },
      "created_at": "..."
    }
  ],
  "pagination": { ... }
}
```

---

## 3. 获取任务详情

**GET** `/api/research/{task_id}`

### 成功响应 (200)

```json
{
  "data": {
    "id": "task-001",
    "topic": "低空经济政策分析",
    "scope_description": "重点关注 2024-2025 年政策",
    "status": "completed",
    "progress_percent": 100,
    "search_source_used": "search_api",
    "sections": [
      {
        "id": "sec-001",
        "section_type": "background",
        "title": "背景概述",
        "content": "低空经济指的是...",
        "order_index": 0
      },
      {
        "id": "sec-002",
        "section_type": "key_points",
        "title": "关键政策观点",
        "content": "...",
        "order_index": 1
      }
    ],
    "citations": [
      {
        "id": "cit-001",
        "source_title": "国家发改委关于低空经济的指导意见",
        "source_url": "https://www.ndrc.gov.cn/...",
        "source_summary": "提出了低空经济发展的五大方向"
      }
    ],
    "saved_item_id": "item-123",
    "created_at": "...",
    "started_at": "...",
    "completed_at": "..."
  }
}
```

---

## 4. 订阅调研进度（SSE）

**GET** `/api/research/{task_id}/events`

### SSE 事件类型

| 事件名 | 说明 |
|--------|------|
| `status` | 任务状态变更：`queued` / `running` / `awaiting_input` / `completed` / `failed` / `degraded` |
| `progress` | 进度更新：`{"percent": 35, "stage": "正在检索网络信息..."}` |
| `chunk` | 阶段性输出摘要：`{"summary": "已完成政策背景检索，发现 5 个关键来源"}` |
| `question` | 用户决策提问：`{"question": "...", "options": [...]}` |
| `report` | 最终报告生成完成（含 sections 摘要） |
| `error` | 错误信息：`{"message": "外部搜索服务暂时不可用"}` |

### 示例 SSE 流

```text
event: status
data: {"status": "running"}

event: progress
data: {"percent": 20, "stage": "正在生成调研大纲..."}

event: progress
data: {"percent": 50, "stage": "正在检索网络信息..."}

event: chunk
data: {"summary": "已检索到 8 篇相关政策文件，其中 3 篇为国家级文件。"}

event: question
data: {"question": "您希望重点关注哪个层面？", "options": ["国家层面", "地方层面", "两者兼顾"]}

event: status
data: {"status": "awaiting_input"}
```

---

## 5. 提交用户决策

**POST** `/api/research/{task_id}/respond`

用于在 `awaiting_input` 状态时恢复调研流程。

### 请求体

```json
{
  "answer": "两者兼顾",
  "custom_input": ""
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `answer` | string | 是 | 选择的答案（若选择的是预定义选项） |
| `custom_input` | string | 否 | 自定义补充输入 |

### 成功响应 (200)

```json
{
  "data": {
    "id": "task-001",
    "status": "running",
    "message": "调研流程已恢复"
  }
}
```

---

## 6. 主题宽泛时的细化引导

当系统判断主题过于宽泛时，SSE 流中会推送 `question` 事件，引导用户聚焦。前端收到后暂停进度动画，展示问题供用户选择或输入。

---

## 7. 保存调研报告到知识库

**POST** `/api/research/{task_id}/save`

### 成功响应 (201)

```json
{
  "data": {
    "item_id": "item-123",
    "title": "调研报告：低空经济政策分析",
    "message": "报告已保存到知识库"
  }
}
```

### 行为说明

- 将调研报告的 Markdown 全文作为新版本的 `content_text` 创建 KnowledgeItem。
- `source_type` 标记为 `research_report`。
- 保存后触发嵌入向量生成和置信度评估。
