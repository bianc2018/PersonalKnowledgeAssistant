# Code Review: 002-one-click-deployment (Scope Change CR-001)

> Feature: 002-one-click-deployment | Date: 2026-04-11
> Files reviewed: 3 | Tasks covered: 19/19
> Status: APPROVED WITH CONDITIONS

## Summary

| Dimension | CRITICAL | HIGH | MEDIUM | LOW | Total |
|-----------|:--------:|:----:|:------:|:---:|:-----:|
| Quality | 0 | 2 | 3 | 1 | 6 |
| Security | 0 | 1 | 1 | 0 | 2 |
| Patterns | 0 | 0 | 0 | 1 | 1 |
| Tests | 0 | 0 | 2 | 1 | 3 |
| **Total** | **0** | **3** | **6** | **3** | **12** |

**Recommendation:** FIX HIGH FINDINGS FIRST, THEN PROCEED TO VERIFY

---

## Positive Highlights

1. **Zero-dependency daemonization.** The double-fork approach using only `os.fork()` and `os.setsid()` keeps the script fully self-contained and avoids pulling in heavy process-management libraries — exactly matching the project constraint.
2. **Clean state-file lifecycle management.** Stale PID detection (`is_pid_alive`) with zombie reaping via `waitpid(WNOHANG)` is a thoughtful touch that prevents "ghost" state files from blocking restarts.
3. **Backward compatibility preserved.** The original foreground behavior (`python deploy.py`) is untouched, and new subcommands are clearly separated from the legacy path.

---

## Findings

### REV-001 [HIGH] Quality — Spec divergence: Python version check allows 3.10, but spec requires 3.11+

| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | HIGH |
| **File** | `deploy.py:103-111` |
| **Rule** | Must match FR-002 and research.md requirements |

**What:** `check_python_version()` rejects versions `< 3.10`, but `research.md` and `spec.md` explicitly require Python **3.11+**. If the runtime is 3.10, the deployment script passes but the FastAPI application may fail later with 3.11-specific syntax or library assumptions.

**Suggested fix:**
```python
def check_python_version() -> None:
    version = sys.version_info
    current = f"{version[0]}.{version[1]}.{version[2]}"
    if version[0] < 3 or (version[0] == 3 and version[1] < 11):
        raise DeployError(
            step="检查环境",
            reason=f"Python 版本不符合要求\n当前版本: {current}\n所需版本: >= 3.11",
            suggestion="请安装 Python 3.11 或更高版本后重试。",
        )
```

Also update the unit test (`TestCheckPythonVersion.test_python_311_passes`) to add a boundary test for `(3, 10, 0, "final", 0)` expecting failure.

---

### REV-002 [HIGH] Security — `_daemonize` sets `os.umask(0)`, causing world-writable `.deploy.state`

| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | HIGH |
| **File** | `deploy.py:259-285` |
| **Rule** | Daemon processes should not create world-writable state files |

**What:** `_daemonize` calls `os.umask(0)`. After this, `write_state_file()` creates `.deploy.state` with mode `0o666` (world-writable). On a shared server or multi-user environment, any local user can overwrite the PID file, causing a denial-of-service (fake PID) or potentially tricking `deploy.py stop` into killing an arbitrary process.

**Suggested fix:** Remove `os.umask(0)` entirely, or set a safe umask such as `0o022`:
```python
def _daemonize(config: DeploymentConfig) -> None:
    ...
    os.setsid()
    os.chdir(str(config.project_root))
    os.umask(0o022)   # safe default instead of 0
    ...
```

---

### REV-003 [MEDIUM] Quality — `cmd_restart` calls `stop_service` twice with misleading UX

| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | MEDIUM |
| **File** | `deploy.py:492-507` |
| **Rule** | Avoid redundant retry logic on operations that already implement full escalation |

**What:** `stop_service()` already performs SIGTERM → 5s wait → SIGKILL → 2s wait. `cmd_restart` retries `stop_service()` a second time and prints "尝试强制结束...", which is confusing because the first call already attempted SIGKILL.

**Suggested fix:** Remove the second `stop_service()` call and improve the message:
```python
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
```

---

### REV-004 [MEDIUM] Quality — `is_app_running()` can false-positive on unrelated uvicorn projects

| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | MEDIUM |
| **File** | `deploy.py:236-252` |
| **Rule** | Process collision detection should avoid cross-project false positives |

**What:** `is_app_running()` scans `/proc/*/cmdline` for any process containing both `"uvicorn"` and `"src.main:app"`. If a developer is running another FastAPI project that happens to use the same module path, `deploy.py` will incorrectly refuse to start.

**Suggested fix:** Augment the check with `cwd` (current working directory) verification:
```python
def is_app_running() -> bool:
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
            same_project = Path(cwd).resolve() == Path(__file__).resolve().parent
            if has_uvicorn and has_app and same_project:
                return True
    except OSError:
        pass
    return False
```

---

### REV-005 [MEDIUM] Security — `.deploy.state` file has no explicit permissions and is stored in project root

| Field | Value |
|-------|-------|
| **Dimension** | Security |
| **Severity** | MEDIUM |
| **File** | `deploy.py:288-290` |
| **Rule** | State files should have restrictive permissions and be tamper-aware |

**What:** `write_state_file()` relies on default file permissions and stores the file in the project root. Even after fixing the umask issue, the file remains in a visible location without any integrity check.

**Suggested fix:** Use `os.open` with explicit `0o600` permissions when creating the file:
```python
def write_state_file(config: DeploymentConfig, pid: int, port: int) -> None:
    fd = os.open(str(config.state_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"{pid}\n{port}\n")
```

