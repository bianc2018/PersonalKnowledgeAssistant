#!/usr/bin/env python3
"""一键部署脚本：自动完成环境检查、依赖安装、配置检查并启动服务。"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class DeploymentConfig:
    """部署运行时配置。"""

    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    python_executable: str = field(default_factory=lambda: sys.executable)
    target_port: int = 8000
    max_retries: int = 3
    retry_delay_seconds: int = 2

    @property
    def pip_command(self) -> list[str]:
        return [self.python_executable, "-m", "pip"]

    @property
    def requirements_file(self) -> Path:
        return self.project_root / "requirements.txt"

    @property
    def env_file(self) -> Path:
        return self.project_root / ".env"

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def log_dir(self) -> Path:
        return self.project_root / "logs"


class DeployError(Exception):
    """部署步骤失败时的自定义异常。"""

    def __init__(self, step: str, reason: str, suggestion: str) -> None:
        self.step = step
        self.reason = reason
        self.suggestion = suggestion
        super().__init__(f"{step}: {reason}")


def _print_step(step_number: int, total: int, name: str, status: str) -> None:
    width = 36
    dots = "." * max(1, width - len(name))
    print(f"[{step_number}/{total}] {name} {dots} [{status}]")


def run_step(
    step_number: int,
    total: int,
    name: str,
    action: Callable[[], None],
) -> None:
    try:
        action()
        _print_step(step_number, total, name, "OK")
    except DeployError:
        _print_step(step_number, total, name, "FAIL")
        raise
    except Exception as exc:
        _print_step(step_number, total, name, "FAIL")
        raise DeployError(
            step=name,
            reason=str(exc),
            suggestion="请查看上方错误详情，修正后重新运行脚本。",
        ) from exc


def check_python_version() -> None:
    version = sys.version_info
    current = f"{version[0]}.{version[1]}.{version[2]}"
    if version[0] < 3 or (version[0] == 3 and version[1] < 11):
        raise DeployError(
            step="检查环境",
            reason=f"Python 版本不符合要求\n当前版本: {current}\n所需版本: >= 3.11",
            suggestion="请安装 Python 3.11 或更高版本后重试。",
        )


def check_pip_available(config: DeploymentConfig) -> None:
    result = subprocess.run(
        config.pip_command + ["--version"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DeployError(
            step="检查环境",
            reason="未找到可用的 pip 命令",
            suggestion="请确保 Python 安装完整，并已安装 pip 包管理器。",
        )


def install_dependencies(config: DeploymentConfig) -> None:
    if not config.requirements_file.exists():
        raise DeployError(
            step="安装依赖",
            reason=f"未找到依赖文件: {config.requirements_file}",
            suggestion="请确认项目已正确克隆，requirements.txt 位于项目根目录。",
        )

    last_error = ""
    for attempt in range(1, config.max_retries + 1):
        result = subprocess.run(
            config.pip_command + ["install", "-r", str(config.requirements_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        last_error = result.stderr.strip().splitlines()[-1] if result.stderr else "未知错误"
        if attempt < config.max_retries:
            time.sleep(config.retry_delay_seconds)

    raise DeployError(
        step="安装依赖",
        reason=f"依赖安装失败，已重试 {config.max_retries} 次\n最后一条错误信息:\n  {last_error}",
        suggestion="请检查网络连接，或稍后重试。如果使用了代理，请确保代理配置正确。",
    )


def _env_template() -> str:
    return (
        "# AI 知识管理助手 - 环境配置模板\n"
        "# 请根据实际情况填写以下字段\n\n"
        "# 数据库路径（可选，默认使用项目根目录下的 data/app.db）\n"
        "# DATABASE_URL=./data/app.db\n\n"
        "# 会话密钥（生产环境必须修改）\n"
        "SECRET_KEY=change-me-in-production\n\n"
        "# 文件上传存储目录\n"
        "# FILES_DIR=./files\n\n"
        "# 日志存储目录\n"
        "# LOG_DIR=./logs\n\n"
        "# LLM 接口配置\n"
        "LLM_BASE_URL=\n"
        "LLM_API_KEY=\n"
        "LLM_MODEL=\n"
        "# LLM_ENABLE_SEARCH=false\n\n"
        "# Embedding 接口配置\n"
        "EMBEDDING_BASE_URL=\n"
        "EMBEDDING_API_KEY=\n"
        "EMBEDDING_MODEL=\n\n"
        "# 搜索 API 配置（可选）\n"
        "# SEARCH_PROVIDER=\n"
        "# SEARCH_API_KEY=\n"
        "# SEARCH_BASE_URL=\n"
    )


def ensure_env_file(config: DeploymentConfig) -> None:
    if config.env_file.exists():
        return
    config.env_file.write_text(_env_template(), encoding="utf-8")
    raise DeployError(
        step="检查配置",
        reason=f"未找到环境配置文件 ({config.env_file.name})",
        suggestion=f"已自动生成模板文件: {config.env_file.name}\n请打开该文件，填写必要的配置项后再次运行 python deploy.py",
    )


def ensure_directories(config: DeploymentConfig) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.log_dir.mkdir(parents=True, exist_ok=True)


def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    for offset in range(max_attempts):
        port = start_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("", port))
                return port
            except OSError:
                continue
    raise DeployError(
        step="检查端口与进程冲突",
        reason=f"无法找到可用端口（已尝试 {start_port} ~ {start_port + max_attempts - 1}）",
        suggestion="请手动释放一个端口，或通过环境变量调整默认端口。",
    )


def is_service_running(port: int) -> bool:
    """通过 /proc/net/tcp 检测端口是否处于监听状态，避免被 proxychains 等 LD_PRELOAD 代理劫持。"""
    hex_port = f"{port:04X}"
    for proc_file in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(proc_file, "r", encoding="utf-8") as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    local_address = parts[1]
                    state = parts[3]
                    if state == "0A" and local_address.endswith(f":{hex_port}"):
                        return True
        except (OSError, StopIteration):
            continue
    return False


def start_service(config: DeploymentConfig, port: int) -> int:
    cmd = [
        config.python_executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    print(f"\n服务已启动，访问地址: http://127.0.0.1:{port}")
    print("按 Ctrl+C 停止服务\n")
    result = subprocess.run(cmd)
    return result.returncode


def _print_error(error: DeployError) -> None:
    print()
    print(f"错误: {error.reason}")
    print(f"建议: {error.suggestion}")


def main() -> int:
    config = DeploymentConfig()
    total_steps = 5

    try:
        run_step(1, total_steps, "检查环境", lambda: (
            check_python_version(),
            check_pip_available(config),
        ))

        run_step(2, total_steps, "安装依赖", lambda: install_dependencies(config))
        run_step(3, total_steps, "检查配置", lambda: ensure_env_file(config))

        ensure_directories(config)

        actual_port = find_available_port(config.target_port)

        run_step(
            4,
            total_steps,
            "检查端口与进程冲突",
            lambda: (
                _raise_if_running(actual_port)
                if is_service_running(actual_port)
                else None
            ),
        )

        run_step(5, total_steps, "启动服务", lambda: None)
        return start_service(config, actual_port)

    except DeployError as exc:
        _print_error(exc)
        return 1


def _raise_if_running(port: int) -> None:
    raise DeployError(
        step="检查端口与进程冲突",
        reason=f"检测到应用服务已在运行\n端口 {port} 当前被占用。",
        suggestion="请先停止现有进程，然后再次运行 python deploy.py\n提示: 在终端中按下 Ctrl+C 即可停止前台运行的服务",
    )


if __name__ == "__main__":
    sys.exit(main())
