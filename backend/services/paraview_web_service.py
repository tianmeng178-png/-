from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse, urlunparse


def _load_system_config() -> Dict:
    config_path = Path(__file__).resolve().parents[2] / "config" / "system_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _build_ws_url(base_url: str) -> str:
    if base_url.startswith("ws://") or base_url.startswith("wss://"):
        parsed = urlparse(base_url)
        path = parsed.path.rstrip("/")
        if not path.endswith("/ws"):
            path = f"{path}/ws" if path else "/ws"
        return urlunparse(parsed._replace(path=path))

    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    path = parsed.path.rstrip("/")
    if not path.endswith("/ws"):
        path = f"{path}/ws" if path else "/ws"
    return urlunparse(parsed._replace(scheme=scheme, path=path))


def _extract_host(base_url: str) -> str:
    try:
        parsed = urlparse(base_url)
        if parsed.hostname:
            return parsed.hostname
    except Exception:
        pass
    return "localhost"


def _windows_path_to_wsl(path: Path) -> str:
    """Convert a Windows path to WSL path (e.g. D:\\foo\\bar -> /mnt/d/foo/bar)."""
    posix = path.as_posix()
    if path.drive:
        return f"/mnt/{path.drive[0].lower()}{posix[2:]}"
    return posix


class ParaViewWebService:
    """ParaViewWeb 进程管理（WSL）"""

    def __init__(self) -> None:
        config = _load_system_config()
        openfoam_cfg = config.get("openfoam", {})
        pv_cfg = config.get("paraview_web", {})

        self.enabled = pv_cfg.get("enabled", True)
        self.use_wsl = pv_cfg.get("use_wsl", True)
        self.wsl_distro = pv_cfg.get("wsl_distro", openfoam_cfg.get("wsl_distro", "Ubuntu-24.04"))
        self.openfoam_path = openfoam_cfg.get("openfoam_path", "/opt/openfoam11")
        self.host = pv_cfg.get("host", "0.0.0.0")
        self.base_url = pv_cfg.get("base_url", "http://localhost")
        port_range = pv_cfg.get("port_range", [9000, 9100])
        self.port_range = (int(port_range[0]), int(port_range[1]))

        self._backend_checked = False
        self._backend = None  # "paraview_web" or None

        self._processes: Dict[str, subprocess.Popen] = {}
        self._ports: Dict[str, int] = {}
        self._urls: Dict[str, str] = {}
        self._log_files: Dict[str, object] = {}  # simulation_id -> open file (pvweb stdout)

    def _is_port_available(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                return False
        return True

    def _can_connect(self, host: str, port: int, timeout: float = 0.5) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def _wait_for_port(self, host: str, port: int, process: subprocess.Popen, timeout: float = 8.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self._can_connect(host, port):
                return True
            if process.poll() is not None:
                return False
            time.sleep(0.2)
        return self._can_connect(host, port)

    def _get_wsl_ip(self) -> Optional[str]:
        cmd = ["wsl", "-d", self.wsl_distro, "bash", "-c", "hostname -I | awk '{print $1}'"]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if result.returncode == 0:
                ip = result.stdout.decode("utf-8", "ignore").strip()
                return ip or None
        except Exception:
            pass
        return None

    def _select_port(self) -> Optional[int]:
        for port in range(self.port_range[0], self.port_range[1] + 1):
            if port in self._ports.values():
                continue
            if self._is_port_available(port):
                return port
        return None

    def _ensure_backend(self) -> bool:
        if self._backend_checked:
            return self._backend is not None

        self._backend_checked = True
        if not self.use_wsl:
            self._backend = None
            return False

        check_cmd = (
            "pvpython - <<'PY'\n"
            "import importlib.util\n"
            "def has(mod):\n"
            "    return importlib.util.find_spec(mod) is not None\n"
            "print('paraview_web' if has('paraview.web.serve') else 'none')\n"
            "PY"
        )
        cmd = ["wsl", "-d", self.wsl_distro, "bash", "-c", check_cmd]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            stdout_text = result.stdout.decode("utf-8", "ignore").strip() if result.stdout else ""
            if result.returncode == 0 and stdout_text == "paraview_web":
                self._backend = "paraview_web"
                return True
        except Exception:
            pass

        self._backend = None
        return False

    def start(self, simulation_id: str, case_dir: str, case_file: Optional[str] = None) -> Dict[str, str]:
        if not self.enabled:
            return {"status": "disabled"}

        if simulation_id in self._processes:
            url = self._urls.get(simulation_id, "")
            return {
                "status": "running",
                "url": url,
                "ws_url": _build_ws_url(url) if url else "",
                "port": str(self._ports.get(simulation_id, "")),
            }

        if not self._ensure_backend():
            return {
                "status": "unavailable",
                "message": "ParaViewWeb 模块不可用，请在 WSL 中安装 paraview.web.serve",
            }

        port = self._select_port()
        if port is None:
            return {"status": "error", "message": "ParaViewWeb 端口已耗尽"}

        case_path = Path(case_file) if case_file else Path(case_dir) / "case.foam"
        try:
            case_path.touch(exist_ok=True)
        except Exception:
            pass

        wsl_case = case_path.as_posix()
        if case_path.drive:
            drive = case_path.drive[0].lower()
            wsl_case = f"/mnt/{drive}{case_path.as_posix()[2:]}"

        wsl_case = _shell_quote(wsl_case)
        # Use custom pvweb_server (registers ParaViewWebPublishImageDelivery for viewport.image.push.*)
        pvweb_script = Path(__file__).resolve().parent / "pvweb_server.py"
        wsl_script = _shell_quote(_windows_path_to_wsl(pvweb_script))
        cmd = (
            f"source {self.openfoam_path}/etc/bashrc && "
            f"pvpython {wsl_script} --data {wsl_case} --host {self.host} --port {port}"
        )
        wsl_cmd = ["wsl", "-d", self.wsl_distro, "bash", "-c", cmd]

        log_dir = Path(__file__).resolve().parents[2] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"pvweb_{simulation_id}.log"
        log_file = open(log_path, "w", encoding="utf-8")
        self._log_files[simulation_id] = log_file

        try:
            process = subprocess.Popen(
                wsl_cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        except Exception as e:
            try:
                log_file.close()
                self._log_files.pop(simulation_id, None)
            except Exception:
                pass
            return {"status": "error", "message": f"ParaViewWeb 启动失败: {e}"}

        url = f"{self.base_url}:{port}"
        host = _extract_host(url)
        ready = self._wait_for_port(host, port, process, timeout=8.0)

        if not ready:
            wsl_ip = self._get_wsl_ip()
            if wsl_ip and self._wait_for_port(wsl_ip, port, process, timeout=3.0):
                url = f"http://{wsl_ip}:{port}"
                ready = True

        if not ready:
            error_output = ""
            try:
                log_file.flush()
                log_file.seek(0)
                error_output = log_file.read()
            except Exception:
                pass
            try:
                log_file.close()
                self._log_files.pop(simulation_id, None)
            except Exception:
                pass
            return {
                "status": "error",
                "message": "ParaViewWeb 未能在端口上就绪",
                "details": error_output.strip() or None,
                "log_path": str(log_path),
            }

        ws_url = _build_ws_url(url)
        self._processes[simulation_id] = process
        self._ports[simulation_id] = port
        self._urls[simulation_id] = url

        return {
            "status": "running",
            "url": url,
            "ws_url": ws_url,
            "port": str(port),
            "log_path": str(log_path),
        }

    def stop(self, simulation_id: str) -> None:
        process = self._processes.pop(simulation_id, None)
        self._ports.pop(simulation_id, None)
        self._urls.pop(simulation_id, None)
        log_file = self._log_files.pop(simulation_id, None)
        if log_file is not None:
            try:
                log_file.close()
            except Exception:
                pass

        if process is None:
            return
        try:
            process.terminate()
        except Exception:
            pass

    def get_info(self, simulation_id: str) -> Dict[str, str]:
        if simulation_id in self._urls:
            url = self._urls.get(simulation_id, "")
            log_dir = Path(__file__).resolve().parents[2] / "logs"
            log_path = log_dir / f"pvweb_{simulation_id}.log"
            return {
                "status": "running",
                "url": url,
                "ws_url": _build_ws_url(url) if url else "",
                "port": str(self._ports.get(simulation_id, "")),
                "log_path": str(log_path),
            }
        if not self.enabled:
            return {"status": "disabled"}
        if not self._ensure_backend():
            return {
                "status": "unavailable",
                "message": "ParaViewWeb 模块不可用，请在 WSL 中安装 paraview.web.serve",
            }
        return {"status": "idle"}