---

### REV-006 [MEDIUM] Quality — `_daemonize` leaks non-standard file descriptors to uvicorn child

| Field | Value |
|-------|-------|
| **Dimension** | Quality |
| **Severity** | MEDIUM |
| **File** | `deploy.py:259-285` |
| **Rule** | Daemon routines should close all FDs > 2 before exec |

**What:** Python files, sockets, or pipe FDs opened by the parent shell/test runner remain accessible to the `uvicorn` child because `os.execvp` preserves open descriptors. This can cause unexpected file locks or socket binding issues.

**Suggested fix:** Close fds > 2 before exec (best-effort, with a safe upper bound):
```python
def _daemonize(config: DeploymentConfig) -> None:
    ...
    # after stdio redirection
    try:
        max_fd = os.sysconf("SC_OPEN_MAX")
    except ValueError:
        max_fd = 1024
    os.closerange(3, max_fd)
    ...
```

---

### REV-007 [MEDIUM] Tests — Missing unit test for `cmd_start` guard when `is_app_running()` is True

| Field | Value |
|-------|-------|
| **Dimension** | Tests |
| **Severity** | MEDIUM |
| **File** | `tests/unit/test_deploy.py` |
| **Rule** | Every guard on the critical path needs a unit test |

**What:** There is no unit test verifying that `cmd_start` raises / returns error code 1 when `is_app_running()` detects a running instance. This guard is critical for FR-010.

**Suggested fix:**
```python
class TestCmdStart:
    @patch.object(deploy, "is_app_running", return_value=True)
    def test_start_guard_when_app_running(self, mock_app, capsys):
        config = deploy.DeploymentConfig()
        result = deploy.cmd_start(config)
        assert result == 1
        captured = capsys.readouterr()
        assert "检测到应用服务已在运行" in captured.out
```

---

### REV-008 [LOW] Patterns — Unused import `shutil` in `deploy.py`

| Field | Value |
|-------|-------|
| **Dimension** | Patterns / Dead Code |
| **Severity** | LOW |
| **File** | `deploy.py:17` |
| **Rule** | Remove unused imports |

**What:** `import shutil` is present but never referenced anywhere in the file.

---

### REV-009 [LOW] Tests — `test_daemon_lifecycle` does not verify actual HTTP health

| Field | Value |
|-------|-------|
| **Dimension** | Tests |
| **Severity** | LOW |
| **File** | `tests/integration/test_deploy_daemon.py:36` |
| **Rule** | Daemon integration test should confirm the service is actually serving traffic |

**What:** The test asserts that `status` reports "运行中", but it does not perform an HTTP request to the bound port to confirm uvicorn successfully loaded the application.

**Suggested fix:** Add a lightweight HTTP probe at the end of the start/restart assertions:
```python
import urllib.request

# after start/restart success
url = None
for line in result.stdout.splitlines():
    if line.startswith("访问地址:"):
        url = line.split(": ", 1)[1]
        break
assert url
with urllib.request.urlopen(url, timeout=5) as resp:
    assert resp.status == 200
```

---

## Required Before Verification (Phase 7)

- [ ] **REV-001**: Fix Python version check to require 3.11+ and update unit tests.
- [ ] **REV-002**: Fix `os.umask(0)` in `_daemonize` to a safe value (e.g., `0o022`).
- [ ] **REV-003**: Remove redundant `stop_service()` retry in `cmd_restart`.

## Suggested Improvements (Optional)

- [ ] **REV-004**: Reduce false positives in `is_app_running()` by checking `cwd`.
- [ ] **REV-005**: Restrict `.deploy.state` file permissions to `0o600`.
- [ ] **REV-006**: Close non-std file descriptors before `os.execvp`.
- [ ] **REV-007**: Add unit test for `cmd_start` guard.
- [ ] **REV-008**: Remove unused `import shutil`.
- [ ] **REV-009**: Add HTTP health check to daemon integration test.

---

## Test Coverage Gap Analysis

| Requirement | Test Status | Gap |
|------------|:----------:|-----|
| FR-001 (single CLI) | ✅ | `test_daemon_lifecycle` covers `start`, `status`, `restart` |
| FR-002 (Python 3.11+) | ⚠️ | Boundary test for 3.10 is missing; currently passes 3.10 incorrectly |
| FR-003 (DB init delegated) | N/A | Not tested at deploy script level (handled by app) |
| FR-004 (foreground start) | ✅ | Existing integration tests |
| FR-005 (error messages) | ✅ | `TestEnsureEnvFile`, `TestFindAvailablePort` |
| FR-006 (re-deploy safe) | ✅ | Existing `test_deploy_e2e.py` |
| FR-012 (daemon `start`) | ✅ | `test_daemon_lifecycle` |
| FR-013 (`status` subcommand) | ✅ | `test_daemon_lifecycle` + `TestStatusCommand` |
| FR-014 (`restart` subcommand) | ✅ | `test_daemon_lifecycle` |
| FR-015 (PID file mgmt) | ✅ | `TestStateFile`, `TestIsPidAlive`, `TestStopService` |
| FR-016 (log redirection) | ⚠️ | No assertion verifying `logs/deploy.log` receives uvicorn output |

---

## Review Checklist

- [x] Quality dimension reviewed (SOLID, DRY, complexity)
- [x] Security dimension reviewed (attack surfaces from plan.md)
- [x] Pattern consistency reviewed (stdlib-only constraints satisfied)
- [x] Test coverage reviewed against spec.md requirements
- [ ] All HIGH findings addressed *(pending user confirmation)*
- [ ] No CRITICAL security vulnerabilities in new code
