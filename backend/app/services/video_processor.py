import os
import uuid
import base64
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

import aiofiles
from openai import OpenAI
import anthropic

from app.config import settings
from app.services.web_analyzer import WebAnalyzer
from app.services.intelligent_selector import intelligent_selector


# Storage directories
UPLOAD_DIR = Path("uploads/videos")
FRAMES_DIR = Path("uploads/frames")
AUDIO_DIR = Path("uploads/audio")

# FFmpeg paths (WinGet 설치 경로)
FFMPEG_BIN = Path(os.path.expanduser("~")) / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin"
FFMPEG = str(FFMPEG_BIN / "ffmpeg.exe") if (FFMPEG_BIN / "ffmpeg.exe").exists() else "ffmpeg"
FFPROBE = str(FFMPEG_BIN / "ffprobe.exe") if (FFMPEG_BIN / "ffprobe.exe").exists() else "ffprobe"

# Ensure directories exist
for d in [UPLOAD_DIR, FRAMES_DIR, AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class VideoProcessor:
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def save_uploaded_video(self, file_content: bytes, original_filename: str) -> Tuple[str, str, int]:
        """Save uploaded video file and return (filename, path, size)"""
        ext = Path(original_filename).suffix or ".mp4"
        filename = f"{uuid.uuid4()}{ext}"
        file_path = UPLOAD_DIR / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        return filename, str(file_path), len(file_content)

    async def get_video_duration(self, video_path: str) -> int:
        """Get video duration in seconds using ffprobe"""
        try:
            cmd = f'"{FFPROBE}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                return int(float(result.stdout.strip()))
            else:
                print(f"ffprobe error: {result.stderr}")
        except Exception as e:
            print(f"Error getting video duration: {e}")
        return 0

    async def extract_audio(self, video_path: str, video_id: str) -> Optional[str]:
        """Extract audio from video using ffmpeg"""
        audio_filename = f"{video_id}.mp3"
        audio_path = AUDIO_DIR / audio_filename

        cmd = f'"{FFMPEG}" -y -i "{video_path}" -vn -acodec libmp3lame -ar 16000 -ac 1 "{audio_path}"'

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, shell=True
            )
            if result.returncode == 0 and audio_path.exists():
                return str(audio_path)
            else:
                print(f"ffmpeg audio error: {result.stderr}")
        except Exception as e:
            print(f"Error extracting audio: {e}")
        return None

    async def extract_frames(self, video_path: str, video_id: str, interval: int = 1) -> Tuple[str, int]:
        """Extract frames at specified interval (default 1 second)"""
        frames_dir = FRAMES_DIR / video_id
        frames_dir.mkdir(parents=True, exist_ok=True)

        output_pattern = str(frames_dir / "frame_%04d.jpg")
        cmd = f'"{FFMPEG}" -y -i "{video_path}" -vf "fps=1/{interval}" -q:v 2 "{output_pattern}"'

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                frame_count = len(list(frames_dir.glob("*.jpg")))
                return str(frames_dir), frame_count
            else:
                print(f"ffmpeg frames error: {result.stderr}")
        except Exception as e:
            print(f"Error extracting frames: {e}")
        return str(frames_dir), 0

    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio using OpenAI Whisper API"""
        if not self.openai_client:
            print("OpenAI client not configured")
            return None

        try:
            with open(audio_path, "rb") as audio_file:
                transcript = await asyncio.to_thread(
                    lambda: self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ko",
                        response_format="text"
                    )
                )
            return transcript
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    async def analyze_frames_with_vision(
        self, frames_dir: str, transcript: Optional[str], max_frames: int = 30
    ) -> dict:
        """Analyze frames using Claude Vision API - 프롬프트 생성 방식"""
        frames_path = Path(frames_dir)
        frame_files = sorted(frames_path.glob("*.jpg"))

        # Sample frames if too many
        if len(frame_files) > max_frames:
            step = len(frame_files) // max_frames
            frame_files = frame_files[::step][:max_frames]

        # Encode frames to base64
        encoded_frames = []
        for frame_file in frame_files:
            with open(frame_file, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode("utf-8")
                encoded_frames.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": data
                    }
                })

        # 1단계: 영상에서 프롬프트 생성 (음성 우선)
        if transcript:
            # 음성이 있으면 음성 내용을 최우선으로 사용
            prompt_generation = f"""당신은 RPA 자동화 전문가입니다. 사용자가 화면 녹화와 함께 **음성으로 설명한 작업**을 자동화해야 합니다.

