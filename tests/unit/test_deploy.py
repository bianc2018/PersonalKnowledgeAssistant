import socket
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
    def test_current_python_passes(self):
        deploy.check_python_version()

    @patch("sys.version_info", (3, 9, 18, "final", 0))
    def test_old_python_fails(self):
        with pytest.raises(deploy.DeployError) as exc_info:
            deploy.check_python_version()
        assert "3.9.18" in str(exc_info.value)
        assert ">= 3.10" in str(exc_info.value)

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
