# -*- coding: utf-8 -*-
"""
국회법 관련 법률 일괄 수집
- 법제처 API 활용
- 국회법해설 PDF에 포함된 법률들
"""
import json
from pathlib import Path
from typing import List, Dict
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from moleg_api import search_law, fetch_law_detail, parse_law_xml


# 국회법해설에 포함된 법률 목록
RELATED_LAWS = [
    {
        'name': '국회법',
        'query': '국회법',
        'output': 'na_act_moleg.json',
        'pdf_pages': '17~716'
    },
    {
        'name': '국정감사 및 조사에 관한 법률',
        'query': '국정감사',
        'output': 'inspection_act_moleg.json',
        'pdf_pages': '717~780'
    },
    {
        'name': '국회에서의 증언·감정 등에 관한 법률',
        'query': '국회에서의 증언',
        'output': 'testimony_act_moleg.json',
        'pdf_pages': '781~849'
    },
    {
        'name': '인사청문회법',
        'query': '인사청문회법',
        'output': 'hearing_act_moleg.json',
        'pdf_pages': '850~907'
    }
]


def fetch_law_by_name(law_name: str, query: str) -> Dict:
    """법률명으로 검색 후 상세 정보 가져오기"""
    print(f"\n=== {law_name} ===")

    # 검색
    print(f"  [1/3] 검색 중... (query: {query})")
    laws = search_law(query)

    if not laws:
        print(f"  [ERROR] 법률을 찾을 수 없습니다")
        return None

    # 정확한 법률 찾기
    target = None
    for law in laws:
        if law['name'] == law_name:
            target = law
            break

    if not target:
        # 정확히 일치하는 게 없으면 첫 번째 결과 사용
        target = laws[0]
        print(f"  [WARN] 정확히 일치하는 법률 없음, 첫 번째 결과 사용: {target['name']}")

    print(f"  - 법령일련번호: {target['mst']}")
    print(f"  - 공포일자: {target['promulgation_date']}")

    # 상세 정보 가져오기
    print(f"  [2/3] 상세 정보 가져오는 중...")
    xml_text = fetch_law_detail(target['mst'])

    # 파싱
    print(f"  [3/3] 파싱 중...")
    result = parse_law_xml(xml_text)
    result['source'] = '법제처 국가법령정보센터'
    result['api_mst'] = target['mst']

    print(f"  - 조문 수: {result['total_articles']}")
    print(f"  - 장/절 수: {len(result['chapters'])}")

    return result


def fetch_all_related_laws(output_dir: str) -> Dict:
    """관련 법률 일괄 수집"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    summary = {
        'total_laws': 0,
        'total_articles': 0,
        'laws': []
    }

    for law_info in RELATED_LAWS:
        result = fetch_law_by_name(law_info['name'], law_info['query'])

        if result:
            # 저장
            output_path = output_dir / law_info['output']
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            results[law_info['name']] = result

            # 통계
            summary['total_laws'] += 1
            summary['total_articles'] += result['total_articles']
            summary['laws'].append({
                'name': law_info['name'],
                'articles': result['total_articles'],
                'chapters': len(result['chapters']),
                'pdf_pages': law_info['pdf_pages'],
                'output': law_info['output']
            })

            print(f"  저장 완료: {output_path}")

    # 요약 저장
    summary_path = output_dir / 'related_laws_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    OUTPUT_DIR = BASE_DIR / "data" / "processed"

    print("=" * 50)
    print("국회법 관련 법률 일괄 수집")
    print("=" * 50)

    summary = fetch_all_related_laws(str(OUTPUT_DIR))

    print("\n" + "=" * 50)
    print("수집 완료")
    print("=" * 50)

    print(f"\n총 {summary['total_laws']}개 법률, {summary['total_articles']}개 조문")
    print("\n법률별 현황:")
    for law in summary['laws']:
        print(f"  - {law['name']}: {law['articles']}개 조문, {law['chapters']}개 장/절")
