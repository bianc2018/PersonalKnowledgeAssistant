"""
集成测试：验证 deploy.py 的守护进程子命令工作流
start → status → restart → status → stop
"""

import subprocess
import sys
import time
from pathlib import Path

DEPLOY = [sys.executable, str(Path(__file__).resolve().parent.parent.parent / "deploy.py")]
CHECK_TIMEOUT = 10  # 秒
POLL_INTERVAL = 0.2


def _wait_for_status(expected_text: str, timeout: float = CHECK_TIMEOUT) -> bool:
    """轮询 status 直到输出包含 expected_text 或超时。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            DEPLOY + ["status"],
            capture_output=True,
            text=True,
        )
        if expected_text in result.stdout:
            return True
        time.sleep(POLL_INTERVAL)
    return False


def _cleanup():
    """测试结束后确保没有遗留的后台服务。"""
    subprocess.run(DEPLOY + ["stop"], capture_output=True)


def test_daemon_lifecycle():
    try:
        # 1. start
        result = subprocess.run(
            DEPLOY + ["start"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"start failed: {result.stdout}\n{result.stderr}"
        assert "服务已在后台启动" in result.stdout
        assert "http://127.0.0.1:" in result.stdout

        # 2. status - 应该显示运行中
        assert _wait_for_status("运行中"), "status did not report running in time"
        status_result = subprocess.run(DEPLOY + ["status"], capture_output=True, text=True)
        assert "PID" in status_result.stdout
        assert "800" in status_result.stdout  # 端口通常是 8000+

        # 3. restart - 先停止再启动
        restart_result = subprocess.run(
            DEPLOY + ["restart"],
            capture_output=True,
            text=True,
        )
        assert restart_result.returncode == 0, f"restart failed: {restart_result.stdout}\n{restart_result.stderr}"
        assert "服务已在后台启动" in restart_result.stdout

        # 再次确认运行中
        assert _wait_for_status("运行中"), "status did not report running after restart"

        # 4. stop
        stop_result = subprocess.run(
            DEPLOY + ["stop"],
            capture_output=True,
            text=True,
        )
        assert stop_result.returncode == 0, f"stop failed: {stop_result.stdout}\n{stop_result.stderr}"
        assert "已停止" in stop_result.stdout or "服务未在运行" in stop_result.stdout

        # 5. status - 应该显示未运行
        assert _wait_for_status("未运行"), "status did not report stopped in time"
    finally:
        _cleanup()