## ⚠️ 매우 중요: 음성 설명이 최우선입니다!
사용자가 음성으로 설명한 내용이 **자동화하고 싶은 작업**입니다.
화면에 보이는 것(녹화 프로그램, 편집기 등)은 무시하고, **음성 내용만** 기반으로 워크플로우를 생성하세요.

## 사용자 음성 설명 (이것이 자동화할 작업입니다!):
"{transcript}"

## 화면 캡처 이미지
아래 이미지들은 참고용입니다. 음성 설명에 언급된 사이트/작업의 URL이나 요소를 확인하는 데만 사용하세요.
화면에 OBS, 녹화 프로그램, 편집기 등이 보여도 무시하세요 - 그것은 녹화 도구일 뿐입니다.

"""
        else:
            # 음성이 없으면 화면 분석
            prompt_generation = """당신은 화면 녹화 영상을 분석하여 사용자가 자동화하고 싶은 작업을 파악하는 전문가입니다.

주어진 화면 캡처 이미지들을 순서대로 분석하여:
1. 사용자가 어떤 사이트/앱에서 작업하고 있는지 파악
2. 어떤 작업을 반복하거나 자동화하려는지 파악
3. 사용자가 입력하거나 클릭하는 요소들 식별

"""

        prompt_generation += """
## 응답 형식 (JSON만 출력):
{
    "generated_prompt": "사용자가 자동화하고 싶어하는 작업을 정확히 설명 (음성 내용 기반)",
    "detected_site": "작업 대상 사이트 (예: 네이버 증권, 쿠팡 등)",
    "detected_url": "사이트 URL (예: https://finance.naver.com)",
    "detected_actions": [
        "1단계: 구체적인 액션",
        "2단계: 구체적인 액션",
        "3단계: 구체적인 액션"
    ],
    "detected_elements": [
        "필요한 요소1 (예: 검색창)",
        "필요한 요소2 (예: 스크린샷 버튼)"
    ],
    "task_summary": "전체 작업 요약 (음성 설명 기반으로 2-3문장)",
    "confidence": 0.95
}

⚠️ 중요:
1. 음성 설명이 있으면 그 내용을 그대로 generated_prompt에 반영하세요
2. 화면의 녹화 프로그램(OBS 등)은 무시하세요
3. 음성에서 언급한 사이트와 작업을 정확히 파악하세요

JSON만 출력하세요."""

        # Build message content
        content = []

        if transcript:
            # 음성이 있으면 음성 우선 강조
            content.append({"type": "text", "text": f"""⚠️ 중요: 사용자가 음성으로 다음 작업을 자동화하고 싶다고 설명했습니다:
"{transcript}"

아래 화면 캡처는 참고용입니다. 녹화 프로그램(OBS 등)이 보여도 무시하고, 음성 내용을 기반으로 워크플로우를 생성하세요.

