#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoFlow 에이전트 빌드 스크립트
PyInstaller로 단일 실행 파일을 생성합니다.

사용법:
    python build_agent.py          # 현재 OS용 빌드
    python build_agent.py --clean  # 이전 빌드 정리 후 빌드
"""

import sys
import os
import subprocess
import shutil
import platform

AGENT_SCRIPT = os.path.join(os.path.dirname(__file__), "autoflow_app.py")
DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")
BUILD_DIR = os.path.join(os.path.dirname(__file__), "build")
VERSION = "1.0.0"


def get_platform_name():
    """현재 OS 이름 반환"""
    system = platform.system().lower()
    if system == "darwin":
        return "mac"
    elif system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    return system


def ensure_pyinstaller():
    """PyInstaller 설치 확인"""
    try:
        import PyInstaller
        print(f"[빌드] PyInstaller {PyInstaller.__version__} 확인됨")
    except ImportError:
        print("[빌드] PyInstaller 설치 중...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            stdout=subprocess.DEVNULL,
        )
        print("[빌드] PyInstaller 설치 완료")


def build():
    """에이전트 빌드"""
    plat = get_platform_name()
    ext = ".exe" if plat == "windows" else ""
    output_name = f"AutoFlowAgent-v{VERSION}-{plat}{ext}"

    print(f"""
╔═══════════════════════════════════════════════════════╗
║           AutoFlow 에이전트 빌드                        ║
╠═══════════════════════════════════════════════════════╣
║  플랫폼  : {plat:<43} ║
║  버전    : {VERSION:<43} ║
║  출력    : dist/{output_name:<37} ║
╚═══════════════════════════════════════════════════════╝
    """)

    ensure_pyinstaller()

    # ws_agent.py도 같이 포함 (CLI 모드 지원)
    ws_agent_path = os.path.join(os.path.dirname(__file__), "ws_agent.py")

    # PyInstaller 명령 구성
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",  # Windows에서 콘솔창 숨김, Mac에서는 무해
        "--name", output_name.replace(ext, ""),
        "--clean",
        # ws_agent.py 데이터로 포함
        "--add-data", f"{ws_agent_path}{os.pathsep}.",
        # GUI 관련
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.scrolledtext",
        # 에이전트 필수 패키지
        "--hidden-import", "requests",
        "--hidden-import", "websocket",
        "--hidden-import", "websocket._abnf",
        "--hidden-import", "websocket._app",
        "--hidden-import", "websocket._core",
        "--hidden-import", "websocket._exceptions",
        "--hidden-import", "websocket._http",
        "--hidden-import", "websocket._logging",
        "--hidden-import", "websocket._socket",
        "--hidden-import", "websocket._ssl_compat",
        "--hidden-import", "websocket._url",
        "--hidden-import", "websocket._utils",
        # 런타임 패키지 (생성 스크립트 실행용)
        "--hidden-import", "selenium",
        "--hidden-import", "selenium.webdriver",
        "--hidden-import", "selenium.webdriver.chrome",
        "--hidden-import", "selenium.webdriver.chrome.service",
        "--hidden-import", "selenium.webdriver.common.by",
        "--hidden-import", "selenium.webdriver.common.keys",
        "--hidden-import", "selenium.webdriver.support.ui",
        "--hidden-import", "selenium.webdriver.support.expected_conditions",
        "--hidden-import", "selenium.webdriver.common.action_chains",
        "--hidden-import", "webdriver_manager",
        "--hidden-import", "webdriver_manager.chrome",
        "--hidden-import", "pandas",
        "--hidden-import", "openpyxl",
        # 불필요한 모듈 제외 (용량 최적화)
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "numpy.testing",
        "--exclude-module", "unittest",
        # 빌드 디렉토리
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        # 소스
        AGENT_SCRIPT,
    ]

    print("[빌드] PyInstaller 실행 중... (1-3분 소요)")
    print()

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        output_path = os.path.join(DIST_DIR, output_name.replace(ext, "") + ext)
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"""
╔═══════════════════════════════════════════════════════╗
║  빌드 성공!                                            ║
╠═══════════════════════════════════════════════════════╣
║  파일: dist/{output_name:<40} ║
║  크기: {size_mb:.1f} MB{' ' * (40 - len(f'{size_mb:.1f} MB'))} ║
╚═══════════════════════════════════════════════════════╝
            """)
        else:
            print(f"[빌드] 성공했으나 파일을 찾을 수 없음: {output_path}")
    else:
        print(f"[빌드] 실패 (exit code: {result.returncode})")
        sys.exit(1)

    # 빌드 중간 파일 정리
    cleanup_build()

    return output_path


def cleanup_build():
    """빌드 중간 파일 정리"""
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    spec_files = [f for f in os.listdir(os.path.dirname(__file__) or ".") if f.endswith(".spec")]
    for spec in spec_files:
        try:
            os.remove(os.path.join(os.path.dirname(__file__) or ".", spec))
        except OSError:
            pass
    print("[빌드] 중간 파일 정리 완료")


def clean_all():
    """모든 빌드 아티팩트 삭제"""
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
    cleanup_build()
    print("[빌드] 모든 빌드 파일 삭제됨")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AutoFlow 에이전트 빌드")
    parser.add_argument("--clean", action="store_true", help="이전 빌드 정리 후 빌드")
    parser.add_argument("--clean-only", action="store_true", help="빌드 파일만 정리 (빌드하지 않음)")
    args = parser.parse_args()

    if args.clean_only:
        clean_all()
    else:
        if args.clean:
            clean_all()
        build()
