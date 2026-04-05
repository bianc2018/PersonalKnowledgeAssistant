# Quickstart: AI 知识管理助手

> 生成日期: 2026-04-05 | 关联 Plan: [plan.md](./plan.md) | 关联 Spec: [spec.md](./spec.md)

---

## 环境要求

- **Python**: 3.11 或更高版本
- **操作系统**: Linux / macOS / Windows
- **可选依赖**: Tesseract OCR（如需图片 OCR 功能）

---

## 1. 安装

### 1.1 克隆仓库并创建虚拟环境

```bash
git clone <repo-url>
cd PersonalKnowledgeAssistant
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 1.2 安装依赖

```bash
pip install -r requirements.txt
```

**核心依赖**（已包含在 `requirements.txt` 中）:
- `fastapi`
- `uvicorn[standard]`
- `sqlite-vec`
- `aiosqlite`
- `httpx`
- `pydantic-settings`
- `cryptography`
- `argon2-cffi`
- `pytest`, `pytest-asyncio`

### 1.3 可选：安装 Tesseract OCR

- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`
- **Windows**: 从 [GitHub tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) 下载安装包

---

## 2. 启动服务

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问:
- **Web 应用**: http://localhost:8000
- **API 文档 (Swagger UI)**: http://localhost:8000/docs
- **API 文档 (ReDoc)**: http://localhost:8000/redoc

---

## 3. 首次初始化

1. 打开浏览器访问 http://localhost:8000
2. 首次使用会进入初始化页面，设置单用户登录密码（≥8 位，需包含字母和数字）
3. 初始化完成后，使用密码登录即可开始使用

---

## 4. 基础配置

### 4.1 LLM 与搜索配置

进入系统设置页面（或通过 API）配置以下信息：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| LLM Base URL | 兼容 OpenAI API 的端点地址 | `https://api.openai.com/v1` |
| LLM API Key | 服务商提供的 API 密钥 | `sk-...` |
| LLM Model | 模型名称 | `gpt-4o` |
| Embedding 配置 | 向量模型端点 | 同 LLM 或独立端点 |
| 搜索 API | Tavily / SerpAPI 等 | `tvly-...` |

### 4.2 隐私策略开关

- **允许发送完整知识内容**：默认关闭，开启后外部 AI 可调阅完整知识用于深度分析
- **允许外部网络搜索**：默认开启，关闭后调研功能受限
- **允许上传运行日志**：默认关闭

---

## 5. 常用操作验证

### 5.1 添加一条知识

```bash
curl -X POST http://localhost:8000/api/knowledge \
  -H "Authorization: Bearer <你的token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试知识",
    "content": "这是一条用于测试的知识条目内容。",
    "source_type": "text",
    "tags": ["测试"]
  }'
```

### 5.2 对话查询

```bash
curl -X POST http://localhost:8000/api/chat/conversations/conv-001/messages \
  -H "Authorization: Bearer <你的token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "测试知识是什么？"}'
```

### 5.3 提交调研任务

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Authorization: Bearer <你的token>" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "人工智能发展趋势",
    "scope_description": "重点关注生成式 AI 在 2024-2025 年的商业化进展"
  }'
```

然后订阅 SSE 查看进度：

```bash
curl -N http://localhost:8000/api/research/task-001/events \
  -H "Authorization: Bearer <你的token>"
```

---

## 6. 运行测试

```bash
pytest tests/
```

仅运行单元测试：

```bash
pytest tests/unit/
```

仅运行集成测试：

```bash
pytest tests/integration/
```

---

## 7. 数据备份与恢复

### 7.1 导出知识库

```bash
curl -X POST http://localhost:8000/api/system/export \
  -H "Authorization: Bearer <你的token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "你的密码"}' \
  --output backup.zip
```

### 7.2 导入知识库

```bash
curl -X POST http://localhost:8000/api/system/import \
  -H "Authorization: Bearer <你的token>" \
  -F "file=@backup.zip"
```

---

## 8. 常见问题

**Q: 启动时提示 sqlite-vec 扩展加载失败？**  
A: 确保安装了 `sqlite-vec` 包并且 Python 有权限加载本地 C 扩展。某些 Linux 发行版可能需要安装 `build-essential`。

**Q: 如何切换为完全离线模式？**  
A: 配置本地 LLM 端点（如 Ollama 或 vLLM）和本地 Embedding 模型，关闭外部搜索开关即可。

**Q: 忘记密码怎么办？**  
A: 本地加密数据不可恢复。请通过系统重置功能清空数据后重新初始化，然后导入已有备份。
