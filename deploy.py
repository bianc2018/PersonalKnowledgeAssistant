#!/usr/bin/env python3
"""一键部署脚本：自动完成环境检查、依赖安装、配置检查并启动服务。

支持子命令：
  python deploy.py              前台启动（兼容旧行为）
  python deploy.py start        后台守护进程启动
  python deploy.py status       查看运行状态
  python deploy.py restart      强制重启
  python deploy.py stop         停止后台服务
  python deploy.py reset-password  重置密码（删除所有本地数据）
"""

from __future__ import annotations

import errno
import os
import signal
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

    @property
    def state_file(self) -> Path:
        return self.project_root / ".deploy.state"

    @property
    def deploy_log(self) -> Path:
        return self.log_dir / "deploy.log"


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


def is_app_running() -> bool:
    """通过扫描 /proc/*/cmdline 检测是否有本应用（uvicorn src.main:app）正在运行。"""
    project_root = Path(__file__).resolve().parent
    try:
        for proc_dir in Path("/proc").glob("[0-9]*"):
            cmdline_file = proc_dir / "cmdline"
            cwd_link = proc_dir / "cwd"
            try:
                cmdline = cmdline_file.read_text(encoding="utf-8")
                cwd = os.readlink(str(cwd_link))
            except OSError:
                continue
            parts = cmdline.split("\x00")
            has_uvicorn = any("uvicorn" in part for part in parts)
            has_app = any("src.main:app" in part for part in parts)
            same_project = Path(cwd).resolve() == project_root
            if has_uvicorn and has_app and same_project:
                return True
    except OSError:
        pass
    return False


# ---------------------------------------------------------------------------
# Daemon helpers (Unix only, standard library)
# ---------------------------------------------------------------------------

