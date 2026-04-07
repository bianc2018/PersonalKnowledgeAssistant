# Quickstart: 一键部署功能

> 关联 Spec: [spec.md](./spec.md) | 关联 Plan: [plan.md](./plan.md)

---

## 首次部署

### 1. 克隆代码仓库

```bash
git clone <仓库地址>
cd PersonalKnowledgeAssistant
```

### 2. 执行一键部署

```bash
python deploy.py
```

### 3. 补全配置文件（若提示）

如果系统提示 `.env` 不存在并已生成模板，请按以下步骤操作：

1. 打开项目根目录下的 `.env` 文件
2. 至少填写以下必填项：
   - `SECRET_KEY`（建议修改为随机字符串）
   - `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`（若需使用 AI 功能）
3. 保存文件后再次执行：

```bash
python deploy.py
```

### 4. 访问服务

部署成功后，终端会显示访问地址：

```text
服务已启动，访问地址: http://127.0.0.1:8000
```

在浏览器中打开该地址即可使用。

---

## 更新后重新部署

当代码有更新时，执行同一命令即可：

```bash
git pull origin main
python deploy.py
```

**注意事项**:
- 若服务仍在运行，脚本会提示你先手动停止现有进程
- 停止方式：在运行服务的终端中按下 `Ctrl+C`
- 重新部署不会删除已有的数据库和用户数据

---

## 故障排查

### 问题 1：Python 版本过低

**现象**:
```text
错误: Python 版本不符合要求
当前版本: 3.10.x
所需版本: >= 3.11
```

**解决方案**:
安装 Python 3.11 或更高版本，并确保 `python` 命令指向新版本：

```bash
# Ubuntu/Debian 示例
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip
```

---

### 问题 2：端口被占用且检测到进程冲突

**现象**:
```text
错误: 检测到应用服务已在运行
端口 8000 当前被占用。
```

**解决方案**:
1. 若你在另一个终端中运行了同一项目，按 `Ctrl+C` 停止它
2. 重新执行 `python deploy.py`

---

### 问题 3：依赖安装因网络中断失败

**现象**:
```text
错误: 依赖安装失败，已重试 3 次
```

**解决方案**:
1. 检查网络连接是否正常
2. 若使用代理，配置 pip 代理环境变量：

```bash
export HTTPS_PROXY=http://your-proxy:port
python deploy.py
```

3. 或等待网络恢复后重试

---

### 问题 4：动态分配的端口如何知道

**现象**: 终端显示非 8000 的端口，如 `http://127.0.0.1:8001`

**说明**: 这是正常行为。当 8000 被其他程序占用时，脚本会自动寻找下一个可用端口并在输出中明确告知你。

---

## 测试验证

### 独立测试 1：首次一键启动

在干净的机器或容器环境中执行：

```bash
docker run --rm -it -v $(pwd):/app -w /app python:3.11 bash
# 容器内
python deploy.py
```

验证服务能在 5 分钟内成功启动并可通过 `http://127.0.0.1:8000` 访问。

### 独立测试 2：更新后重新部署

在已部署环境中拉取新代码后再次执行 `python deploy.py`（先停止旧服务），验证数据不丢失。

### 独立测试 3：部署失败反馈

故意删除 `.env` 文件或占用 8000 端口，执行 `python deploy.py`，验证错误信息是否明确且可指导修复。
