# -*- coding: utf-8 -*-
"""
법제처 API 연동 모듈
- 국가법령정보센터 Open API
- 조/항/호/목 구조화된 법령 데이터 가져오기
"""
import re
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


BASE_URL = "https://www.law.go.kr/DRF"
DEFAULT_OC = "chetera"  # Open API 인증키 (테스트용)


def search_law(query: str, oc: str = DEFAULT_OC) -> List[Dict]:
    """법령 검색"""
    url = f"{BASE_URL}/lawSearch.do"
    params = {
        "OC": oc,
        "target": "law",
        "type": "XML",
        "query": query,
        "display": 10
    }

    response = requests.get(url, params=params)
    response.encoding = 'utf-8'

    root = ET.fromstring(response.text)
    laws = []

    for law_elem in root.findall('.//law'):
        law = {
            'mst': law_elem.findtext('법령일련번호'),
            'law_id': law_elem.findtext('법령ID'),
            'name': law_elem.findtext('법령명한글'),
            'promulgation_date': law_elem.findtext('공포일자'),
            'enforcement_date': law_elem.findtext('시행일자'),
            'department': law_elem.findtext('소관부처명'),
        }
        laws.append(law)

    return laws


def fetch_law_detail(mst: str, oc: str = DEFAULT_OC) -> str:
    """법령 상세 정보(XML) 가져오기"""
    url = f"{BASE_URL}/lawService.do"
    params = {
        "OC": oc,
        "target": "law",
        "MST": mst,
        "type": "XML"
    }

    response = requests.get(url, params=params)
    response.encoding = 'utf-8'
    return response.text


def parse_ho(ho_elem: ET.Element) -> Dict:
    """호(Item) 파싱"""
    ho_num = ho_elem.findtext('호번호', '').strip()
    ho_content = ho_elem.findtext('호내용', '').strip()

    # 호번호에서 숫자 추출 (1., 2., ...)
    num_match = re.match(r'(\d+)\.', ho_num)
    num = int(num_match.group(1)) if num_match else ho_num

    result = {
        'type': 'item',
        'number': num,
        'content': ho_content,
        'children': []
    }

    # 목(SubItem) 파싱
    for mok_elem in ho_elem.findall('목'):
        mok = parse_mok(mok_elem)
        result['children'].append(mok)

    return result


def parse_mok(mok_elem: ET.Element) -> Dict:
    """목(SubItem) 파싱"""
    mok_num = mok_elem.findtext('목번호', '').strip()
    mok_content = mok_elem.findtext('목내용', '').strip()

    # 목번호에서 한글 추출 (가., 나., ...)
    char_match = re.match(r'([가-하])\.', mok_num)
    char = char_match.group(1) if char_match else mok_num

    return {
        'type': 'subitem',
        'number': char,
        'content': mok_content
    }


def parse_hang(hang_elem: ET.Element) -> Dict:
    """항(Paragraph) 파싱"""
    hang_num = hang_elem.findtext('항번호', '').strip()
    hang_content = hang_elem.findtext('항내용', '').strip()

    # 항번호에서 숫자 추출 (①, ②, ...)
    circled_numbers = {
        '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
        '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
        '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15,
        '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20,
    }
    num = circled_numbers.get(hang_num, hang_num)

    result = {
        'type': 'paragraph',
        'number': num,
        'content': hang_content,
        'children': []
    }

    # 호(Item) 파싱
    for ho_elem in hang_elem.findall('호'):
        ho = parse_ho(ho_elem)
        result['children'].append(ho)

    return result


def parse_article(article_elem: ET.Element) -> Optional[Dict]:
    """조문 파싱"""
    article_type = article_elem.findtext('조문여부', '')

    # 장/절 구분자는 제외
    if article_type == '전문':
        return None

    article_num = article_elem.findtext('조문번호', '')
    sub_num = article_elem.findtext('조문가지번호', '')
    title = article_elem.findtext('조문제목', '').strip()
    content = article_elem.findtext('조문내용', '').strip()
    reference = article_elem.findtext('조문참고자료', '').strip()

    # 조문 ID 생성: 제1조 -> "1", 제1조의2 -> "1-2"
    if sub_num:
        article_id = f"{article_num}-{sub_num}"
    else:
        article_id = article_num

    result = {
        'article_id': article_id,
        'article_num': int(article_num) if article_num.isdigit() else article_num,
        'sub_num': int(sub_num) if sub_num and sub_num.isdigit() else None,
        'title': title,
        'content': content,
        'reference': reference,
        'paragraphs': []
    }

    # 항(Paragraph) 파싱
    for hang_elem in article_elem.findall('항'):
        hang = parse_hang(hang_elem)
        result['paragraphs'].append(hang)

    return result


