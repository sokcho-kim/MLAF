# -*- coding: utf-8 -*-
"""
법률 조/항/호/목 계층 구조 파싱 모듈

법률 구조:
- 조(Article): 제1조, 제2조...
- 항(Paragraph): ①, ②, ③... 또는 ⑴, ⑵, ⑶...
- 호(Item): 1., 2., 3...
- 목(SubItem): 가., 나., 다...
"""
import re
from typing import List, Dict, Optional, Tuple
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


# 원문자 숫자 매핑
CIRCLED_NUMBERS = {
    '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
    '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
    '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15,
    '⑯': 16, '⑰': 17, '⑱': 18, '⑲': 19, '⑳': 20,
}

PARENTHESIZED_NUMBERS = {
    '⑴': 1, '⑵': 2, '⑶': 3, '⑷': 4, '⑸': 5,
    '⑹': 6, '⑺': 7, '⑻': 8, '⑼': 9, '⑽': 10,
    '⑾': 11, '⑿': 12, '⒀': 13, '⒁': 14, '⒂': 15,
}

KOREAN_CHARS = ['가', '나', '다', '라', '마', '바', '사', '아', '자', '차', '카', '타', '파', '하']


def detect_paragraph(text: str) -> Optional[Tuple[int, int]]:
    """
    항(Paragraph) 감지
    Returns: (항 번호, 시작 위치) 또는 None
    """
    # 원문자 항: ① ② ③...
    for char, num in CIRCLED_NUMBERS.items():
        match = re.search(rf'^{re.escape(char)}\s*', text)
        if match:
            return num, match.end()

    # 괄호 숫자 항: ⑴ ⑵ ⑶...
    for char, num in PARENTHESIZED_NUMBERS.items():
        match = re.search(rf'^{re.escape(char)}\s*', text)
        if match:
            return num, match.end()

    return None


def detect_item(text: str) -> Optional[Tuple[int, int]]:
    """
    호(Item) 감지
    Returns: (호 번호, 시작 위치) 또는 None
    """
    # 숫자 + 마침표: 1. 2. 3...
    match = re.match(r'^(\d+)\.\s*', text)
    if match:
        return int(match.group(1)), match.end()

    return None


def detect_subitem(text: str) -> Optional[Tuple[str, int]]:
    """
    목(SubItem) 감지
    Returns: (목 문자, 시작 위치) 또는 None
    """
    # 한글 + 마침표: 가. 나. 다...
    match = re.match(r'^([가-하])\.\s*', text)
    if match:
        char = match.group(1)
        if char in KOREAN_CHARS:
            return char, match.end()

    return None


def parse_law_structure(text: str) -> List[Dict]:
    """
    법률 텍스트를 조/항/호/목 계층 구조로 파싱

    Returns:
        List of structure elements:
        {
            'type': 'paragraph' | 'item' | 'subitem',
            'number': 1 | '가',
            'content': '내용',
            'children': [...]
        }
    """
    lines = text.split('\n')
    structures = []

    current_paragraph = None
    current_item = None
    current_subitem = None
    buffer = []

    def flush_buffer():
        """버퍼 내용을 현재 구조에 추가"""
        nonlocal buffer
        if buffer:
            content = ' '.join(buffer).strip()
            if current_subitem:
                current_subitem['content'] += ' ' + content
            elif current_item:
                current_item['content'] += ' ' + content
            elif current_paragraph:
                current_paragraph['content'] += ' ' + content
            buffer = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 항 감지
        para_result = detect_paragraph(line)
        if para_result:
            flush_buffer()
            num, pos = para_result

            # 이전 항 저장
            if current_paragraph:
                if current_item:
                    if current_subitem:
                        current_item['children'].append(current_subitem)
                        current_subitem = None
                    current_paragraph['children'].append(current_item)
                    current_item = None
                structures.append(current_paragraph)

            current_paragraph = {
                'type': 'paragraph',
                'number': num,
                'content': line[pos:].strip(),
                'children': []
            }
            continue

        # 호 감지
        item_result = detect_item(line)
        if item_result:
            flush_buffer()
            num, pos = item_result

            # 이전 호 저장
            if current_item:
                if current_subitem:
                    current_item['children'].append(current_subitem)
                    current_subitem = None
                if current_paragraph:
                    current_paragraph['children'].append(current_item)

            current_item = {
                'type': 'item',
                'number': num,
                'content': line[pos:].strip(),
                'children': []
            }
            continue

        # 목 감지
        subitem_result = detect_subitem(line)
        if subitem_result:
            flush_buffer()
            char, pos = subitem_result

            # 이전 목 저장
            if current_subitem and current_item:
                current_item['children'].append(current_subitem)

            current_subitem = {
                'type': 'subitem',
                'number': char,
                'content': line[pos:].strip(),
            }
            continue

        # 일반 텍스트
        buffer.append(line)

    # 마지막 요소들 저장
    flush_buffer()
    if current_subitem and current_item:
        current_item['children'].append(current_subitem)
    if current_item and current_paragraph:
        current_paragraph['children'].append(current_item)
    if current_paragraph:
        structures.append(current_paragraph)

    return structures


def extract_law_text_structure(article_content: str) -> Dict:
    """
    조문 내용에서 법조문(law_text)과 해설(commentary) 분리 후
    법조문을 항/호/목 구조로 파싱

    Returns:
        {
            'law_text': '원문',
            'law_structure': [...],  # 구조화된 법조문
            'commentary': '해설'
        }
    """
    # 해설 시작 마커 찾기
    markers = [
        r'【\s*해\s*설\s*】',
        r'해\s*설\s*요\s*지',
        r'\n\s*1\.\s+[가-힣]{2,}의\s+의의',  # "1. OO의 의의"
        r'\n\s*1\.\s+의\s*의',  # "1. 의의"
    ]

    split_pos = len(article_content)
    for marker in markers:
        match = re.search(marker, article_content)
        if match:
            split_pos = min(split_pos, match.start())
            break

    law_text = article_content[:split_pos].strip()
    commentary = article_content[split_pos:].strip()

    # 법조문 구조 파싱
    law_structure = parse_law_structure(law_text)

    return {
        'law_text': law_text,
        'law_structure': law_structure,
        'commentary': commentary
    }


# 테스트
if __name__ == "__main__":
    test_text = """① 국회는 헌법에 특별한 규정이 있는 경우를 제외하고는 재적의원 과반수의 출석과 출석의원 과반수의 찬성으로 의결한다.
② 가부동수인 때에는 부결된 것으로 본다.
③ 다음 각 호의 어느 하나에 해당하는 경우에는 재적의원 3분의 2 이상의 찬성이 필요하다.
1. 헌법개정안의 의결
2. 국회의원 제명
3. 대통령 탄핵소추의 의결
가. 탄핵소추의 발의
나. 탄핵소추의 의결"""

    result = parse_law_structure(test_text)

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
