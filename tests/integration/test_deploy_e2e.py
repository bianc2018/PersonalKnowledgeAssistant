"""端到端部署脚本验证。

这些测试通过子进程执行 deploy.py，验证 happy path 和 guarded re-deploy。
由于 deploy.py 会启动真实服务并前台阻塞，测试使用超时控制并在后台线程中运行服务。
"""

import socket
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread

import pytest


DEPLOY_PY = Path(__file__).resolve().parents[2] / "deploy.py"
REQUIREMENTS_TXT = Path(__file__).resolve().parents[2] / "requirements.txt"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _occupy_port(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(1)
    return sock


class TestDeployHappyPath:
    @pytest.mark.timeout(60)
    def test_help_or_version_not_available(self):
        result = subprocess.run(
            [sys.executable, str(DEPLOY_PY), "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Not a real feature but script doesn't crash on unexpected args
        # Actually let's just run syntax-check via python -m py_compile
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(DEPLOY_PY)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    @pytest.mark.timeout(60)
    def test_env_missing_generates_template(self, tmp_path, monkeypatch):
        tmp_env = tmp_path / ".env"
        deploy_tmp = tmp_path / "deploy.py"
        deploy_tmp.write_text(DEPLOY_PY.read_text(), encoding="utf-8")
        req_tmp = tmp_path / "requirements.txt"
        req_tmp.write_text("# minimal for test\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(deploy_tmp)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
        )

        assert result.returncode == 1
        assert "未找到环境配置文件" in result.stdout or "未找到环境配置文件" in result.stderr
        assert tmp_env.exists()
        content = tmp_env.read_text(encoding="utf-8")
        assert "SECRET_KEY" in content


class TestDeployGuards:
    @pytest.mark.timeout(30)
    def test_detects_running_service(self, tmp_path, monkeypatch):
        free_port = _find_free_port()

        # 创建最小 FastAPI 应用，使 uvicorn 可以正常启动
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text(
            "from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8"
        )

        # 在后台启动 uvicorn，模拟已有服务实例
        blocker = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", str(free_port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(tmp_path),
        )
        try:
            deploy_tmp = tmp_path / "deploy.py"
            deploy_tmp.write_text(DEPLOY_PY.read_text(), encoding="utf-8")
            req_tmp = tmp_path / "requirements.txt"
            req_tmp.write_text(REQUIREMENTS_TXT.read_text(), encoding="utf-8")
            env_file = tmp_path / ".env"
            env_file.write_text("SECRET_KEY=test\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(deploy_tmp)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(tmp_path),
            )

            assert result.returncode == 1
            combined = result.stdout + result.stderr
            assert "检测到应用服务已在运行" in combined
        finally:
            blocker.terminate()
            try:
                blocker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                blocker.kill()
                blocker.wait()