def parse_law_xml(xml_text: str) -> Dict:
    """법령 XML 파싱"""
    root = ET.fromstring(xml_text)

    # 기본 정보
    basic_info = root.find('기본정보')
    law_info = {
        'law_id': basic_info.findtext('법령ID', ''),
        'name': basic_info.findtext('법령명_한글', '').strip(),
        'promulgation_date': basic_info.findtext('공포일자', ''),
        'promulgation_no': basic_info.findtext('공포번호', ''),
        'enforcement_date': basic_info.findtext('시행일자', ''),
        'department': basic_info.findtext('소관부처', '').strip(),
        'revision_type': basic_info.findtext('제개정구분', ''),
    }

    # 조문 파싱
    articles = []
    chapters = []  # 장/절 정보
    current_chapter = None

    for article_elem in root.findall('.//조문단위'):
        article_type = article_elem.findtext('조문여부', '')

        # 장/절 구분자
        if article_type == '전문':
            chapter_content = article_elem.findtext('조문내용', '').strip()
            # 장/절 파싱: "제1장 총칙" 등
            chapter_match = re.match(r'제(\d+)([장절관편])[\s\S]*?([가-힣\s]+)', chapter_content)
            if chapter_match:
                current_chapter = {
                    'number': int(chapter_match.group(1)),
                    'type': chapter_match.group(2),  # 장, 절, 관, 편
                    'title': chapter_match.group(3).strip(),
                    'raw': chapter_content
                }
                chapters.append(current_chapter)
            continue

        # 일반 조문
        article = parse_article(article_elem)
        if article:
            if current_chapter:
                article['chapter'] = {
                    'number': current_chapter['number'],
                    'type': current_chapter['type'],
                    'title': current_chapter['title']
                }
            articles.append(article)

    return {
        'info': law_info,
        'chapters': chapters,
        'articles': articles,
        'total_articles': len(articles)
    }


def fetch_national_assembly_act(output_path: str, oc: str = DEFAULT_OC) -> Dict:
    """국회법 가져오기"""

    print("[1/4] 국회법 검색 중...")
    laws = search_law("국회법", oc)

    if not laws:
        raise ValueError("국회법을 찾을 수 없습니다")

    # 정확히 "국회법"인 것 찾기
    na_act = None
    for law in laws:
        if law['name'] == '국회법':
            na_act = law
            break

    if not na_act:
        na_act = laws[0]  # fallback

    print(f"  - 법령일련번호: {na_act['mst']}")
    print(f"  - 공포일자: {na_act['promulgation_date']}")
    print(f"  - 시행일자: {na_act['enforcement_date']}")

    print("[2/4] 법령 상세 정보 가져오는 중...")
    xml_text = fetch_law_detail(na_act['mst'], oc)

    print("[3/4] XML 파싱 중...")
    result = parse_law_xml(xml_text)

    print(f"[4/4] 결과 저장 중... ({result['total_articles']}개 조문)")

    # 메타데이터 추가
    result['source'] = '법제처 국가법령정보센터'
    result['api_mst'] = na_act['mst']

    # JSON 저장
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료! 저장 위치: {output_path}")

    # 통계
    print(f"\n=== 통계 ===")
    print(f"조문 수: {result['total_articles']}")
    print(f"장/절 수: {len(result['chapters'])}")

    # 항/호/목 통계
    total_para = sum(len(a['paragraphs']) for a in result['articles'])
    total_items = sum(
        len(p['children'])
        for a in result['articles']
        for p in a['paragraphs']
    )
    print(f"항 수: {total_para}")
    print(f"호 수: {total_items}")

    return result


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    OUTPUT_PATH = BASE_DIR / "data" / "processed" / "na_act_moleg.json"

    result = fetch_national_assembly_act(str(OUTPUT_PATH))

    # 샘플 출력
    print("\n=== 샘플 (처음 3개 조문) ===")
    for article in result['articles'][:3]:
        print(f"\n[제{article['article_id']}조] {article['title']}")
        if article.get('chapter'):
            print(f"  장: 제{article['chapter']['number']}{article['chapter']['type']} {article['chapter']['title']}")
        print(f"  항 수: {len(article['paragraphs'])}")

        for para in article['paragraphs'][:2]:
            print(f"    {para['number']}항: {para['content'][:50]}...")
            for item in para['children'][:2]:
                print(f"      {item['number']}호: {item['content'][:40]}...")
