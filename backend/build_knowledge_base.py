#!/usr/bin/env python3
"""
지식베이스 구축 스크립트
자동화 프로젝트 폴더를 스캔하여 인덱스와 벡터 DB를 생성합니다.

사용법:
    python build_knowledge_base.py                    # 인덱스 구축
    python build_knowledge_base.py --force            # 강제 재구축
    python build_knowledge_base.py search "네이버 크롤링"  # 검색 테스트
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from app.services.knowledge_base import KnowledgeBase


def main():
    # 설정
    PROJECTS_PATH = r"C:\Users\user\Desktop\프로그램 파일"
    DATA_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base_data")
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")

    print("=" * 60)
    print("  자동화 프로젝트 지식베이스 구축 도구")
    print("=" * 60)
    print(f"\n프로젝트 경로: {PROJECTS_PATH}")
    print(f"데이터 저장 경로: {DATA_DIR}")
    print(f"OpenAI API: {'설정됨' if OPENAI_KEY else '미설정 (폴백 임베딩 사용)'}")
    print()

    # 지식베이스 초기화
    kb = KnowledgeBase(
        projects_path=PROJECTS_PATH,
        data_dir=DATA_DIR,
        openai_api_key=OPENAI_KEY
    )

    # 명령어 처리
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--force":
            print("\n[강제 재구축 모드]")
            kb.build_index(force=True)

        elif command == "search":
            query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "네이버 크롤링"
            print(f"\n[검색] '{query}'")
            print("-" * 40)

            results = kb.search(query, top_k=5)
            if results:
                for i, r in enumerate(results, 1):
                    print(f"\n{i}. {r.name}")
                    print(f"   카테고리: {r.category}/{r.subcategory}")
                    print(f"   점수: {r.score:.2f} (키워드: {r.keyword_score:.2f}, 시맨틱: {r.semantic_score:.2f})")
                    print(f"   설명: {r.description}")
            else:
                print("검색 결과 없음")

        elif command == "context":
            query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "네이버 카페 글쓰기"
            print(f"\n[AI 컨텍스트] '{query}'")
            print("-" * 40)
            context = kb.get_context_for_ai(query)
            print(context if context else "컨텍스트 없음")

        elif command == "stats":
            stats = kb.get_stats()
            print("\n[통계]")
            print(f"총 프로젝트: {stats['total_projects']}")
            print(f"총 코드 라인: {stats['total_lines']:,}")
            print(f"벡터 DB: {'활성' if stats['has_vector_db'] else '비활성'}")
            print("\n카테고리별:")
            for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
                print(f"  {cat}: {count}개")

        else:
            print(f"알 수 없는 명령어: {command}")
            print_usage()

    else:
        # 기본: 인덱스 구축
        stats = kb.get_stats()
        if stats['total_projects'] > 0:
            print(f"\n기존 인덱스 발견: {stats['total_projects']}개 프로젝트")
            print("재구축하려면 --force 옵션을 사용하세요.")
            print("\n[현재 통계]")
            print(f"총 프로젝트: {stats['total_projects']}")
            print(f"벡터 DB: {'활성' if stats['has_vector_db'] else '비활성'}")
        else:
            print("\n인덱스 구축 시작...")
            kb.build_index(force=True)


def print_usage():
    print("""
사용법:
    python build_knowledge_base.py              # 인덱스 구축 (기존 있으면 스킵)
    python build_knowledge_base.py --force      # 강제 재구축
    python build_knowledge_base.py search <쿼리>  # 검색 테스트
    python build_knowledge_base.py context <쿼리> # AI 컨텍스트 생성
    python build_knowledge_base.py stats        # 통계 출력
""")


if __name__ == "__main__":
    main()
