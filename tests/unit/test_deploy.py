import os
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def import_deploy_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("deploy", Path.cwd() / "deploy.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["deploy"] = module
    spec.loader.exec_module(module)
    return module


# Ensure we import the module fresh for tests
deploy = import_deploy_module()


class TestCheckPythonVersion:
    @pytest.mark.skipif(sys.version_info < (3, 11), reason="Requires Python 3.11+")
    def test_current_python_passes(self):
        deploy.check_python_version()

    @patch("sys.version_info", (3, 10, 12, "final", 0))
    def test_python_310_fails(self):
        with pytest.raises(deploy.DeployError) as exc_info:
            deploy.check_python_version()
        assert "3.10.12" in str(exc_info.value)
        assert ">= 3.11" in str(exc_info.value)

    @patch("sys.version_info", (3, 11, 0, "final", 0))
    def test_python_311_passes(self):
        deploy.check_python_version()


class TestCheckPipAvailable:
    @patch("subprocess.run")
    def test_pip_available(self, mock_run):
        mock_run.return_value.returncode = 0
        config = deploy.DeploymentConfig()
        deploy.check_pip_available(config)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == sys.executable
        assert args[1] == "-m"
        assert args[2] == "pip"

    @patch("subprocess.run")
    def test_pip_missing(self, mock_run):
        mock_run.return_value.returncode = 1
        config = deploy.DeploymentConfig()
        with pytest.raises(deploy.DeployError) as exc_info:
            deploy.check_pip_available(config)
        assert "pip" in str(exc_info.value).lower()


class TestFindAvailablePort:
    def test_finds_default_port_when_free(self):
        port = deploy.find_available_port(start_port=8000, max_attempts=10)
        assert port >= 8000

    def test_finds_next_port_when_8000_occupied(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 8000))
        try:
            port = deploy.find_available_port(start_port=8000, max_attempts=10)
            assert port > 8000
        finally:
            sock.close()

    def test_exhausts_ports_raises(self):
        with pytest.raises(deploy.DeployError):
            # Use a range that is almost certainly fully occupied on any normal system
            deploy.find_available_port(start_port=1, max_attempts=1)


class TestEnsureEnvFile:
    def test_missing_env_generates_template(self, tmp_path):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        with pytest.raises(deploy.DeployError) as exc_info:
            deploy.ensure_env_file(config)
        assert config.env_file.exists()
        content = config.env_file.read_text(encoding="utf-8")
        assert "SECRET_KEY" in content
        assert "LLM_BASE_URL" in content
        assert "EMBEDDING_BASE_URL" in content
        assert ".env" in str(exc_info.value)

    def test_existing_env_skips(self, tmp_path):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        config.env_file.write_text("SECRET_KEY=test\n", encoding="utf-8")
        deploy.ensure_env_file(config)
        assert config.env_file.read_text(encoding="utf-8") == "SECRET_KEY=test\n"


