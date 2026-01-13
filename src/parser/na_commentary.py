# -*- coding: utf-8 -*-
"""
국회법해설 파싱 모듈 (v0)
- 조문 단위 분할
- law_text / commentary 분리
"""
import re
import json
import fitz
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def extract_text_from_pdf(pdf_path: str, start_page: int = 0, end_page: int = None) -> str:
    """PDF에서 텍스트 추출"""
    doc = fitz.open(pdf_path)
    full_text = []

    if end_page is None:
        end_page = len(doc)
    else:
        end_page = min(end_page, len(doc))

    for page_num in range(start_page, end_page):
        page = doc[page_num]
        text = page.get_text()
        # 페이지 구분자 추가
        full_text.append(f"\n<<PAGE_{page_num + 1}>>\n{text}")

    doc.close()
    return "\n".join(full_text)


def normalize_article_id(article_num: str, sub_num: Optional[str] = None) -> str:
    """조문 번호 정규화: 제1조 -> "1", 제1조의2 -> "1-2" """
    if sub_num:
        return f"{article_num}-{sub_num}"
    return article_num


def find_commentary_marker(text: str) -> int:
    """해설 시작 위치 찾기"""
    markers = [
        r'【\s*해\s*설\s*】',
        r'해\s*설\s*요\s*지',
        r'^\s*해\s*설\s*$',
        r'^\s*1\.\s+[가-힣]',  # 1. 으로 시작하는 해설
        r'^\s*가\.\s+[가-힣]',  # 가. 으로 시작하는 해설
    ]

    for marker in markers:
        match = re.search(marker, text, re.MULTILINE)
        if match:
            return match.start()

    return -1


def parse_articles(text: str) -> List[Dict]:
    """조문 단위로 파싱"""

    # 조문 시작 패턴 (공백/줄바꿈 허용)
    article_pattern = r'^\s*제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*[\(\（]([^)\）]+)[\)\）]'

    articles = []
    lines = text.split('\n')

    current_article = None
    current_content = []
    current_page = 1

    for line in lines:
        # 페이지 마커 확인
        page_match = re.match(r'<<PAGE_(\d+)>>', line)
        if page_match:
            current_page = int(page_match.group(1))
            continue

        # 조문 시작 확인
        article_match = re.match(article_pattern, line)
        if article_match:
            # 이전 조문 저장
            if current_article:
                content_text = '\n'.join(current_content).strip()
                current_article['content_raw'] = content_text

                # law_text / commentary 분리 시도
                marker_pos = find_commentary_marker(content_text)
                if marker_pos > 0:
                    current_article['law_text'] = content_text[:marker_pos].strip()
                    current_article['commentary'] = content_text[marker_pos:].strip()
                else:
                    # 마커 없으면 전체를 commentary로 (조문 원문은 짧으니)
                    current_article['law_text'] = ""
                    current_article['commentary'] = content_text

                articles.append(current_article)

            # 새 조문 시작
            article_num = article_match.group(1)
            sub_num = article_match.group(2)
            title = article_match.group(3).strip()

            current_article = {
                'article_id': normalize_article_id(article_num, sub_num),
                'article_num': int(article_num),
                'sub_num': int(sub_num) if sub_num else None,
                'title': title,
                'start_page': current_page,
            }
            current_content = [line]
        else:
            if current_article:
                current_content.append(line)

    # 마지막 조문 저장
    if current_article:
        content_text = '\n'.join(current_content).strip()
        current_article['content_raw'] = content_text

        marker_pos = find_commentary_marker(content_text)
        if marker_pos > 0:
            current_article['law_text'] = content_text[:marker_pos].strip()
            current_article['commentary'] = content_text[marker_pos:].strip()
        else:
            current_article['law_text'] = ""
            current_article['commentary'] = content_text

        articles.append(current_article)

    return articles


def parse_na_commentary(pdf_path: str, output_path: str, start_page: int = 16, end_page: int = 716) -> Dict:
    """
    국회법해설 파싱 메인 함수

    Args:
        pdf_path: PDF 파일 경로
        output_path: JSON 출력 경로
        start_page: 시작 페이지 (0-indexed), 기본값 16 (17페이지부터)
        end_page: 종료 페이지 (exclusive), 기본값 716 (국정감사법 시작 전까지)
    """

    print(f"[1/3] PDF 텍스트 추출 중... (페이지: {start_page + 1} ~ {end_page})")
    text = extract_text_from_pdf(pdf_path, start_page, end_page)

    print(f"[2/3] 조문 파싱 중...")
    articles = parse_articles(text)

    print(f"[3/3] 결과 저장 중... ({len(articles)}개 조문)")

    result = {
        'source': '국회법해설',
        'source_file': str(pdf_path),
        'total_articles': len(articles),
        'articles': articles
    }

    # JSON 저장
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료! 저장 위치: {output_path}")

    return result


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    PDF_PATH = BASE_DIR / "data" / "raw" / "국회법해설.pdf"
    OUTPUT_PATH = BASE_DIR / "data" / "processed" / "na_commentary.json"

    result = parse_na_commentary(str(PDF_PATH), str(OUTPUT_PATH))

    # 샘플 출력
    print("\n=== 샘플 (처음 3개) ===")
    for article in result['articles'][:3]:
        print(f"\n[{article['article_id']}] {article['title']}")
        print(f"  페이지: {article['start_page']}")
        print(f"  해설 길이: {len(article.get('commentary', ''))}")
