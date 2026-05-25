#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoFlow 로컬 에이전트 v1.0.0
WebSocket + HTTP 폴링 하이브리드 에이전트

사용법:
    # 토큰으로 연결 (웹 UI에서 토큰 복사)
    python ws_agent.py --token <YOUR_TOKEN>

    # 이메일/비밀번호로 연결
    python ws_agent.py --email user@example.com --password mypass

    # 서버 지정
    python ws_agent.py --token <TOKEN> --server http://myserver:8000
"""

__version__ = "1.0.0"

import sys
import os
import subprocess

# stdout 버퍼링 비활성화
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


# ── 의존성 자동 설치 ──────────────────────────────────────────────────

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

ALL_PACKAGES = {**AGENT_PACKAGES, **RUNTIME_PACKAGES}


def ensure_dependencies(packages: dict):
    """누락된 패키지를 자동으로 설치"""
    missing = []
    for import_name, pip_name in packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        print(f"[설치] 필요 패키지 설치 중: {', '.join(missing)}")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", *missing],
                stdout=subprocess.DEVNULL,
            )
            print(f"[설치] 패키지 설치 완료!")
        except subprocess.CalledProcessError as e:
            print(f"[설치] 패키지 설치 실패: {e}")
            print(f"[설치] 수동 설치: pip install {' '.join(missing)}")
            sys.exit(1)


# 에이전트 실행에 필요한 패키지 먼저 설치
ensure_dependencies(AGENT_PACKAGES)

# 이제 안전하게 import
import argparse
import json
import time
import threading
import tempfile
import uuid
import re
from datetime import datetime
from typing import Optional, Dict, Any

import requests
import websocket


# ── AutoFlowAgent 클래스 ──────────────────────────────────────────────

class AutoFlowAgent:
    """AutoFlow 로컬 실행 에이전트"""

    def __init__(self, server_url: str, token: str, poll_interval: int = 3):
        self.server_url = server_url.rstrip("/")
        self.api_base = f"{self.server_url}/api/execution"
        self.token = token
        self.auth_headers = {"Authorization": f"Bearer {token}"}
        self.agent_id = str(uuid.uuid4())[:8]
        self.poll_interval = poll_interval

        self.ws: Optional[websocket.WebSocketApp] = None
        self.running = True
        self.current_process: Optional[subprocess.Popen] = None
        self.reconnect_delay = 1  # 지수 백오프 초기값

    def log(self, message: str, prefix: str = "에이전트"):
        """타임스탬프 로그 출력"""
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{prefix}] {message}")

    # ── 인증 ──────────────────────────────────────────────────────

    @classmethod
    def from_credentials(cls, server_url: str, email: str, password: str, **kwargs):
        """이메일/비밀번호로 로그인하여 에이전트 생성"""
        url = f"{server_url.rstrip('/')}/api/auth/login"
        try:
            resp = requests.post(url, json={"email": email, "password": password}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            token = data.get("access_token")
            if not token:
                print(f"[오류] 로그인 응답에 토큰이 없습니다: {data}")
                sys.exit(1)
            user_name = data.get("user", {}).get("name", email)
            print(f"[인증] 로그인 성공: {user_name}")
            return cls(server_url, token, **kwargs)
        except requests.RequestException as e:
            print(f"[오류] 로그인 실패: {e}")
            sys.exit(1)

    # ── HTTP 폴링 (실행 명령 수신) ────────────────────────────────

    def poll_commands(self):
        """대기 중인 명령을 주기적으로 폴링"""
        while self.running:
            try:
                r = requests.get(
                    f"{self.api_base}/pending-commands",
                    params={"agent_id": self.agent_id},
                    headers=self.auth_headers,
                    timeout=10,
                )
                if r.status_code == 200:
                    commands = r.json().get("commands", [])
                    for cmd in commands:
                        self.execute_command(cmd)
                elif r.status_code == 401:
                    self.log("인증 토큰이 만료되었습니다. 새 토큰으로 재시작해주세요.", "오류")
                    self.running = False
                    return
            except requests.RequestException:
                pass  # 네트워크 오류는 조용히 무시 (재시도)
            time.sleep(self.poll_interval)

    def execute_command(self, command: Dict[str, Any]):
        """수신된 명령 실행"""
        cmd_id = command.get("command_id", "")
        cmd_type = command.get("command_type", "")
        workflow_name = command.get("workflow_name", "automation")
        blocks = command.get("blocks", [])

        self.log(f"명령 수신: type={cmd_type}, blocks={len(blocks)}", "실행")

        if cmd_type == "run":
            self.run_workflow(cmd_id, blocks, workflow_name)
        elif cmd_type == "stop":
            self.stop_workflow(cmd_id)

    def run_workflow(self, command_id: str, blocks: list, workflow_name: str):
        """워크플로우 실행: 코드 생성 → 의존성 확인 → 실행"""
        # 1. 코드 생성
        self.log("코드 생성 요청 중...", "실행")
        self.send_ws_log("코드 생성 중...")

        try:
            r = requests.post(
                f"{self.api_base}/generate-code",
                json={"blocks": blocks, "workflow_name": workflow_name},
                headers=self.auth_headers,
                timeout=30,
            )
            if r.status_code != 200:
                self.log(f"코드 생성 실패: HTTP {r.status_code}", "오류")
                self.report_result(command_id, False, error="코드 생성 실패")
                return
            code = r.json().get("code")
            if not code:
                self.report_result(command_id, False, error="생성된 코드 없음")
                return
        except Exception as e:
            self.report_result(command_id, False, error=str(e))
            return

        # 2. 생성된 코드의 의존성 확인 및 설치
        self.ensure_script_dependencies(code)

        # 3. 임시 파일에 저장 후 실행
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            script_path = f.name

        self.log(f"스크립트 실행 시작", "실행")
        self.send_ws_log("자동화 실행 중...")

        try:
            self.current_process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            stdout, stderr = self.current_process.communicate(timeout=300)

            if self.current_process.returncode == 0:
                self.log("실행 완료!", "실행")
                self.report_result(command_id, True, data={"output": stdout[-500:] if stdout else ""})
                self.send_ws_msg({"type": "execution_complete", "success": True})
            else:
                error_msg = stderr[:500] if stderr else "알 수 없는 오류"
                self.log(f"실행 실패: {error_msg[:100]}", "오류")
                self.report_result(command_id, False, error=error_msg)
                self.send_ws_msg({"type": "execution_error", "error": error_msg[:200]})

        except subprocess.TimeoutExpired:
            if self.current_process:
                self.current_process.kill()
            self.report_result(command_id, False, error="실행 시간 초과 (5분)")
        except Exception as e:
            self.report_result(command_id, False, error=str(e))
        finally:
            self.current_process = None
            try:
                os.unlink(script_path)
            except OSError:
                pass

    def ensure_script_dependencies(self, code: str):
        """생성된 스크립트의 import문을 스캔하여 누락 패키지 설치"""
        # import문에서 패키지 이름 추출
        import_pattern = re.compile(
            r"^\s*(?:from\s+([\w.]+)|import\s+([\w.]+))", re.MULTILINE
        )
        found_modules = set()
        for match in import_pattern.finditer(code):
            module = (match.group(1) or match.group(2)).split(".")[0]
            found_modules.add(module)

        # 알려진 패키지 매핑
        known_packages = {
            "selenium": "selenium",
            "webdriver_manager": "webdriver-manager",
            "pandas": "pandas",
            "openpyxl": "openpyxl",
            "pyautogui": "pyautogui",
            "pyperclip": "pyperclip",
            "requests": "requests",
            "bs4": "beautifulsoup4",
            "PIL": "pillow",
            "lxml": "lxml",
            "cssselect": "cssselect",
        }

        missing = []
        for module in found_modules:
            if module in known_packages:
                try:
                    __import__(module)
                except ImportError:
                    missing.append(known_packages[module])

        if missing:
            self.log(f"스크립트 의존성 설치: {', '.join(missing)}", "설치")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--quiet", *missing],
                    stdout=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                self.log(f"일부 패키지 설치 실패: {missing}", "경고")

    def stop_workflow(self, command_id: str):
        """실행 중인 워크플로우 중지"""
        if self.current_process:
            self.current_process.terminate()
            self.log("워크플로우 중지됨", "실행")
            self.report_result(command_id, True, data={"message": "중지됨"})
        else:
            self.report_result(command_id, True, data={"message": "실행 중인 작업 없음"})

    def report_result(self, command_id: str, success: bool,
                      data: Optional[Dict] = None, error: Optional[str] = None):
        """실행 결과를 서버에 보고"""
        try:
            requests.post(
                f"{self.api_base}/report-result",
                params={"command_id": command_id, "success": success, "error": error},
                headers=self.auth_headers,
                json={"data": data} if data else None,
                timeout=10,
            )
        except requests.RequestException:
            self.log("결과 보고 실패", "경고")

    # ── WebSocket (프론트엔드 상태 연동) ──────────────────────────

    def send_ws_msg(self, msg: dict):
        """WebSocket으로 메시지 전송"""
        if self.ws:
            try:
                self.ws.send(json.dumps(msg))
            except Exception:
                pass

    def send_ws_log(self, log_msg: str):
        """실행 로그를 WebSocket으로 전달"""
        self.send_ws_msg({"type": "execution_log", "log": log_msg})

    def _on_open(self, ws):
        self.ws = ws
        self.reconnect_delay = 1  # 재연결 성공 시 백오프 초기화
        self.log("WebSocket 연결 성공!")

        # ping 루프
        def ping_loop():
            while self.running:
                try:
                    ws.send(json.dumps({"type": "ping"}))
                    time.sleep(30)
                except Exception:
                    break

        threading.Thread(target=ping_loop, daemon=True).start()

        # HTTP 폴링 시작
        threading.Thread(target=self.poll_commands, daemon=True).start()

        self.log("명령 대기 중... (Ctrl+C로 종료)")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            if msg_type not in ("pong",):
                self.log(f"WS 수신: {data}")
        except json.JSONDecodeError:
            pass

    def _on_error(self, ws, error):
        self.log(f"WebSocket 오류: {error}", "경고")

    def _on_close(self, ws, code, reason):
        self.ws = None
        if self.running:
            self.log(f"WebSocket 연결 끊김. {self.reconnect_delay}초 후 재연결...", "경고")

    # ── 메인 실행 (자동 재연결) ───────────────────────────────────

    def run(self):
        """에이전트 메인 루프 (자동 재연결 포함)"""
        self._print_banner()

        # 런타임 의존성 사전 설치
        self.log("런타임 의존성 확인 중...")
        ensure_dependencies(RUNTIME_PACKAGES)
        self.log("의존성 준비 완료!")

        ws_url = f"{self.server_url.replace('http://', 'ws://').replace('https://', 'wss://')}/ws/agent?token={self.token}"

        while self.running:
            try:
                self.log("WebSocket 연결 중...")
                ws_app = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                ws_app.run_forever()
            except KeyboardInterrupt:
                self.log("사용자에 의해 종료됨")
                self.running = False
                break
            except Exception as e:
                self.log(f"연결 오류: {e}", "오류")

            if self.running:
                time.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 30)  # 지수 백오프, 최대 30초

        if self.current_process:
            self.current_process.terminate()
        self.log("에이전트 종료됨")

    def _print_banner(self):
        print(f"""
