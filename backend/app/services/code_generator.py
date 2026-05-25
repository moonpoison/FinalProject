"""
블록 워크플로우를 Python 코드로 변환하는 코드 생성기
개선된 버전: 에러 처리, 재시도 로직, 로깅 강화, 지식베이스 참조
"""

from typing import List, Dict, Any, Optional
import json

# 지식베이스 (옵션)
try:
    from app.services.knowledge_base import get_knowledge_base
    HAS_KNOWLEDGE_BASE = True
except ImportError:
    HAS_KNOWLEDGE_BASE = False
    print("[CodeGenerator] 지식베이스 모듈 로드 실패 - 기본 모드로 동작")


class CodeGenerator:
    """블록을 Python/Selenium 코드로 변환 (지식베이스 참조)"""

    def __init__(self):
        self.indent = "    "
        self.kb_patterns = {}  # 지식베이스에서 가져온 코드 패턴
        self.kb_selectors = {}  # 지식베이스에서 가져온 셀렉터

    def _load_knowledge_patterns(self, prompt: str) -> None:
        """지식베이스에서 관련 코드 패턴 로드 (전체 코드 포함)"""
        if not HAS_KNOWLEDGE_BASE or not prompt:
            return

        try:
            kb = get_knowledge_base()
            # include_full_code=True로 전체 코드 포함
            search_result = kb.search_for_workflow(prompt, top_k=3, include_full_code=True)

            if search_result.get("found"):
                print(f"[CodeGenerator] 지식베이스에서 {len(search_result.get('references', []))}개 프로젝트 참조 로드")
                for ref in search_result.get("references", []):
                    # 셀렉터 수집
                    for selector in ref.get("selectors", []):
                        if selector and len(selector) < 200:
                            # 셀렉터 유형 추측
                            if "login" in selector.lower() or "id" in selector.lower() or "pw" in selector.lower():
                                self.kb_selectors["login"] = self.kb_selectors.get("login", []) + [selector]
                            elif "search" in selector.lower() or "query" in selector.lower():
                                self.kb_selectors["search"] = self.kb_selectors.get("search", []) + [selector]
                            elif "list" in selector.lower() or "item" in selector.lower():
                                self.kb_selectors["list"] = self.kb_selectors.get("list", []) + [selector]
                            elif "button" in selector.lower() or "btn" in selector.lower():
                                self.kb_selectors["button"] = self.kb_selectors.get("button", []) + [selector]

                    # 전체 코드에서 유용한 패턴 추출 (full_code 우선)
                    code_to_analyze = ref.get("full_code", "") or ref.get("code_sample", "")
                    if code_to_analyze:
                        self._extract_code_patterns(code_to_analyze, ref.get("category", ""))
                        print(f"[CodeGenerator] '{ref.get('name', '')}' 프로젝트에서 코드 패턴 추출 ({len(code_to_analyze)}자)")

                print(f"[CodeGenerator] 지식베이스에서 {len(self.kb_selectors)} 유형의 셀렉터 로드됨")
        except Exception as e:
            print(f"[CodeGenerator] 지식베이스 로드 오류: {e}")

    def _extract_code_patterns(self, code: str, category: str) -> None:
        """코드 샘플에서 유용한 패턴 추출"""
        import re

        # 로그인 패턴 추출
        login_patterns = re.findall(r'(driver\.find_element.*?(?:login|id|pw|password|email|username).*?\.(?:send_keys|click).*?)\n', code, re.IGNORECASE)
        if login_patterns:
            self.kb_patterns["login"] = self.kb_patterns.get("login", []) + login_patterns[:3]

        # 대기 패턴 추출
        wait_patterns = re.findall(r'(WebDriverWait.*?\.until.*?\))', code, re.IGNORECASE)
        if wait_patterns:
            self.kb_patterns["wait"] = self.kb_patterns.get("wait", []) + wait_patterns[:3]

        # 데이터 추출 패턴
        extract_patterns = re.findall(r'(for.*?in.*?find_elements.*?:[\s\S]*?(?:append|text|get_attribute).*?\n)', code, re.IGNORECASE)
        if extract_patterns:
            self.kb_patterns["extract"] = self.kb_patterns.get("extract", []) + extract_patterns[:3]

        # 스크롤 패턴
        scroll_patterns = re.findall(r'(execute_script.*?scroll.*?\))', code, re.IGNORECASE)
        if scroll_patterns:
            self.kb_patterns["scroll"] = self.kb_patterns.get("scroll", []) + scroll_patterns[:2]

    def _get_kb_comment(self, block_type: str) -> str:
        """블록 타입에 맞는 지식베이스 참고 주석 생성"""
        comments = []

        if block_type in ["input-text", "click"] and self.kb_selectors.get("login"):
            comments.append(f"# 참고: 유사 프로젝트 셀렉터 - {self.kb_selectors['login'][0][:60]}")
        elif block_type == "extract-list" and self.kb_selectors.get("list"):
            comments.append(f"# 참고: 유사 프로젝트 셀렉터 - {self.kb_selectors['list'][0][:60]}")
        elif block_type == "click" and self.kb_selectors.get("button"):
            comments.append(f"# 참고: 유사 프로젝트 버튼 - {self.kb_selectors['button'][0][:60]}")

        return "\n".join(comments) if comments else ""

    def generate(self, blocks: List[Dict[str, Any]], workflow_name: str = "automation",
                 prompt: Optional[str] = None) -> str:
        """블록 리스트를 실행 가능한 Python 코드로 변환 (지식베이스 참조)"""

        # 지식베이스에서 관련 패턴 로드
        self.kb_patterns = {}
        self.kb_selectors = {}
        if prompt:
            self._load_knowledge_patterns(prompt)

        imports = self._generate_imports()
        setup = self._generate_setup()
        main_code = self._generate_main(blocks)

        code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동 생성된 RPA 스크립트: {workflow_name}