def _daemonize(config: DeploymentConfig) -> None:
    """Double-fork 守护进程化，并重定向 stdout/stderr 到日志文件。"""
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid > 0:
        os._exit(0)

    os.setsid()
    os.chdir(str(config.project_root))
    os.umask(0o022)

    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid > 0:
        os._exit(0)

    # 重定向标准流
    stdin_fd = os.open(os.devnull, os.O_RDONLY)
    log_fd = os.open(str(config.deploy_log), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(stdin_fd, sys.stdin.fileno())
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(stdin_fd)
    if log_fd > 2:
        os.close(log_fd)

    # 关闭其余非标准文件描述符，避免泄漏给 uvicorn 子进程
    try:
        max_fd = os.sysconf("SC_OPEN_MAX")
    except ValueError:
        max_fd = 1024
    os.closerange(3, max_fd)


def write_state_file(config: DeploymentConfig, pid: int, port: int) -> None:
    fd = os.open(str(config.state_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"{pid}\n{port}\n")


def read_state_file(config: DeploymentConfig) -> tuple[int, int] | None:
    if not config.state_file.exists():
        return None
    try:
        lines = config.state_file.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) >= 2:
            return int(lines[0]), int(lines[1])
    except (ValueError, OSError):
        pass
    return None


def remove_state_file(config: DeploymentConfig) -> None:
    try:
        config.state_file.unlink(missing_ok=True)
    except OSError:
        pass


def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        raise
    # 如果是僵尸进程（已死但未被收尸），尝试无阻塞 wait 后视为已死
    try:
        waited_pid, _ = os.waitpid(pid, os.WNOHANG)
        if waited_pid == pid:
            return False
    except OSError:
        pass
    return True


def start_daemon(config: DeploymentConfig, port: int) -> None:
    """在前置检查完毕后启动后台守护进程。"""
    ensure_directories(config)
    config.deploy_log.parent.mkdir(parents=True, exist_ok=True)

    # 确保没有存活的后台实例
    state = read_state_file(config)
    if state:
        pid, _ = state
        if is_pid_alive(pid):
            raise DeployError(
                step="启动服务",
                reason=f"后台服务已在运行 (PID {pid})",
                suggestion="如需重启，请运行: python deploy.py restart",
            )
        else:
            remove_state_file(config)

    # 方案：由前台进程 fork 出 daemon 进程；daemon 进程写 state_file 后 exec uvicorn。
    # 前台进程等待 state_file 出现并确认 PID 存活后输出成功信息。
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid > 0:
        # 父进程：等待 daemon 写入 state_file
        for _ in range(30):  # 最多等待 3 秒
            time.sleep(0.1)
            state = read_state_file(config)
            if state and is_pid_alive(state[0]):
                _, actual_port = state
                print("服务已在后台启动")
                print(f"访问地址: http://127.0.0.1:{actual_port}")
                print(f"日志文件: {config.deploy_log}")
                print("查看状态: python deploy.py status")
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(0)
        raise DeployError(
            step="启动服务",
            reason="后台服务启动失败，子进程未正常写入状态文件",
            suggestion=f"请检查日志文件排查原因: {config.deploy_log}",
        )

    # 子进程：daemonize 后写入 state_file，然后 exec uvicorn
    _daemonize(config)
    write_state_file(config, os.getpid(), port)
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
    os.execvp(cmd[0], cmd)


def stop_service(config: DeploymentConfig) -> bool:
    """停止后台服务，返回是否成功。"""
    state = read_state_file(config)
    if not state:
        return False
    pid, _ = state
    if not is_pid_alive(pid):
        remove_state_file(config)
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass

    for _ in range(50):  # 最多等待 5 秒
        if not is_pid_alive(pid):
            remove_state_file(config)
            return True
        time.sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass

    for _ in range(20):  # 再等待 2 秒
        if not is_pid_alive(pid):
            remove_state_file(config)
            return True
        time.sleep(0.1)

    remove_state_file(config)
    return False


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_start(config: DeploymentConfig) -> int:
    if is_app_running():
        _raise_if_app_running()

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

        def _check_port() -> None:
            if is_service_running(actual_port):
                _raise_if_running(actual_port)

        run_step(4, total_steps, "检查端口", _check_port)
        run_step(5, total_steps, "启动服务", lambda: None)
        start_daemon(config, actual_port)
        return 0
    except DeployError as exc:
        _print_error(exc)
        return 1


def cmd_status(config: DeploymentConfig) -> int:
    state = read_state_file(config)
    if state:
        pid, port = state
        if is_pid_alive(pid):
            url = f"http://127.0.0.1:{port}"
            print(f"状态: 运行中")
            print(f"PID : {pid}")
            print(f"端口: {port}")
            print(f"地址: {url}")
            return 0
        else:
            remove_state_file(config)
    # 同时检查前台进程
    if is_app_running():
        print("状态: 运行中（前台模式）")
        print("提示: 前台进程无法通过 status 获取端口，请查看启动时输出的地址")
        return 0
    print("状态: 未运行")
    print("提示: 运行 python deploy.py start 后台启动，或 python deploy.py 前台启动")
    return 0


def cmd_stop(config: DeploymentConfig) -> int:
    if stop_service(config):
        print("服务已停止")
        return 0
    if is_app_running():
        print("检测到前台模式运行的服务，请在其终端按 Ctrl+C 停止")
        return 1
    print("服务未在运行")
    return 1


def cmd_restart(config: DeploymentConfig) -> int:
    state = read_state_file(config)
    if state:
        pid, _ = state
        if is_pid_alive(pid):
            print(f"正在停止后台服务 (PID {pid})...")
            if not stop_service(config):
                _print_error(DeployError(
                    step="重启服务",
                    reason="无法终止旧进程",
                    suggestion="请手动 kill 该进程后再试",
                ))
                return 1
    return cmd_start(config)


def cmd_reset_password(config: DeploymentConfig) -> int:
    db_path = config.data_dir / "app.db"
    files_dir = config.project_root / "files"
    print("\033[91m⚠️  警告：此操作将永久删除所有本地数据！\033[0m\n")
    print("以下文件/目录将被删除：")
    print(f"  - {db_path}")
    print(f"  - {files_dir}")
    print("\n此操作不可恢复。")
    try:
        confirmation = input("请输入 RESET 以确认删除，或按 Ctrl+C 取消：\n> ").strip()
    except EOFError:
        print("\n操作已取消，未做任何更改。")
        return 0
    if confirmation != "RESET":
        print("操作已取消，未做任何更改。")
        return 0

    if is_app_running():
        print("正在停止服务...")
        stop_service(config)

    if db_path.exists():
        db_path.unlink()
        print(f"已删除 {db_path}")
    else:
        print(f"数据库文件已不存在，跳过: {db_path}")

    if files_dir.exists():
        import shutil
        shutil.rmtree(files_dir)
        print(f"已删除 {files_dir}")
    else:
        print(f"附件目录已不存在，跳过: {files_dir}")

    print("\033[92m✅ 重置完成。请重新运行启动脚本并完成初始化。\033[0m")
    return 0


# ---------------------------------------------------------------------------
# Foreground main (legacy compatibility)
# ---------------------------------------------------------------------------

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


def main_foreground(config: DeploymentConfig) -> int:
    total_steps = 5
    try:
        run_step(1, total_steps, "检查环境", lambda: (
            check_python_version(),
            check_pip_available(config),
        ))
        run_step(2, total_steps, "安装依赖", lambda: install_dependencies(config))
        run_step(3, total_steps, "检查配置", lambda: ensure_env_file(config))

        ensure_directories(config)

        actual_port = config.target_port

        def _check_port_and_process() -> None:
            if is_app_running():
                _raise_if_app_running()
            nonlocal actual_port
            actual_port = find_available_port(config.target_port)
            if is_service_running(actual_port):
                _raise_if_running(actual_port)

        run_step(4, total_steps, "检查端口与进程冲突", _check_port_and_process)
        run_step(5, total_steps, "启动服务", lambda: None)
        return start_service(config, actual_port)
    except DeployError as exc:
        _print_error(exc)
        return 1


def _print_error(error: DeployError) -> None:
    print()
    print(f"错误: {error.reason}")
    print(f"建议: {error.suggestion}")


def _print_usage() -> None:
    print("Usage:")
    print("  python deploy.py              前台启动服务")
    print("  python deploy.py start        后台守护进程启动")
    print("  python deploy.py status       查看服务运行状态")
    print("  python deploy.py restart      强制重启后台服务")
    print("  python deploy.py stop         停止后台服务")
    print("  python deploy.py reset-password  重置密码并清空数据")
    print("  python deploy.py --help       显示此帮助信息")


def main() -> int:
    config = DeploymentConfig()
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("-h", "--help"):
            _print_usage()
            return 0
        if arg == "start":
            return cmd_start(config)
        if arg == "status":
            return cmd_status(config)
        if arg == "restart":
            return cmd_restart(config)
        if arg == "stop":
            return cmd_stop(config)
        if arg == "reset-password":
            return cmd_reset_password(config)
        print(f"错误: 未识别的参数: {arg}")
        print("提示: 运行 python deploy.py --help 查看用法")
        return 1
    return main_foreground(config)


def _raise_if_running(port: int) -> None:
    raise DeployError(
        step="检查端口与进程冲突",
        reason=f"检测到应用服务已在运行\n端口 {port} 当前被占用。",
        suggestion="请先停止现有进程，然后再次运行 python deploy.py\n提示: 在终端中按下 Ctrl+C 即可停止前台运行的服务",
    )


def _raise_if_app_running() -> None:
    raise DeployError(
        step="检查端口与进程冲突",
        reason="检测到应用服务已在运行。",
        suggestion="请先停止现有进程，然后再次运行 python deploy.py。\n提示: 在终端中按下 Ctrl+C 即可停止前台运行的服务",
    )


if __name__ == "__main__":
    sys.exit(main())