╔═══════════════════════════════════════════════════════╗
║         AutoFlow 로컬 에이전트 v{__version__}               ║
╠═══════════════════════════════════════════════════════╣
║  에이전트 ID : {self.agent_id:<39} ║
║  서버 URL   : {self.server_url:<39} ║
╚═══════════════════════════════════════════════════════╝
        """)


# ── CLI 진입점 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AutoFlow 로컬 에이전트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 토큰으로 연결 (웹 UI에서 복사)
  %(prog)s --token eyJhbGci...

  # 이메일/비밀번호로 연결
  %(prog)s --email user@example.com --password mypass

  # 서버 지정
  %(prog)s --token <TOKEN> --server http://myserver:8000
        """,
    )
    parser.add_argument("--token", help="인증 토큰 (웹 UI에서 복사)")
    parser.add_argument("--email", help="로그인 이메일")
    parser.add_argument("--password", help="로그인 비밀번호")
    parser.add_argument("--server", default="http://localhost:8000", help="서버 URL (기본: http://localhost:8000)")
    parser.add_argument("--poll-interval", type=int, default=3, help="명령 폴링 간격 초 (기본: 3)")
    parser.add_argument("--version", action="version", version=f"AutoFlow Agent v{__version__}")

    args = parser.parse_args()

    # 인증 방식 결정
    if args.token:
        agent = AutoFlowAgent(args.server, args.token, poll_interval=args.poll_interval)
    elif args.email and args.password:
        agent = AutoFlowAgent.from_credentials(
            args.server, args.email, args.password, poll_interval=args.poll_interval
        )
    else:
        print("[오류] --token 또는 --email/--password를 지정해주세요.")
        print()
        print("  토큰 연결:  python ws_agent.py --token <YOUR_TOKEN>")
        print("  로그인 연결: python ws_agent.py --email user@example.com --password mypass")
        print()
        print("토큰은 AutoFlow 웹 UI의 마이페이지 > 설정에서 복사할 수 있습니다.")
        sys.exit(1)

    try:
        agent.run()
    except KeyboardInterrupt:
        print("\n[에이전트] 종료됨")


if __name__ == "__main__":
    main()