AutoFlow에서 생성됨

사용법:
    python {workflow_name}.py

필수 패키지:
    pip install selenium webdriver-manager pandas openpyxl
"""

{imports}

{setup}

class AutoFlowRunner:
    """AutoFlow 자동화 실행기"""

    def __init__(self, headless: bool = False, timeout: int = 10):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self.collected_data = []
        self.variables = {{}}
        self.logger = self._setup_logger()

        # output 폴더 설정 (모든 파일 저장 위치)
        self.output_dir = os.path.join(os.getcwd(), "output")
        self._setup_output_dir()

    def _setup_output_dir(self):
        """output 폴더 생성 및 하위 폴더 구조 설정"""
        from datetime import datetime

        # 메인 output 폴더
        os.makedirs(self.output_dir, exist_ok=True)

        # 날짜별 하위 폴더
        today = datetime.now().strftime("%Y-%m-%d")
        self.today_dir = os.path.join(self.output_dir, today)
        os.makedirs(self.today_dir, exist_ok=True)

        # 하위 폴더들
        self.screenshot_dir = os.path.join(self.today_dir, "screenshots")
        self.download_dir = os.path.join(self.today_dir, "downloads")
        self.data_dir = os.path.join(self.today_dir, "data")

        for d in [self.screenshot_dir, self.download_dir, self.data_dir]:
            os.makedirs(d, exist_ok=True)

        self.log(f"출력 폴더 설정 완료: {{self.today_dir}}")

    def _setup_logger(self):
        """로거 설정"""
        import logging
        logger = logging.getLogger("AutoFlow")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                "[%(asctime)s] %(levelname)s: %(message)s",
                datefmt="%H:%M:%S"
            ))
            logger.addHandler(handler)
        return logger

    def log(self, message: str, level: str = "info"):
        """로그 출력"""
        getattr(self.logger, level)(message)

    def init_browser(self):
        """브라우저 초기화"""
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = webdriver.ChromeOptions()

        # 기본 옵션
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        # 다운로드 폴더 설정
        prefs = {{
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True  # PDF 자동 다운로드
        }}
        options.add_experimental_option("prefs", prefs)

        # User-Agent 설정
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        if self.headless:
            options.add_argument('--headless=new')

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, self.timeout)

            # headless 모드에서 다운로드 허용
            if self.headless:
                self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {{
                    "behavior": "allow",
                    "downloadPath": self.download_dir
                }})

            # 봇 탐지 우회 스크립트
            stealth_script = "Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }}); Object.defineProperty(navigator, 'plugins', {{ get: () => [1, 2, 3] }});"
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {{'source': stealth_script}})

            self.log(f"브라우저 초기화 완료 (다운로드: {{self.download_dir}})")
            return True
        except Exception as e:
            self.log(f"브라우저 초기화 실패: {{e}}", "error")
            return False

    def close_browser(self):
        """브라우저 종료"""
        if self.driver:
            try:
                self.driver.quit()
                self.log("브라우저 종료")
            except:
                pass
            self.driver = None

    def retry(self, func, max_attempts: int = 3, delay: float = 1.0):
        """재시도 래퍼"""
        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                if attempt < max_attempts - 1:
                    self.log(f"재시도 {{attempt + 1}}/{{max_attempts}}: {{e}}", "warning")
                    time.sleep(delay)
                else:
                    raise e

    def safe_find(self, selector: str, by: str = "css", timeout: int = None) -> Any:
        """요소를 안전하게 찾기"""
        timeout = timeout or self.timeout
        by_type = By.CSS_SELECTOR if by == "css" else By.XPATH

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
            return element
        except TimeoutException:
            self.log(f"요소를 찾을 수 없음: {{selector}}", "warning")
            return None
        except Exception as e:
            self.log(f"요소 검색 오류: {{e}}", "error")
            return None

    def safe_click(self, selector: str, by: str = "css", timeout: int = None) -> bool:
        """요소를 안전하게 클릭"""
        timeout = timeout or self.timeout
        by_type = By.CSS_SELECTOR if by == "css" else By.XPATH

        def do_click():
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by_type, selector))
            )
            # 스크롤하여 요소가 보이게
            self.driver.execute_script(
                "arguments[0].scrollIntoView({{behavior: 'smooth', block: 'center'}});",
                element
            )
            time.sleep(0.3)
            element.click()
            return True

        try:
            return self.retry(do_click)
        except Exception as e:
            self.log(f"클릭 실패 [{{selector}}]: {{e}}", "error")
            return False

    def safe_input(self, selector: str, text: str, by: str = "css",
                   clear: bool = True, timeout: int = None) -> bool:
        """요소에 안전하게 텍스트 입력"""
        timeout = timeout or self.timeout
        by_type = By.CSS_SELECTOR if by == "css" else By.XPATH

        def do_input():
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({{behavior: 'smooth', block: 'center'}});",
                element
            )
            time.sleep(0.2)
            if clear:
                element.clear()
            element.send_keys(text)
            return True

        try:
            return self.retry(do_input)
        except Exception as e:
            self.log(f"입력 실패 [{{selector}}]: {{e}}", "error")
            return False

    def safe_extract_text(self, selector: str, by: str = "css", timeout: int = None) -> str:
        """요소에서 텍스트 안전하게 추출"""
        element = self.safe_find(selector, by, timeout)
        if element:
            return element.text.strip()
        return ""

    def safe_extract_attribute(self, selector: str, attr: str,
                               by: str = "css", timeout: int = None) -> str:
        """요소에서 속성 안전하게 추출"""
        element = self.safe_find(selector, by, timeout)
        if element:
            return element.get_attribute(attr) or ""
        return ""

    def wait_for_page_load(self, timeout: int = None):
        """페이지 로드 완료 대기"""
        timeout = timeout or self.timeout
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(0.5)  # 추가 안정화 대기
            return True
        except:
            return False

    def random_delay(self, min_sec: float = 0.5, max_sec: float = 2.0):
        """랜덤 지연 (봇 탐지 우회)"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def save_to_excel(self, data: list, filename: str):
        """데이터를 엑셀로 저장 (output/날짜/data 폴더에 저장)"""
        try:
            import pandas as pd
            # output 폴더에 저장
            filepath = os.path.join(self.data_dir, os.path.basename(filename))
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False)
            self.log(f"엑셀 저장 완료: {{filepath}} ({{len(data)}}건)")
            return True
        except Exception as e:
            self.log(f"엑셀 저장 실패: {{e}}", "error")
            return False

    def save_to_csv(self, data: list, filename: str):
        """데이터를 CSV로 저장 (output/날짜/data 폴더에 저장)"""
        try:
            import pandas as pd
            # output 폴더에 저장
            filepath = os.path.join(self.data_dir, os.path.basename(filename))
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            self.log(f"CSV 저장 완료: {{filepath}} ({{len(data)}}건)")
            return True
        except Exception as e:
            self.log(f"CSV 저장 실패: {{e}}", "error")
            return False

    def save_screenshot(self, filename: str = None):
        """스크린샷 저장 (output/날짜/screenshots 폴더에 저장)"""
        try:
            from datetime import datetime
            if not filename:
                filename = f"screenshot_{{datetime.now().strftime('%H%M%S')}}.png"
            filepath = os.path.join(self.screenshot_dir, os.path.basename(filename))
            self.driver.save_screenshot(filepath)
            self.log(f"스크린샷 저장: {{filepath}}")
            return filepath
        except Exception as e:
            self.log(f"스크린샷 저장 실패: {{e}}", "error")
            return None

    def wait_for_download(self, timeout: int = 60):
        """다운로드 완료 대기"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            # .crdownload 파일이 없으면 다운로드 완료
            downloading = [f for f in os.listdir(self.download_dir) if f.endswith('.crdownload')]
            if not downloading:
                files = os.listdir(self.download_dir)
                if files:
                    latest = max([os.path.join(self.download_dir, f) for f in files], key=os.path.getctime)
                    self.log(f"다운로드 완료: {{latest}}")
                    return latest
            time.sleep(1)
        self.log("다운로드 타임아웃", "warning")
        return None

    def run(self) -> dict:
        """메인 자동화 실행"""
        self.log("=" * 50)
        self.log("AutoFlow 자동화 시작")
        self.log("=" * 50)

        try:
{main_code}

            self.log("=" * 50)
            self.log(f"자동화 완료! (수집: {{len(self.collected_data)}}건)")
            self.log("=" * 50)

            return {{"success": True, "data": self.collected_data}}

        except KeyboardInterrupt:
            self.log("사용자에 의해 중단됨", "warning")
            return {{"success": False, "error": "사용자 중단"}}

        except Exception as e:
            self.log(f"오류 발생: {{e}}", "error")
            import traceback
            traceback.print_exc()
            return {{"success": False, "error": str(e)}}

        finally:
            self.close_browser()


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="AutoFlow 자동화 스크립트")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드")
    parser.add_argument("--timeout", type=int, default=10, help="기본 타임아웃 (초)")
    args = parser.parse_args()

    runner = AutoFlowRunner(headless=args.headless, timeout=args.timeout)
    result = runner.run()

    print("\\n" + "=" * 50)
    print("실행 결과:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result["success"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
'''
        return code

    def _generate_imports(self) -> str:
        return '''import time
import json
import random
import os
from datetime import datetime
from typing import Any, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)'''

    def _generate_setup(self) -> str:
        return '''# 선택적 패키지 임포트
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("[경고] pandas가 설치되지 않음. 엑셀/CSV 저장 기능 제한됨")

try:
    import pyautogui
    import pyperclip
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False'''

    def _generate_main(self, blocks: List[Dict[str, Any]]) -> str:
        """블록들을 Python 코드로 변환"""
        lines = []
        indent = self.indent * 3  # 클래스 메서드 내부이므로 3단계 들여쓰기

        for i, block in enumerate(blocks):
            block_type = block.get("id") or block.get("type", "")
            field_values = block.get("fieldValues", {}) or block.get("field_values", {})
            label = block.get("label", block_type)

            # 블록 시작 주석
            lines.append(f'{indent}# ── [{i+1}] {label} {"─" * max(1, 40 - len(label))}')
            lines.append(f'{indent}self.log("[{i+1}] {label}")')

            # 블록 타입별 코드 생성
            code = self._generate_block_code(block_type, field_values, indent)
            lines.append(code)
            lines.append("")  # 빈 줄

        return "\n".join(lines)

    def _generate_block_code(self, block_type: str, values: Dict, indent: str) -> str:
        """개별 블록을 코드로 변환"""

        # 시작/기본 블록
        if block_type == "start":
            return f"{indent}pass  # 워크플로우 시작"

        elif block_type == "end":
            return f"{indent}pass  # 워크플로우 종료"

        # 브라우저 블록
        elif block_type == "open-browser":
            headless = values.get("headless", "false") == "true"
            return f'''{indent}self.headless = {headless}
{indent}if not self.init_browser():
{indent}    raise Exception("브라우저 초기화 실패")'''

        elif block_type == "open-site":
            url = values.get("url", "https://example.com")
            return f'''{indent}if not self.driver:
{indent}    self.init_browser()
{indent}self.driver.get("{url}")
{indent}self.wait_for_page_load()
{indent}self.random_delay(0.5, 1.5)'''

        elif block_type == "navigate":
            url = values.get("url", "")
            return f'''{indent}self.driver.get("{url}")
{indent}self.wait_for_page_load()'''

        elif block_type == "close-browser":
            return f"{indent}self.close_browser()"

        # 탭 블록
        elif block_type == "new-tab":
            url = values.get("url", "about:blank")
            return f'''{indent}self.driver.execute_script("window.open('{url}', '_blank');")
{indent}self.driver.switch_to.window(self.driver.window_handles[-1])
{indent}self.wait_for_page_load()'''

        elif block_type == "close-tab":
            return f'''{indent}if len(self.driver.window_handles) > 1:
{indent}    self.driver.close()
{indent}    self.driver.switch_to.window(self.driver.window_handles[-1])'''

        elif block_type == "switch-tab":
            index = values.get("index", 0)
            return f'''{indent}handles = self.driver.window_handles
{indent}if {index} < len(handles):
{indent}    self.driver.switch_to.window(handles[{index}])'''

        # 액션 블록
        elif block_type == "click":
            selector = self._escape_string(values.get("selector", ""))
            selector_type = values.get("selectorType", "css")
            return f'''{indent}self.safe_click("{selector}", by="{selector_type}")
{indent}self.random_delay(0.3, 0.8)'''

        elif block_type == "double-click":
            selector = self._escape_string(values.get("selector", ""))
            selector_type = values.get("selectorType", "css")
            return f'''{indent}element = self.safe_find("{selector}", by="{selector_type}")
{indent}if element:
{indent}    ActionChains(self.driver).double_click(element).perform()'''

        elif block_type == "right-click":
            selector = self._escape_string(values.get("selector", ""))
            selector_type = values.get("selectorType", "css")
            return f'''{indent}element = self.safe_find("{selector}", by="{selector_type}")
{indent}if element:
{indent}    ActionChains(self.driver).context_click(element).perform()'''

        elif block_type == "hover":
            selector = self._escape_string(values.get("selector", ""))
            selector_type = values.get("selectorType", "css")
            return f'''{indent}element = self.safe_find("{selector}", by="{selector_type}")
{indent}if element:
{indent}    ActionChains(self.driver).move_to_element(element).perform()
{indent}    self.random_delay(0.3, 0.6)'''

        elif block_type == "input-text":
            selector = self._escape_string(values.get("selector", ""))
            text = self._escape_string(values.get("text", ""))
            selector_type = values.get("selectorType", "css")
            clear = values.get("clear", "clear") == "clear"
            return f'''{indent}self.safe_input("{selector}", "{text}", by="{selector_type}", clear={clear})
{indent}self.random_delay(0.2, 0.5)'''

        elif block_type == "scroll":
            direction = values.get("direction", "down")
            amount = values.get("amount", 500)
            scroll_val = int(amount) if direction == "down" else -int(amount)
            return f'''{indent}self.driver.execute_script("window.scrollBy(0, {scroll_val})")
{indent}time.sleep(0.3)'''

        elif block_type == "scroll-to":
            selector = self._escape_string(values.get("selector", ""))
            selector_type = values.get("selectorType", "css")
            return f'''{indent}element = self.safe_find("{selector}", by="{selector_type}")
{indent}if element:
{indent}    self.driver.execute_script(
{indent}        "arguments[0].scrollIntoView({{behavior: 'smooth', block: 'center'}});",
{indent}        element
{indent}    )
{indent}    time.sleep(0.5)'''

        # 키보드 블록
        elif block_type == "press-key":
            key = values.get("key", "ENTER").upper()
            key_map = {
                "ENTER": "ENTER", "TAB": "TAB", "ESCAPE": "ESCAPE",
                "BACKSPACE": "BACKSPACE", "DELETE": "DELETE",
                "ARROWUP": "ARROW_UP", "ARROWDOWN": "ARROW_DOWN",
                "ARROWLEFT": "ARROW_LEFT", "ARROWRIGHT": "ARROW_RIGHT"
            }
            selenium_key = key_map.get(key, key)
            return f'''{indent}ActionChains(self.driver).send_keys(Keys.{selenium_key}).perform()
{indent}time.sleep(0.2)'''

        elif block_type == "hotkey":
            keys = values.get("keys", "ctrl+c")
            key_parts = [k.strip().lower() for k in keys.split("+")]
            return f'''{indent}actions = ActionChains(self.driver)
{indent}# 단축키: {keys}
{indent}{"".join([f"actions.key_down(Keys.{k.upper() if k in ['ctrl','alt','shift'] else k.upper()}); " for k in key_parts[:-1]])}
{indent}actions.send_keys("{key_parts[-1]}")
{indent}{"".join([f"actions.key_up(Keys.{k.upper()}); " for k in reversed(key_parts[:-1]) if k in ['ctrl','alt','shift']])}
{indent}actions.perform()'''

        elif block_type == "type-text":
            text = self._escape_string(values.get("text", ""))
            delay = values.get("delay", 0.05)
            return f'''{indent}for char in "{text}":
{indent}    ActionChains(self.driver).send_keys(char).perform()
{indent}    time.sleep({delay})'''

        # 데이터 추출 블록
        elif block_type == "extract-text":
            selector = self._escape_string(values.get("selector", ""))
            var_name = values.get("variable", "extracted_text")
            selector_type = values.get("selectorType", "css")
            return f'''{indent}{var_name} = self.safe_extract_text("{selector}", by="{selector_type}")
{indent}self.variables["{var_name}"] = {var_name}
{indent}self.collected_data.append({{"{var_name}": {var_name}}})
{indent}self.log(f"추출: {{{var_name}[:50]}}...")'''

        elif block_type == "extract-attribute":
            selector = self._escape_string(values.get("selector", ""))
            attr = values.get("attribute", "href")
            var_name = values.get("variable", "attr_value")
            selector_type = values.get("selectorType", "css")
            return f'''{indent}{var_name} = self.safe_extract_attribute("{selector}", "{attr}", by="{selector_type}")
{indent}self.variables["{var_name}"] = {var_name}
{indent}self.collected_data.append({{"{var_name}": {var_name}}})'''

        elif block_type == "extract-list":
            selector = self._escape_string(values.get("selector", ""))
            selector_type = values.get("selectorType", "css")
            fields = values.get("fields", "text")
            var_name = values.get("variable", "items")
            return f'''{indent}by_type = By.CSS_SELECTOR if "{selector_type}" == "css" else By.XPATH
{indent}elements = self.driver.find_elements(by_type, "{selector}")
{indent}{var_name} = []
{indent}for idx, el in enumerate(elements):
{indent}    item = {{"index": idx}}
{indent}    for field in "{fields}".split(","):
{indent}        field = field.strip()
{indent}        if field == "text":
{indent}            item["text"] = el.text.strip()
{indent}        elif field == "html":
{indent}            item["html"] = el.get_attribute("innerHTML")
{indent}        else:
{indent}            item[field] = el.get_attribute(field)
{indent}    {var_name}.append(item)
{indent}    self.collected_data.append(item)
{indent}self.variables["{var_name}"] = {var_name}
{indent}self.log(f"목록 추출: {{len({var_name})}}건")'''

        # 저장 블록
        elif block_type == "save-excel":
            filename = values.get("filename", "result.xlsx")
            var_name = values.get("variable", "")
            if var_name:
                return f'''{indent}data = self.variables.get("{var_name}", self.collected_data)
{indent}self.save_to_excel(data, "{filename}")'''
            return f'{indent}self.save_to_excel(self.collected_data, "{filename}")'

        elif block_type == "save-csv":
            filename = values.get("filename", "result.csv")
            var_name = values.get("variable", "")
            if var_name:
                return f'''{indent}data = self.variables.get("{var_name}", self.collected_data)
{indent}self.save_to_csv(data, "{filename}")'''
            return f'{indent}self.save_to_csv(self.collected_data, "{filename}")'

        # 제어 블록
        elif block_type == "wait":
            seconds = values.get("seconds", 1)
            return f'{indent}time.sleep({seconds})'

        elif block_type == "random-delay":
            min_sec = values.get("min", 1)
            max_sec = values.get("max", 3)
            return f'{indent}self.random_delay({min_sec}, {max_sec})'

        elif block_type == "wait-element":
            selector = self._escape_string(values.get("selector", ""))
            timeout = values.get("timeout", 10)
            selector_type = values.get("selectorType", "css")
            return f'''{indent}element = self.safe_find("{selector}", by="{selector_type}", timeout={timeout})
{indent}if not element:
{indent}    self.log("요소 대기 타임아웃: {selector}", "warning")'''

        elif block_type == "wait-page-load":
            timeout = values.get("timeout", 10)
            return f'{indent}self.wait_for_page_load(timeout={timeout})'

        elif block_type == "loop":
            count = values.get("count", 1)
            return f'''{indent}for _loop_i in range({count}):
{indent}    self.log(f"반복 {{_loop_i + 1}}/{count}")
{indent}    # TODO: 반복할 블록 내용'''

        elif block_type == "condition":
            condition = values.get("condition", "True")
            return f'''{indent}if {condition}:
{indent}    pass  # TODO: 조건 참일 때 실행할 내용'''

        # 유틸리티 블록
        elif block_type == "screenshot":
            filename = values.get("filename", "screenshot.png")
            if not filename.endswith(".png"):
                filename += ".png"
            return f'{indent}self.save_screenshot("{filename}")'

        elif block_type == "log":
            message = self._escape_string(values.get("message", ""))
            return f'{indent}self.log("{message}")'

        elif block_type == "set-variable":
            name = values.get("name", "var")
            value = values.get("value", "")
            return f'''{indent}self.variables["{name}"] = "{value}"'''

        # 알림 블록
        elif block_type == "alert-accept":
            return f'''{indent}try:
{indent}    alert = self.driver.switch_to.alert
{indent}    alert.accept()
{indent}    self.log("알림 수락")
{indent}except:
{indent}    pass'''

        elif block_type == "alert-dismiss":
            return f'''{indent}try:
{indent}    alert = self.driver.switch_to.alert
{indent}    alert.dismiss()
{indent}    self.log("알림 거부")
{indent}except:
{indent}    pass'''

        elif block_type == "refresh":
            return f'''{indent}self.driver.refresh()
{indent}self.wait_for_page_load()'''

        elif block_type == "go-back":
            return f'''{indent}self.driver.back()
{indent}self.wait_for_page_load()'''

        elif block_type == "go-forward":
            return f'''{indent}self.driver.forward()
{indent}self.wait_for_page_load()'''

        # API 블록
        elif block_type == "http-request" or block_type == "api-request":
            url = self._escape_string(values.get("url", ""))
            method = values.get("method", "GET").upper()
            var_name = values.get("variable", "api_response")
            return f'''{indent}import requests
{indent}try:
{indent}    _response = requests.{method.lower()}("{url}", timeout=30)
{indent}    {var_name} = _response.json() if _response.headers.get("content-type", "").startswith("application/json") else _response.text
{indent}    self.variables["{var_name}"] = {var_name}
{indent}    self.log(f"API 응답: {{_response.status_code}}")
{indent}except Exception as e:
{indent}    self.log(f"API 요청 실패: {{e}}", "error")'''

        # 데스크톱 자동화 블록
        elif block_type == "mouse-click-coords":
            x = values.get("x", 0)
            y = values.get("y", 0)
            return f'''{indent}if HAS_PYAUTOGUI:
{indent}    pyautogui.click({x}, {y})
{indent}    self.log(f"마우스 클릭: ({x}, {y})")'''

        elif block_type == "mouse-move":
            x = values.get("x", 0)
            y = values.get("y", 0)
            return f'''{indent}if HAS_PYAUTOGUI:
{indent}    pyautogui.moveTo({x}, {y}, duration=0.3)'''

        elif block_type == "clipboard-copy":
            text = self._escape_string(values.get("text", ""))
            return f'''{indent}if HAS_PYAUTOGUI:
{indent}    pyperclip.copy("{text}")'''

        elif block_type == "clipboard-paste":
            return f'''{indent}if HAS_PYAUTOGUI:
{indent}    pyautogui.hotkey("ctrl", "v")'''

        # 커스텀 코드
        elif block_type == "custom-code":
            code = values.get("code", "pass")
            description = values.get("description", "커스텀 코드")
            code_lines = code.replace("\\n", "\n").split("\n")
            indented_code = "\n".join([f"{indent}{line}" for line in code_lines])
            return f'''{indent}# {description}
{indented_code}'''

        # 알 수 없는 블록
        else:
            return f'{indent}pass  # 미지원 블록: {block_type}'

    def _escape_string(self, s: str) -> str:
        """문자열 이스케이프"""
        if not s:
            return ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# 싱글톤 인스턴스
code_generator = CodeGenerator()