"""})
        else:
            content.append({"type": "text", "text": "다음은 사용자의 화면 녹화에서 추출한 프레임들입니다. 사용자가 자동화하고 싶은 작업이 무엇인지 분석해주세요:\n\n"})

        for i, frame in enumerate(encoded_frames):
            content.append({"type": "text", "text": f"[프레임 {i+1}/{len(encoded_frames)}]"})
            content.append(frame)

        content.append({"type": "text", "text": f"\n\n{prompt_generation}"})

        try:
            response = await asyncio.to_thread(
                lambda: self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": content}]
                )
            )

            response_text = response.content[0].text
            print(f"[Video] Claude 분석 결과: {response_text[:200]}...")

            # Parse JSON from response
            import json
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)

                # ===== 실제 웹페이지 분석 (지능형 셀렉터 추출) =====
                verified_selectors = {}
                page_elements = {}
                intelligent_analysis = {}
                detected_url = result.get("detected_url", "")

                if detected_url and detected_url.startswith("http"):
                    print(f"[Video] 지능형 셀렉터 분석 시작: {detected_url}")
                    try:
                        # IntelligentSelectorService로 실제 HTML 기반 분석
                        intelligent_result = await intelligent_selector.analyze_page_for_task(
                            detected_url,
                            result.get("generated_prompt", ""),
                            result.get("detected_elements", [])
                        )

                        if intelligent_result.get("success"):
                            # 셀렉터 변환 (dict 형식으로)
                            for name, info in intelligent_result.get("selectors", {}).items():
                                if isinstance(info, dict) and info.get("selector") != "not_found":
                                    verified_selectors[name] = info.get("selector", "")

                            # 폼 정보
                            forms = intelligent_result.get("forms", [])
                            for form in forms:
                                if form.get("input_selector"):
                                    verified_selectors[f"form_{form.get('purpose', 'input')}"] = form.get("input_selector")
                                if form.get("submit_selector"):
                                    verified_selectors[f"submit_{form.get('purpose', 'button')}"] = form.get("submit_selector")

                            # 리스트 정보
                            lists = intelligent_result.get("lists", [])
                            for lst in lists:
                                if lst.get("item_selector"):
                                    verified_selectors[f"list_{lst.get('purpose', 'items')}"] = lst.get("item_selector")

                            intelligent_analysis = {
                                "selectors": intelligent_result.get("selectors", {}),
                                "forms": forms,
                                "lists": lists,
                                "notes": intelligent_result.get("notes", "")
                            }

                            print(f"[Video] 지능형 분석 완료 - 셀렉터 {len(verified_selectors)}개 추출")
                        else:
                            print(f"[Video] 지능형 분석 실패: {intelligent_result.get('error', 'unknown')}")
                            # 폴백: 기존 WebAnalyzer 사용
                            html = await WebAnalyzer.fetch_page(detected_url)
                            if html:
                                page_structure = WebAnalyzer.extract_page_structure(html)
                                page_elements = {
                                    "inputs": page_structure.get("inputs", [])[:10],
                                    "buttons": page_structure.get("buttons", [])[:10],
                                    "lists": page_structure.get("lists", [])[:5]
                                }
                    except Exception as e:
                        print(f"[Video] 웹페이지 분석 오류: {e}")

                # 분석 결과 반환 (실제 검증된 셀렉터 포함)
                return {
                    "generated_prompt": result.get("generated_prompt", "화면 녹화 작업 자동화"),
                    "detected_site": result.get("detected_site", ""),
                    "detected_url": detected_url,
                    "detected_actions": result.get("detected_actions", []),
                    "detected_elements": result.get("detected_elements", []),
                    "task_summary": result.get("task_summary", ""),
                    "confidence": result.get("confidence", 0.5),
                    "task_name": result.get("generated_prompt", "영상 분석 작업")[:30],
                    "summary": result.get("task_summary", "영상에서 분석된 작업입니다."),
                    "verified_selectors": verified_selectors,
                    "page_elements": page_elements,
                    "intelligent_analysis": intelligent_analysis
                }

        except Exception as e:
            print(f"Error analyzing frames: {e}")

        return {
            "generated_prompt": "화면 녹화 작업 자동화",
            "detected_site": "",
            "detected_url": "",
            "detected_actions": [],
            "detected_elements": [],
            "task_summary": "영상 분석 중 오류가 발생했습니다.",
            "confidence": 0,
            "task_name": "알 수 없는 작업",
            "summary": "영상 분석 중 오류가 발생했습니다."
        }

    async def generate_blocks_from_analysis(self, analysis_result: dict) -> List[dict]:
        """Generate automation blocks from analysis result"""
        blocks = []
        block_id_counter = 0

        # Block type mapping
        block_mapping = {
            "open-site": {"id": "open-site", "type": "browser", "category": "browser", "label": "사이트 열기", "icon": "Globe", "color": "#3B82F6"},
            "click": {"id": "click", "type": "action", "category": "browser", "label": "클릭", "icon": "MousePointer", "color": "#8B5CF6"},
            "input": {"id": "input", "type": "action", "category": "browser", "label": "텍스트 입력", "icon": "Type", "color": "#EC4899"},
            "extract": {"id": "extract-list", "type": "data", "category": "data", "label": "데이터 추출", "icon": "Database", "color": "#10B981"},
            "wait": {"id": "wait", "type": "control", "category": "control", "label": "대기", "icon": "Clock", "color": "#F59E0B"},
            "condition": {"id": "condition", "type": "control", "category": "control", "label": "조건 분기", "icon": "GitBranch", "color": "#6366F1"},
            "loop": {"id": "loop", "type": "control", "category": "control", "label": "반복", "icon": "Repeat", "color": "#14B8A6"},
            "save-excel": {"id": "save-excel", "type": "data", "category": "data", "label": "엑셀 저장", "icon": "FileSpreadsheet", "color": "#22C55E"},
        }

        # Add start block
        blocks.append({
            "id": "start",
            "instance_id": f"start-{datetime.now().timestamp()}",
            "type": "trigger",
            "category": "trigger",
            "label": "시작",
            "icon": "Play",
            "color": "#22C55E",
            "field_values": {},
            "group_id": None,
            "group_label": None,
            "group_color": None
        })

        for group in analysis_result.get("groups", []):
            group_id = group.get("id")
            group_label = group.get("label")
            group_color = group.get("color", "#6B7280")

            for step in group.get("steps", []):
                block_type = step.get("block_type", "click")
                block_def = block_mapping.get(block_type, block_mapping["click"])

                block = {
                    **block_def,
                    "instance_id": f"{block_def['id']}-{datetime.now().timestamp()}-{block_id_counter}",
                    "field_values": step.get("params", {}),
                    "group_id": group_id,
                    "group_label": group_label,
                    "group_color": group_color
                }

                # Add step label as description
                if step.get("label"):
                    block["field_values"]["description"] = step["label"]

                blocks.append(block)
                block_id_counter += 1

        return blocks

    async def process_video_complete(
        self,
        video_id: str,
        video_path: str,
        progress_callback=None
    ) -> dict:
        """Complete video processing pipeline"""
        result = {
            "duration": 0,
            "audio_path": None,
            "transcript": None,
            "frames_dir": None,
            "frame_count": 0,
            "analysis_result": None,
            "generated_blocks": None,
            "error": None
        }

        try:
            # Step 1: Get video duration
            if progress_callback:
                await progress_callback("processing", 5)
            result["duration"] = await self.get_video_duration(video_path)

            # Step 2: Extract audio
            if progress_callback:
                await progress_callback("extracting_audio", 15)
            result["audio_path"] = await self.extract_audio(video_path, video_id)

            # Step 3: Extract frames
            if progress_callback:
                await progress_callback("extracting_frames", 30)
            result["frames_dir"], result["frame_count"] = await self.extract_frames(
                video_path, video_id
            )

            # Step 4: Transcribe audio
            if progress_callback:
                await progress_callback("transcribing", 50)
            if result["audio_path"]:
                result["transcript"] = await self.transcribe_audio(result["audio_path"])

            # Step 5: Analyze frames with vision
            if progress_callback:
                await progress_callback("analyzing", 70)
            if result["frames_dir"] and result["frame_count"] > 0:
                result["analysis_result"] = await self.analyze_frames_with_vision(
                    result["frames_dir"],
                    result["transcript"]
                )

            # Step 6: Generate blocks
            if progress_callback:
                await progress_callback("generating", 90)
            if result["analysis_result"]:
                result["generated_blocks"] = await self.generate_blocks_from_analysis(
                    result["analysis_result"]
                )

            if progress_callback:
                await progress_callback("completed", 100)

        except Exception as e:
            result["error"] = str(e)
            if progress_callback:
                await progress_callback("failed", 0)

        return result


# Singleton instance
video_processor = VideoProcessor()
