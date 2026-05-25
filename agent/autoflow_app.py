#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoFlow 로컬 에이전트 - GUI 버전
더블클릭으로 실행 가능한 데스크톱 앱

지원 OS: macOS, Windows, Linux
"""

__version__ = "1.0.0"

import sys
import os
import subprocess
import threading
import json
import time
import re
import uuid
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any

# stdout 버퍼링 비활성화
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


# ── 의존성 자동 설치 ──────────────────────────────────────────────

AGENT_PACKAGES = {
    "requests": "requests",
    "websocket": "websocket-client",
}

RUNTIME_PACKAGES = {
    "selenium": "selenium",
    "webdriver_manager": "webdriver-manager",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
}


def ensure_dependencies(packages: dict, status_callback=None):
    """누락된 패키지를 자동으로 설치"""
    missing = []
    for import_name, pip_name in packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        msg = f"패키지 설치 중: {', '.join(missing)}"
        if status_callback:
            status_callback(msg)
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", *missing],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if status_callback:
                status_callback("패키지 설치 완료!")
        except subprocess.CalledProcessError:
            if status_callback:
                status_callback(f"패키지 설치 실패. 수동 설치: pip install {' '.join(missing)}")


# 에이전트 필수 패키지 설치
ensure_dependencies(AGENT_PACKAGES)

import requests
import websocket

# tkinter import (PyInstaller 번들 시에도 포함됨)
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


# ── 에이전트 코어 로직 ────────────────────────────────────────────

class AgentCore:
    """에이전트 핵심 로직 (GUI 독립)"""

    def __init__(self, server_url: str, token: str, log_callback=None, status_callback=None):
        self.server_url = server_url.rstrip("/")
        self.api_base = f"{self.server_url}/api/execution"
        self.token = token
        self.auth_headers = {"Authorization": f"Bearer {token}"}
        self.agent_id = str(uuid.uuid4())[:8]
        self.log_cb = log_callback or print
        self.status_cb = status_callback or (lambda *a: None)

        self.ws: Optional[websocket.WebSocketApp] = None
        self.running = False
        self.connected = False
        self.current_process: Optional[subprocess.Popen] = None
        self.reconnect_delay = 1

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_cb(f"[{ts}] {message}")

    def start(self):
        """에이전트 시작 (별도 스레드에서 호출)"""
        self.running = True
        self.status_cb("connecting")

        # 런타임 의존성 설치
        self.log("런타임 의존성 확인 중...")
        ensure_dependencies(RUNTIME_PACKAGES, lambda msg: self.log(msg))
        self.log("의존성 준비 완료!")

        ws_url = (
            self.server_url
            .replace("http://", "ws://")
            .replace("https://", "wss://")
            + f"/ws/agent?token={self.token}"
        )

        while self.running:
            try:
                self.log("서버 연결 중...")
                ws_app = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                ws_app.run_forever()
            except Exception as e:
                self.log(f"연결 오류: {e}")

            if self.running:
                self.status_cb("reconnecting")
                self.log(f"{self.reconnect_delay}초 후 재연결...")
                time.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 30)

        self.status_cb("disconnected")

    def stop(self):
        """에이전트 중지"""
        self.running = False
        self.connected = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.current_process:
            self.current_process.terminate()
        self.status_cb("disconnected")

    # ── WebSocket 핸들러 ──

    def _on_open(self, ws):
        self.ws = ws
        self.connected = True
        self.reconnect_delay = 1
        self.status_cb("connected")
        self.log("서버 연결 성공!")

        # ping 루프
        def ping():
            while self.running and self.connected:
                try:
                    ws.send(json.dumps({"type": "ping"}))
                    time.sleep(30)
                except Exception:
                    break
        threading.Thread(target=ping, daemon=True).start()

        # HTTP 폴링 시작
        threading.Thread(target=self._poll_commands, daemon=True).start()

        self.log("명령 대기 중...")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get("type") not in ("pong",):
                self.log(f"메시지: {data.get('type', 'unknown')}")
        except json.JSONDecodeError:
            pass

    def _on_error(self, ws, error):
        pass  # 재연결 시 로그 중복 방지

    def _on_close(self, ws, code, reason):
        self.ws = None
        self.connected = False
        if self.running:
            self.status_cb("reconnecting")

    # ── HTTP 폴링 ──

    def _poll_commands(self):
        while self.running and self.connected:
            try:
                r = requests.get(
                    f"{self.api_base}/pending-commands",
                    params={"agent_id": self.agent_id},
                    headers=self.auth_headers,
                    timeout=10,
                )
                if r.status_code == 200:
                    for cmd in r.json().get("commands", []):
                        self._execute_command(cmd)
                elif r.status_code == 401:
                    self.log("토큰이 만료되었습니다. 새 토큰으로 재연결해주세요.")
                    self.stop()
                    return
            except requests.RequestException:
                pass
            time.sleep(3)

    def _execute_command(self, command: dict):
        cmd_id = command.get("command_id", "")
        cmd_type = command.get("command_type", "")
        blocks = command.get("blocks", [])
        workflow_name = command.get("workflow_name", "automation")

        self.log(f"명령 수신: {cmd_type} ({len(blocks)}개 블록)")

        if cmd_type == "run":
            self._run_workflow(cmd_id, blocks, workflow_name)
        elif cmd_type == "stop":
            if self.current_process:
                self.current_process.terminate()
                self._report_result(cmd_id, True, data={"message": "중지됨"})

    def _run_workflow(self, command_id: str, blocks: list, workflow_name: str):
        self.log("코드 생성 중...")
        self._send_ws({"type": "execution_log", "log": "코드 생성 중..."})

        try:
            r = requests.post(
                f"{self.api_base}/generate-code",
                json={"blocks": blocks, "workflow_name": workflow_name},
                headers=self.auth_headers,
                timeout=30,
            )
            if r.status_code != 200:
                self._report_result(command_id, False, error="코드 생성 실패")
                return
            code = r.json().get("code")
            if not code:
                self._report_result(command_id, False, error="생성된 코드 없음")
                return
        except Exception as e:
            self._report_result(command_id, False, error=str(e))
            return

        # 스크립트 의존성 확인
        self._ensure_script_deps(code)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            script_path = f.name

        self.log("자동화 실행 중...")
        self._send_ws({"type": "execution_log", "log": "자동화 실행 중..."})

        try:
            self.current_process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8",
            )
            stdout, stderr = self.current_process.communicate(timeout=300)

            if self.current_process.returncode == 0:
                self.log("실행 완료!")
                self._report_result(command_id, True, data={"output": stdout[-500:] if stdout else ""})
                self._send_ws({"type": "execution_complete", "success": True})
            else:
                err = stderr[:500] if stderr else "알 수 없는 오류"
                self.log(f"실행 실패: {err[:80]}")
                self._report_result(command_id, False, error=err)
                self._send_ws({"type": "execution_error", "error": err[:200]})
        except subprocess.TimeoutExpired:
            if self.current_process:
                self.current_process.kill()
            self._report_result(command_id, False, error="시간 초과 (5분)")
        except Exception as e:
            self._report_result(command_id, False, error=str(e))
        finally:
            self.current_process = None
            try:
                os.unlink(script_path)
            except OSError:
                pass

    def _ensure_script_deps(self, code: str):
        pattern = re.compile(r"^\s*(?:from\s+([\w.]+)|import\s+([\w.]+))", re.MULTILINE)
        modules = {(m.group(1) or m.group(2)).split(".")[0] for m in pattern.finditer(code)}
        known = {
            "selenium": "selenium", "webdriver_manager": "webdriver-manager",
            "pandas": "pandas", "openpyxl": "openpyxl",
            "pyautogui": "pyautogui", "pyperclip": "pyperclip",
            "bs4": "beautifulsoup4", "PIL": "pillow",
        }
        missing = []
        for mod in modules:
            if mod in known:
                try:
                    __import__(mod)
                except ImportError:
                    missing.append(known[mod])
        if missing:
            self.log(f"패키지 설치: {', '.join(missing)}")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--quiet", *missing],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                pass

    def _report_result(self, command_id: str, success: bool,
                       data: Optional[Dict] = None, error: Optional[str] = None):
        try:
            requests.post(
                f"{self.api_base}/report-result",
                params={"command_id": command_id, "success": success, "error": error},
                headers=self.auth_headers,
                json={"data": data} if data else None,
                timeout=10,
            )
        except requests.RequestException:
            pass

    def _send_ws(self, msg: dict):
        if self.ws:
            try:
                self.ws.send(json.dumps(msg))
            except Exception:
                pass


# ── GUI 앱 ────────────────────────────────────────────────────────

class AutoFlowApp:
    """AutoFlow 에이전트 GUI"""

    # 설정 파일 경로
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".autoflow")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "agent_config.json")

    def __init__(self):
        self.agent: Optional[AgentCore] = None
        self.agent_thread: Optional[threading.Thread] = None

        self.root = tk.Tk()
        self.root.title(f"AutoFlow Agent v{__version__}")
        self.root.geometry("480x560")
        self.root.minsize(400, 480)
        self.root.resizable(True, True)

        # 시스템별 스타일
        if sys.platform == "darwin":
            self.root.configure(bg="#f5f5f7")
        elif sys.platform == "win32":
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        self._build_ui()
        self._load_config()

        self.root.protocol("WM_DELETE_CLOSE", self._on_close)

    def _build_ui(self):
        style = ttk.Style()
        style.configure("Title.TLabel", font=("", 14, "bold"))
        style.configure("Status.TLabel", font=("", 11))
        style.configure("Connect.TButton", font=("", 11))

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # ── 헤더 ──
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(header, text="AutoFlow Agent", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text=f"v{__version__}", foreground="gray").pack(side=tk.LEFT, padx=(8, 0))

        # ── 상태 표시 ──
        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X, pady=(0, 15))

        self.status_indicator = tk.Canvas(status_frame, width=12, height=12, highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 8))
        self.status_dot = self.status_indicator.create_oval(2, 2, 10, 10, fill="#999", outline="")

        self.status_label = ttk.Label(status_frame, text="미연결", style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT)

        # ── 연결 설정 ──
        settings_frame = ttk.LabelFrame(main, text="연결 설정", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # 서버 URL
        ttk.Label(settings_frame, text="서버 URL").pack(anchor=tk.W)
        self.server_var = tk.StringVar(value="http://localhost:8000")
        self.server_entry = ttk.Entry(settings_frame, textvariable=self.server_var)
        self.server_entry.pack(fill=tk.X, pady=(2, 8))

        # 인증 방식 탭
        auth_notebook = ttk.Notebook(settings_frame)
        auth_notebook.pack(fill=tk.X, pady=(0, 5))

        # 토큰 탭
        token_frame = ttk.Frame(auth_notebook, padding=8)
        auth_notebook.add(token_frame, text="토큰")
        ttk.Label(token_frame, text="연결 토큰 (웹 UI에서 복사)").pack(anchor=tk.W)
        self.token_var = tk.StringVar()
        self.token_entry = ttk.Entry(token_frame, textvariable=self.token_var, show="*")
        self.token_entry.pack(fill=tk.X, pady=(2, 0))

        # 이메일 탭
        login_frame = ttk.Frame(auth_notebook, padding=8)
        auth_notebook.add(login_frame, text="이메일 로그인")
        ttk.Label(login_frame, text="이메일").pack(anchor=tk.W)
        self.email_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.email_var).pack(fill=tk.X, pady=(2, 6))
        ttk.Label(login_frame, text="비밀번호").pack(anchor=tk.W)
        self.password_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.password_var, show="*").pack(fill=tk.X, pady=(2, 0))

        self.auth_notebook = auth_notebook

        # ── 연결/해제 버튼 ──
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(5, 10))

        self.connect_btn = ttk.Button(btn_frame, text="연결", command=self._toggle_connection, style="Connect.TButton")
        self.connect_btn.pack(fill=tk.X, ipady=4)

        # ── 로그 ──
        log_frame = ttk.LabelFrame(main, text="로그", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=10, font=("Courier", 10),
            state=tk.DISABLED, wrap=tk.WORD,
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _toggle_connection(self):
        if self.agent and self.agent.running:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        server = self.server_var.get().strip()
        if not server:
            messagebox.showwarning("입력 오류", "서버 URL을 입력해주세요.")
            return

        # 인증 방식 확인
        current_tab = self.auth_notebook.index(self.auth_notebook.select())
        token = None

        if current_tab == 0:  # 토큰
            token = self.token_var.get().strip()
            if not token:
                messagebox.showwarning("입력 오류", "연결 토큰을 입력해주세요.")
                return
        else:  # 이메일 로그인
            email = self.email_var.get().strip()
            password = self.password_var.get().strip()
            if not email or not password:
                messagebox.showwarning("입력 오류", "이메일과 비밀번호를 입력해주세요.")
                return
            # 로그인 시도
            self._add_log("로그인 중...")
            try:
                resp = requests.post(
                    f"{server}/api/auth/login",
                    json={"email": email, "password": password},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                token = data.get("access_token")
                if not token:
                    messagebox.showerror("로그인 실패", "서버 응답에 토큰이 없습니다.")
                    return
                user_name = data.get("user", {}).get("name", email)
                self._add_log(f"로그인 성공: {user_name}")
            except requests.RequestException as e:
                messagebox.showerror("로그인 실패", f"서버 연결 실패:\n{e}")
                return

        # 설정 저장
        self._save_config()

        # 에이전트 시작
        self.agent = AgentCore(
            server_url=server,
            token=token,
            log_callback=self._add_log,
            status_callback=self._update_status,
        )

        self.connect_btn.config(text="연결 해제")
        self.server_entry.config(state=tk.DISABLED)

        self.agent_thread = threading.Thread(target=self.agent.start, daemon=True)
        self.agent_thread.start()

    def _disconnect(self):
        if self.agent:
            self.agent.stop()
            self.agent = None
        self.connect_btn.config(text="연결")
        self.server_entry.config(state=tk.NORMAL)
        self._add_log("연결 해제됨")

    def _update_status(self, status: str):
        """상태 업데이트 (스레드 안전)"""
        def update():
            colors = {
                "connected": ("#22c55e", "연결됨"),
                "connecting": ("#f59e0b", "연결 중..."),
                "reconnecting": ("#f59e0b", "재연결 중..."),
                "disconnected": ("#999999", "미연결"),
            }
            color, text = colors.get(status, ("#999999", status))
            self.status_indicator.itemconfig(self.status_dot, fill=color)
            self.status_label.config(text=text)
        self.root.after(0, update)

    def _add_log(self, message: str):
        """로그 추가 (스레드 안전)"""
        def append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, append)

    def _save_config(self):
        """설정 저장"""
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        config = {
            "server_url": self.server_var.get().strip(),
            "email": self.email_var.get().strip(),
        }
        # 토큰과 비밀번호는 저장하지 않음 (보안)
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _load_config(self):
        """저장된 설정 불러오기"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if config.get("server_url"):
                    self.server_var.set(config["server_url"])
                if config.get("email"):
                    self.email_var.set(config["email"])
            except (OSError, json.JSONDecodeError):
                pass

    def _on_close(self):
        """앱 종료"""
        if self.agent:
            self.agent.stop()
        self.root.destroy()

    def run(self):
        """앱 실행"""
        self.root.mainloop()


# ── 진입점 ────────────────────────────────────────────────────────

def main():
    # CLI 인자가 있으면 커맨드라인 모드
    if len(sys.argv) > 1 and any(a.startswith("--") for a in sys.argv[1:]):
        # ws_agent.py의 CLI 모드 사용
        from ws_agent import main as cli_main
        cli_main()
    else:
        # GUI 모드
        app = AutoFlowApp()
        app.run()


if __name__ == "__main__":
    main()
