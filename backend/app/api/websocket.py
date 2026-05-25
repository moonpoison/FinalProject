"""
WebSocket 엔드포인트 - PyAgent와 웹 프론트엔드 연결
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set, Optional
import json
import asyncio
from datetime import datetime

from app.utils.security import decode_token

router = APIRouter()


class ConnectionManager:
    """웹소켓 연결 관리자"""

    def __init__(self):
        # user_id -> {"agents": set(), "browsers": set()}
        self.connections: Dict[str, Dict[str, Set[WebSocket]]] = {}

    async def connect_agent(self, websocket: WebSocket, user_id: str):
        """PyAgent 연결"""
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = {"agents": set(), "browsers": set()}
        self.connections[user_id]["agents"].add(websocket)

        # 브라우저들에게 에이전트 연결 알림
        await self.broadcast_to_browsers(user_id, {
            "type": "agent_connected",
            "timestamp": datetime.now().isoformat()
        })

    async def connect_browser(self, websocket: WebSocket, user_id: str):
        """브라우저 연결"""
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = {"agents": set(), "browsers": set()}
        self.connections[user_id]["browsers"].add(websocket)

        # 에이전트 연결 상태 알림
        has_agent = len(self.connections[user_id]["agents"]) > 0
        await websocket.send_json({
            "type": "status",
            "agent_connected": has_agent,
            "timestamp": datetime.now().isoformat()
        })

    def disconnect_agent(self, websocket: WebSocket, user_id: str):
        """PyAgent 연결 해제"""
        if user_id in self.connections:
            self.connections[user_id]["agents"].discard(websocket)
            # 브라우저들에게 알림 (비동기로 처리해야 함)

    def disconnect_browser(self, websocket: WebSocket, user_id: str):
        """브라우저 연결 해제"""
        if user_id in self.connections:
            self.connections[user_id]["browsers"].discard(websocket)

    async def broadcast_to_agents(self, user_id: str, message: dict):
        """해당 유저의 모든 에이전트에게 메시지 전송"""
        if user_id in self.connections:
            disconnected = set()
            for websocket in self.connections[user_id]["agents"]:
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.add(websocket)
            # 끊어진 연결 제거
            self.connections[user_id]["agents"] -= disconnected

    async def broadcast_to_browsers(self, user_id: str, message: dict):
        """해당 유저의 모든 브라우저에게 메시지 전송"""
        if user_id in self.connections:
            disconnected = set()
            for websocket in self.connections[user_id]["browsers"]:
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.add(websocket)
            # 끊어진 연결 제거
            self.connections[user_id]["browsers"] -= disconnected

    def has_agent(self, user_id: str) -> bool:
        """에이전트 연결 여부"""
        if user_id not in self.connections:
            return False
        return len(self.connections[user_id]["agents"]) > 0


manager = ConnectionManager()


@router.websocket("/agent")
async def websocket_agent(websocket: WebSocket, token: str = Query(...)):
    """PyAgent용 웹소켓 엔드포인트"""
    # 토큰 검증
    try:
        payload = decode_token(token)
        if not payload:
            print(f"[WS] Agent auth failed: invalid token")
            await websocket.close(code=4001)
            return
        user_id = payload.get("sub")
        if not user_id:
            print(f"[WS] Agent auth failed: no user_id in token")
            await websocket.close(code=4001)
            return
    except Exception as e:
        print(f"[WS] Agent auth failed: {e}")
        await websocket.close(code=4001)
        return

    await manager.connect_agent(websocket, user_id)
    print(f"[WS] Agent connected: user={user_id}")

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "execution_log":
                # 실행 로그를 브라우저로 전달
                await manager.broadcast_to_browsers(user_id, {
                    "type": "execution_log",
                    "log": data.get("log"),
                    "workspace_id": data.get("workspace_id"),
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "execution_complete":
                # 실행 완료 알림
                await manager.broadcast_to_browsers(user_id, {
                    "type": "execution_complete",
                    "workspace_id": data.get("workspace_id"),
                    "success": data.get("success", True),
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "execution_error":
                # 실행 오류 알림
                await manager.broadcast_to_browsers(user_id, {
                    "type": "execution_error",
                    "workspace_id": data.get("workspace_id"),
                    "error": data.get("error"),
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect_agent(websocket, user_id)
        print(f"[WS] Agent disconnected: user={user_id}")
        # 브라우저에게 연결 해제 알림
        await manager.broadcast_to_browsers(user_id, {
            "type": "agent_disconnected",
            "timestamp": datetime.now().isoformat()
        })


@router.websocket("/browser")
async def websocket_browser(websocket: WebSocket, token: str = Query(...)):
    """브라우저용 웹소켓 엔드포인트"""
    # 토큰 검증
    try:
        payload = decode_token(token)
        if not payload:
            print(f"[WS] Browser auth failed: invalid token")
            await websocket.close(code=4001)
            return
        user_id = payload.get("sub")
        if not user_id:
            print(f"[WS] Browser auth failed: no user_id in token")
            await websocket.close(code=4001)
            return
    except Exception as e:
        print(f"[WS] Browser auth failed: {e}")
        await websocket.close(code=4001)
        return

    await manager.connect_browser(websocket, user_id)
    print(f"[WS] Browser connected: user={user_id}")

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "run_workspace":
                # 워크스페이스 실행 요청 -> 에이전트로 전달
                if manager.has_agent(user_id):
                    await manager.broadcast_to_agents(user_id, {
                        "type": "run_workspace",
                        "workspace_id": data.get("workspace_id"),
                        "variables": data.get("variables", {}),
                        "timestamp": datetime.now().isoformat()
                    })
                    await websocket.send_json({
                        "type": "run_requested",
                        "workspace_id": data.get("workspace_id")
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "에이전트가 연결되어 있지 않습니다"
                    })

            elif msg_type == "stop_execution":
                # 실행 중지 요청 -> 에이전트로 전달
                await manager.broadcast_to_agents(user_id, {
                    "type": "stop_execution",
                    "workspace_id": data.get("workspace_id"),
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "refresh_workspaces":
                # 워크스페이스 새로고침 요청 -> 에이전트로 전달
                await manager.broadcast_to_agents(user_id, {
                    "type": "refresh",
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "check_agent":
                # 에이전트 연결 상태 확인
                await websocket.send_json({
                    "type": "status",
                    "agent_connected": manager.has_agent(user_id),
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect_browser(websocket, user_id)
        print(f"[WS] Browser disconnected: user={user_id}")


# 에이전트 상태 확인 REST API (웹소켓 외에도 사용 가능)
@router.get("/agent-status/{user_id}")
async def get_agent_status(user_id: str):
    """에이전트 연결 상태 확인"""
    return {
        "connected": manager.has_agent(user_id),
        "timestamp": datetime.now().isoformat()
    }
