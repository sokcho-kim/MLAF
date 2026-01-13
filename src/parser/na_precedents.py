# -*- coding: utf-8 -*-
"""
국회선례집 파싱 모듈 (v0)
- 선례번호 단위 분할
- 오탐 방지 안전장치 포함
"""
import re
import json
import fitz
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sys

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def extract_text_with_pages(pdf_path: str, start_page: int = 0) -> List[Tuple[int, str]]:
    """PDF에서 페이지별 텍스트 추출"""
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pages.append((page_num + 1, text))

    doc.close()
    return pages


def is_precedent_number_line(line: str, prev_num: Optional[int]) -> Tuple[bool, Optional[int]]:
    """
    선례 번호 줄인지 판단
    선례집 형식: 숫자만 단독으로 한 줄에 있음

    Returns:
        (is_valid, precedent_num)
    """
    line = line.strip()

    # 숫자만 있는 줄인지 확인
    if not re.match(r'^\d+$', line):
        return False, None

    num = int(line)

    # 안전장치 1: 번호가 합리적 범위인지 (1~600 정도)
    if num < 1 or num > 600:
        return False, None

    # 안전장치 2: 단조 증가 체크
    if prev_num is not None:
        # 같거나 작으면 무시
        if num <= prev_num:
            return False, None
        # 너무 큰 점프도 의심 (50 이상)
        if num - prev_num > 50:
            return False, None

    return True, num


def extract_title_from_content(content_lines: List[str]) -> str:
    """내용에서 제목(첫 문장) 추출"""
    if not content_lines:
        return ""

    # 첫 몇 줄을 합쳐서 제목으로
    title_lines = []
    for line in content_lines[:3]:
        line = line.strip()
        if not line:
            continue
        title_lines.append(line)
        # 마침표나 관련법조문(국, 헌 등) 나오면 제목 끝
        if re.search(r'[.。]$|^국\s*\d|^헌\s*\d|^국감조', line):
            break

    title = ' '.join(title_lines)
    # 너무 길면 자르기
    if len(title) > 100:
        title = title[:100] + "..."

    return title


def parse_precedents(pages: List[Tuple[int, str]]) -> List[Dict]:
    """선례 단위로 파싱"""

    precedents = []
    current_precedent = None
    current_content = []
    prev_num = None

    for page_num, page_text in pages:
        lines = page_text.split('\n')

        for line in lines:
            # 선례 번호 줄인지 확인
            is_num_line, num = is_precedent_number_line(line, prev_num)

            if is_num_line:
                # 이전 선례 저장
                if current_precedent:
                    content_text = '\n'.join(current_content).strip()
                    current_precedent['description_raw'] = content_text
                    current_precedent['title'] = extract_title_from_content(current_content)
                    precedents.append(current_precedent)

                # 새 선례 시작
                current_precedent = {
                    'precedent_num': num,
                    'start_page': page_num,
                }
                current_content = []
                prev_num = num
            else:
                if current_precedent:
                    current_content.append(line)

    # 마지막 선례 저장
    if current_precedent:
        content_text = '\n'.join(current_content).strip()
        current_precedent['description_raw'] = content_text
        current_precedent['title'] = extract_title_from_content(current_content)
        precedents.append(current_precedent)

    return precedents


def parse_na_precedents(pdf_path: str, output_path: str, start_page: int = 40) -> Dict:
    """국회선례집 파싱 메인 함수"""

    print(f"[1/3] PDF 텍스트 추출 중... (시작 페이지: {start_page + 1})")
    pages = extract_text_with_pages(pdf_path, start_page)

    print(f"[2/3] 선례 파싱 중...")
    precedents = parse_precedents(pages)

    print(f"[3/3] 결과 저장 중... ({len(precedents)}개 선례)")

    result = {
        'source': '국회선례집',
        'source_file': str(pdf_path),
        'total_precedents': len(precedents),
        'precedents': precedents
    }

    # JSON 저장
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료! 저장 위치: {output_path}")

    # 통계
    if precedents:
        nums = [p['precedent_num'] for p in precedents]
        print(f"\n=== 통계 ===")
        print(f"선례 번호 범위: {min(nums)} ~ {max(nums)}")
        print(f"파싱된 선례 수: {len(precedents)}")

        # 누락 체크
        expected = set(range(min(nums), max(nums) + 1))
        actual = set(nums)
        missing = expected - actual
        if missing:
            print(f"누락된 번호: {sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}")

    return result


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    PDF_PATH = BASE_DIR / "data" / "raw" / "국회선례집.pdf"
    OUTPUT_PATH = BASE_DIR / "data" / "processed" / "na_precedents.json"

    result = parse_na_precedents(str(PDF_PATH), str(OUTPUT_PATH))

    # 샘플 출력
    print("\n=== 샘플 (처음 5개) ===")
    for prec in result['precedents'][:5]:
        print(f"\n[{prec['precedent_num']}] {prec['title'][:60]}...")
        print(f"  페이지: {prec['start_page']}")
        print(f"  내용 길이: {len(prec.get('description_raw', ''))}")
