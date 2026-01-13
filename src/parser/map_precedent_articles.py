# -*- coding: utf-8 -*-
"""
선례-조문 매핑 모듈
- 선례 텍스트에서 법률 조문 참조 추출
- 국회법, 헌법, 국정감사법 등 조문과 매핑
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import Counter
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


# 법률 약어 매핑
LAW_ABBREVIATIONS = {
    '국': '국회법',
    '헌': '헌법',
    '공선': '공직선거법',
    '국감': '국정감사 및 조사에 관한 법률',
    '국감조': '국정감사 및 조사에 관한 법률',
    '증언': '국회에서의 증언·감정 등에 관한 법률',
    '인청': '인사청문회법',
}


def extract_law_references(text: str) -> List[Dict]:
    """
    텍스트에서 법률 조문 참조 추출

    패턴 예시:
    - 국 2 → 국회법 제2조
    - 헌 47① → 헌법 제47조 제1항
    - 국감조 3 → 국정감사법 제3조
    - 공선188,189 → 공직선거법 제188조, 제189조
    """
    references = []

    # 패턴 1: 약어 + 숫자 (국 2, 헌 47 등)
    # 여러 조문 참조도 처리 (공선188,189)
    pattern = r'(' + '|'.join(re.escape(k) for k in sorted(LAW_ABBREVIATIONS.keys(), key=len, reverse=True)) + r')\s*(\d+(?:\s*[,·]\s*\d+)*)'

    for match in re.finditer(pattern, text):
        abbr = match.group(1)
        numbers_str = match.group(2)

        law_name = LAW_ABBREVIATIONS.get(abbr, abbr)

        # 여러 조문 번호 분리
        numbers = re.split(r'\s*[,·]\s*', numbers_str)
        for num in numbers:
            if num.isdigit():
                references.append({
                    'law': law_name,
                    'article': int(num),
                    'raw': match.group(0)
                })

    # 패턴 2: "제N조" 형태 직접 참조
    pattern2 = r'(?:국회법|헌법)\s*제\s*(\d+)\s*조'
    for match in re.finditer(pattern2, text):
        law_name = '국회법' if '국회법' in match.group(0) else '헌법'
        references.append({
            'law': law_name,
            'article': int(match.group(1)),
            'raw': match.group(0)
        })

    # 중복 제거
    seen = set()
    unique_refs = []
    for ref in references:
        key = (ref['law'], ref['article'])
        if key not in seen:
            seen.add(key)
            unique_refs.append(ref)

    return unique_refs


def map_precedents_to_articles(
    precedents_path: str,
    output_path: str
) -> Dict:
    """선례-조문 매핑 수행"""

    print("[1/3] 선례 데이터 로드 중...")
    with open(precedents_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    precedents = data['precedents']

    print(f"[2/3] 조문 참조 추출 중... ({len(precedents)}개 선례)")

    # 매핑 결과
    mapped_precedents = []
    all_references = []
    law_stats = Counter()

    for prec in precedents:
        text = prec.get('description_raw', '') + ' ' + prec.get('title', '')
        refs = extract_law_references(text)

        mapped = {
            **prec,
            'law_references': refs,
            'referenced_laws': list(set(r['law'] for r in refs)),
            'referenced_articles': [
                {'law': r['law'], 'article': r['article']}
                for r in refs
            ]
        }
        mapped_precedents.append(mapped)

        # 통계
        for ref in refs:
            all_references.append(ref)
            law_stats[ref['law']] += 1

    print(f"[3/3] 결과 저장 중...")

    # 국회법 조문별 선례 역매핑
    article_to_precedents = {}
    for prec in mapped_precedents:
        for ref in prec['law_references']:
            if ref['law'] == '국회법':
                art_id = str(ref['article'])
                if art_id not in article_to_precedents:
                    article_to_precedents[art_id] = []
                article_to_precedents[art_id].append({
                    'precedent_num': prec['precedent_num'],
                    'title': prec['title'][:50] + '...' if len(prec['title']) > 50 else prec['title']
                })

    result = {
        'source': '국회선례집',
        'total_precedents': len(mapped_precedents),
        'total_references': len(all_references),
        'law_reference_stats': dict(law_stats),
        'precedents': mapped_precedents,
        'article_to_precedents': article_to_precedents
    }

    # JSON 저장
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"완료! 저장 위치: {output_path}")

    # 통계 출력
    print(f"\n=== 매핑 통계 ===")
    print(f"전체 선례: {len(mapped_precedents)}개")
    print(f"전체 조문 참조: {len(all_references)}개")
    print(f"\n법률별 참조 횟수:")
    for law, count in law_stats.most_common():
        print(f"  - {law}: {count}회")

    # 국회법 조문별 선례 수
    na_articles = article_to_precedents
    print(f"\n국회법 조문별 선례 수: {len(na_articles)}개 조문")
    print("선례가 많은 조문 TOP 10:")
    sorted_articles = sorted(na_articles.items(), key=lambda x: len(x[1]), reverse=True)
    for art_id, precs in sorted_articles[:10]:
        print(f"  - 제{art_id}조: {len(precs)}개 선례")

    return result


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent

    PRECEDENTS_PATH = BASE_DIR / "data" / "processed" / "na_precedents.json"
    OUTPUT_PATH = BASE_DIR / "data" / "processed" / "precedent_article_map.json"

    result = map_precedents_to_articles(str(PRECEDENTS_PATH), str(OUTPUT_PATH))

    # 샘플 출력
    print("\n=== 샘플 (처음 3개) ===")
    for prec in result['precedents'][:3]:
        print(f"\n[선례 {prec['precedent_num']}] {prec['title'][:50]}...")
        print(f"  참조 법률: {prec['referenced_laws']}")
        for ref in prec['law_references'][:3]:
            print(f"    - {ref['law']} 제{ref['article']}조")