class TestIsServiceRunning:
    def test_service_detected(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.listen(1)
        try:
            assert deploy.is_service_running(port)
        finally:
            sock.close()


class TestStateFile:
    def test_write_and_read(self, tmp_path):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        deploy.write_state_file(config, 12345, 8080)
        assert config.state_file.exists()
        content = config.state_file.read_text(encoding="utf-8")
        assert content.strip() == "12345\n8080"
        result = deploy.read_state_file(config)
        assert result == (12345, 8080)

    def test_read_missing_returns_none(self, tmp_path):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        assert deploy.read_state_file(config) is None

    def test_remove_stale(self, tmp_path):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        deploy.write_state_file(config, 1, 2)
        deploy.remove_state_file(config)
        assert not config.state_file.exists()


class TestIsPidAlive:
    def test_self_alive(self):
        assert deploy.is_pid_alive(os.getpid())

    def test_nonexistent_dead(self):
        assert not deploy.is_pid_alive(99999)


class TestStopService:
    def test_no_state_file_returns_false(self, tmp_path):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        assert deploy.stop_service(config) is False

    def test_stale_pid_cleaned_up(self, tmp_path):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        deploy.write_state_file(config, 99999, 8000)
        assert deploy.stop_service(config) is False
        assert not config.state_file.exists()

    def test_stop_running_process(self, tmp_path):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            deploy.write_state_file(config, proc.pid, 8000)
            assert deploy.stop_service(config) is True
            assert not config.state_file.exists()
            # 确保进程已终止
            proc.poll()
            assert proc.returncode is not None or not deploy.is_pid_alive(proc.pid)
        finally:
            proc.kill()
            proc.wait()


class TestCmdStart:
    @patch.object(deploy, "is_app_running", return_value=True)
    def test_start_guard_when_app_running(self, mock_app):
        config = deploy.DeploymentConfig()
        with pytest.raises(deploy.DeployError) as exc_info:
            deploy.cmd_start(config)
        assert "检测到应用服务已在运行" in str(exc_info.value)


class TestStatusCommand:
    @patch.object(deploy, "read_state_file", return_value=(1234, 8000))
    @patch.object(deploy, "is_pid_alive", return_value=True)
    def test_status_running(self, mock_alive, mock_read, capsys):
        config = deploy.DeploymentConfig()
        result = deploy.cmd_status(config)
        assert result == 0
        captured = capsys.readouterr()
        assert "运行中" in captured.out
        assert "1234" in captured.out
        assert "8000" in captured.out

    @patch.object(deploy, "read_state_file", return_value=None)
    @patch.object(deploy, "is_app_running", return_value=True)
    def test_status_foreground(self, mock_app, mock_read, capsys):
        config = deploy.DeploymentConfig()
        result = deploy.cmd_status(config)
        assert result == 0
        captured = capsys.readouterr()
        assert "前台模式" in captured.out

    @patch.object(deploy, "read_state_file", return_value=None)
    @patch.object(deploy, "is_app_running", return_value=False)
    def test_status_stopped(self, mock_app, mock_read, capsys):
        config = deploy.DeploymentConfig()
        result = deploy.cmd_status(config)
        assert result == 0
        captured = capsys.readouterr()
        assert "未运行" in captured.out


class TestCmdResetPassword:
    @patch.object(deploy, "is_app_running", return_value=False)
    @patch.object(deploy, "stop_service", return_value=True)
    def test_reset_password_confirm_reset_deletes_files(self, mock_stop, mock_running, tmp_path, monkeypatch):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        db_path = config.data_dir / "app.db"
        files_dir = tmp_path / "files"
        config.data_dir.mkdir(parents=True, exist_ok=True)
        db_path.write_text("dummy db", encoding="utf-8")
        files_dir.mkdir(parents=True, exist_ok=True)
        (files_dir / "dummy.txt").write_text("dummy", encoding="utf-8")

        import io
        monkeypatch.setattr("sys.stdin", io.StringIO("RESET\n"))
        result = deploy.cmd_reset_password(config)
        assert result == 0
        assert not db_path.exists()
        assert not files_dir.exists()

    @patch.object(deploy, "is_app_running", return_value=False)
    @patch.object(deploy, "stop_service", return_value=True)
    def test_reset_password_cancel_keeps_files(self, mock_stop, mock_running, tmp_path, monkeypatch):
        config = deploy.DeploymentConfig()
        config.project_root = tmp_path
        db_path = config.data_dir / "app.db"
        files_dir = tmp_path / "files"
        config.data_dir.mkdir(parents=True, exist_ok=True)
        db_path.write_text("dummy db", encoding="utf-8")
        files_dir.mkdir(parents=True, exist_ok=True)

        import io
        monkeypatch.setattr("sys.stdin", io.StringIO("no\n"))
        result = deploy.cmd_reset_password(config)
        assert result == 0
        assert db_path.exists()
        assert files_dir.exists()
