#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoFlow 로컬 에이전트
서버에서 실행 명령을 받아 로컬에서 자동화를 실행합니다.

사용법:
    python autoflow_agent.py --server http://localhost:8000

필요 패키지:
    pip install requests selenium pandas
"""

import argparse
import json
import os
import sys
import time
import uuid
import tempfile
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import requests
except ImportError:
    print("requests 패키지가 필요합니다: pip install requests")
    sys.exit(1)


class AutoFlowAgent:
    """AutoFlow 로컬 실행 에이전트"""

    def __init__(self, server_url: str, agent_id: Optional[str] = None):
        self.server_url = server_url.rstrip("/")
        self.agent_id = agent_id or str(uuid.uuid4())[:8]
        self.api_base = f"{self.server_url}/api/execution"
        self.running = True
        self.current_process: Optional[subprocess.Popen] = None

        print(f"""
╔═══════════════════════════════════════════════════════╗
║           AutoFlow 로컬 에이전트 v1.0                  ║
╠═══════════════════════════════════════════════════════╣
║  에이전트 ID: {self.agent_id:<40} ║
║  서버 URL: {self.server_url:<42} ║
╚═══════════════════════════════════════════════════════╝
        """)

    def poll_commands(self) -> list:
        """서버에서 대기 중인 명령 가져오기"""
        try:
            response = requests.get(
                f"{self.api_base}/pending-commands",
                params={"agent_id": self.agent_id},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("commands", [])
        except requests.RequestException as e:
            print(f"[{self._timestamp()}] 서버 연결 실패: {e}")
        return []

    def report_result(self, command_id: str, success: bool,
                      data: Optional[Dict] = None, error: Optional[str] = None):
        """실행 결과를 서버에 보고"""
        try:
            response = requests.post(
                f"{self.api_base}/report-result",
                params={
                    "command_id": command_id,
                    "success": success,
                    "error": error,
                },
                json={"data": data} if data else None,
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"[{self._timestamp()}] 결과 보고 실패: {e}")
        return False

    def generate_code(self, blocks: list, workflow_name: str) -> Optional[str]:
        """서버에서 Python 코드 생성"""
        try:
            response = requests.post(
                f"{self.api_base}/generate-code",
                json={
                    "blocks": blocks,
                    "workflow_name": workflow_name
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("code")
        except requests.RequestException as e:
            print(f"[{self._timestamp()}] 코드 생성 실패: {e}")
        return None

    def execute_command(self, command: Dict[str, Any]):
        """명령 실행"""
        command_id = command.get("command_id")
        command_type = command.get("command_type")
        workflow_name = command.get("workflow_name", "automation")
        blocks = command.get("blocks", [])

        print(f"\n[{self._timestamp()}] 명령 수신: {command_type}")
        print(f"  - ID: {command_id}")
        print(f"  - 워크플로우: {workflow_name}")
        print(f"  - 블록 수: {len(blocks)}")

        if command_type == "run":
            self._run_workflow(command_id, blocks, workflow_name)
        elif command_type == "stop":
            self._stop_workflow(command_id)
        elif command_type == "status":
            self._report_status(command_id)

    def _run_workflow(self, command_id: str, blocks: list, workflow_name: str):
        """워크플로우 실행"""
        print(f"[{self._timestamp()}] 코드 생성 중...")

        # 코드 생성
        code = self.generate_code(blocks, workflow_name)
        if not code:
            self.report_result(command_id, False, error="코드 생성 실패")
            return

        # 임시 파일에 저장
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as f:
            f.write(code)
            script_path = f.name

        print(f"[{self._timestamp()}] 스크립트 생성: {script_path}")
        print(f"[{self._timestamp()}] 실행 시작...")

        try:
            # Python 스크립트 실행
            self.current_process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )

            stdout, stderr = self.current_process.communicate(timeout=300)

            if self.current_process.returncode == 0:
                print(f"[{self._timestamp()}] 실행 완료!")
                # stdout에서 JSON 결과 추출 시도
                try:
                    result_data = json.loads(stdout.strip().split("\n")[-1])
                except (json.JSONDecodeError, IndexError):
                    result_data = {"output": stdout}

                self.report_result(command_id, True, data=result_data)
            else:
                print(f"[{self._timestamp()}] 실행 실패")
                self.report_result(command_id, False, error=stderr or "실행 오류")

        except subprocess.TimeoutExpired:
            self.current_process.kill()
            self.report_result(command_id, False, error="실행 시간 초과 (5분)")

        except Exception as e:
            self.report_result(command_id, False, error=str(e))

        finally:
            self.current_process = None
            # 임시 파일 삭제
            try:
                os.unlink(script_path)
            except:
                pass

    def _stop_workflow(self, command_id: str):
        """실행 중인 워크플로우 중지"""
        if self.current_process:
            self.current_process.terminate()
            print(f"[{self._timestamp()}] 워크플로우 중지됨")
            self.report_result(command_id, True, data={"message": "중지됨"})
        else:
            self.report_result(command_id, True, data={"message": "실행 중인 작업 없음"})

    def _report_status(self, command_id: str):
        """현재 상태 보고"""
        status = {
            "agent_id": self.agent_id,
            "running": self.current_process is not None,
            "timestamp": self._timestamp()
        }
        self.report_result(command_id, True, data=status)

    def _timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def run(self, poll_interval: int = 3):
        """에이전트 메인 루프"""
        print(f"[{self._timestamp()}] 에이전트 시작됨. 명령 대기 중...")
        print(f"[{self._timestamp()}] 종료하려면 Ctrl+C를 누르세요.\n")

        try:
            while self.running:
                commands = self.poll_commands()

                for command in commands:
                    self.execute_command(command)

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print(f"\n[{self._timestamp()}] 에이전트 종료 중...")
            if self.current_process:
                self.current_process.terminate()
            print(f"[{self._timestamp()}] 에이전트 종료됨.")


def main():
    parser = argparse.ArgumentParser(
        description="AutoFlow 로컬 실행 에이전트"
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="AutoFlow 서버 URL (기본값: http://localhost:8000)"
    )
    parser.add_argument(
        "--agent-id",
        default=None,
        help="에이전트 ID (기본값: 자동 생성)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=3,
        help="명령 폴링 간격 (초, 기본값: 3)"
    )

    args = parser.parse_args()

    agent = AutoFlowAgent(
        server_url=args.server,
        agent_id=args.agent_id
    )
    agent.run(poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
