"""
부처별 하부 조직명 수집

- 각 부처 직제(대통령령)에서 실/국/과 명칭 추출
- R&R 데이터 증강용
"""
import os
import json
import requests
import xml.etree.ElementTree as ET
import re
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
import time

load_dotenv()

BASE_URL = "https://www.law.go.kr/DRF"
DEFAULT_OC = "chetera"

# 부처별 직제 검색 키워드 (2025.10.1 개정 반영)
MINISTRY_ORG_KEYWORDS = {
    "재정경제부": "기획재정부와 그 소속기관 직제",  # 개정 전 이름으로 검색
    "과학기술정보통신부": "과학기술정보통신부와 그 소속기관 직제",
    "교육부": "교육부와 그 소속기관 직제",
    "외교부": "외교부와 그 소속기관 직제",
    "통일부": "통일부와 그 소속기관 직제",
    "법무부": "법무부와 그 소속기관 직제",
    "국방부": "국방부와 그 소속기관 직제",
    "행정안전부": "행정안전부와 그 소속기관 직제",
    "국가보훈부": "국가보훈부와 그 소속기관 직제",
    "문화체육관광부": "문화체육관광부와 그 소속기관 직제",
    "농림축산식품부": "농림축산식품부와 그 소속기관 직제",
    "산업통상부": "산업통상자원부 직제",  # 수정
    "보건복지부": "보건복지부와 그 소속기관 직제",
    "기후에너지환경부": "환경부와 그 소속기관 직제",
    "고용노동부": "고용노동부와 그 소속기관 직제",
    "성평등가족부": "여성가족부 직제",  # 수정
    "국토교통부": "국토교통부와 그 소속기관 직제",
    "해양수산부": "해양수산부와 그 소속기관 직제",
    "식품의약품안전처": "식품의약품안전처와 그 소속기관 직제",
    "국가데이터처": "통계청 직제",  # 수정
    "지식재산처": "특허청 직제",  # 수정
}


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

    try:
        response = requests.get(url, params=params, timeout=30)
        response.encoding = 'utf-8'

        root = ET.fromstring(response.text)
        laws = []

        for law_elem in root.findall('.//law'):
            law = {
                'mst': law_elem.findtext('법령일련번호'),
                'law_id': law_elem.findtext('법령ID'),
                'name': law_elem.findtext('법령명한글'),
            }
            laws.append(law)

        return laws

    except Exception as e:
        print(f"[ERROR] 검색 실패: {e}")
        return []


def fetch_law_detail(mst: str, oc: str = DEFAULT_OC) -> Optional[str]:
    """법령 상세 정보(XML) 가져오기"""
    url = f"{BASE_URL}/lawService.do"
    params = {
        "OC": oc,
        "target": "law",
        "MST": mst,
        "type": "XML"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        print(f"[ERROR] 상세 조회 실패: {e}")
        return None


def extract_org_names(xml_text: str) -> List[str]:
    """
    직제 XML에서 조직명 추출
    - 실, 국, 과, 담당관, 센터 등
    """
    org_names = []

    # 패턴: ~실, ~국, ~과, ~담당관, ~센터, ~팀
    patterns = [
        r'([가-힣]+(?:실|국|과|담당관|센터|팀|본부|단))\b',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, xml_text)
        org_names.extend(matches)

    # 중복 제거 및 정리
    org_names = list(set(org_names))

    # 불필요한 항목 제거
    exclude_words = ['조', '항', '호', '목', '제', '법', '령', '규칙', '시행', '부칙', '본문']
    org_names = [name for name in org_names if not any(ex in name for ex in exclude_words)]

    # 너무 짧은 것 제거 (2글자 이하)
    org_names = [name for name in org_names if len(name) > 2]

    return sorted(org_names)


def fetch_ministry_orgs(ministry_name: str) -> Dict:
    """
    특정 부처의 하부 조직명 수집
    """
    search_keyword = MINISTRY_ORG_KEYWORDS.get(ministry_name)
    if not search_keyword:
        return {"ministry": ministry_name, "orgs": [], "error": "검색 키워드 없음"}

    # 1. 직제 검색
    laws = search_law(search_keyword)

    if not laws:
        return {"ministry": ministry_name, "orgs": [], "error": "직제 검색 실패"}

    # 정확한 직제 찾기
    target_law = None
    for law in laws:
        if "직제" in law['name'] and "시행" not in law['name']:
            target_law = law
            break

    if not target_law:
        target_law = laws[0]

    # 2. 직제 상세 조회
    xml_text = fetch_law_detail(target_law['mst'])
    if not xml_text:
        return {"ministry": ministry_name, "orgs": [], "error": "직제 조회 실패"}

    # 3. 조직명 추출
    org_names = extract_org_names(xml_text)

    return {
        "ministry": ministry_name,
        "law_name": target_law['name'],
        "orgs": org_names,
        "count": len(org_names)
    }


def collect_all_ministry_orgs() -> Dict:
    """
    모든 부처의 하부 조직명 수집
    """
    print("=" * 60)
    print("부처별 하부 조직명 수집")
    print("=" * 60)

    results = {}

    for ministry_name in MINISTRY_ORG_KEYWORDS.keys():
        print(f"\n[수집] {ministry_name}...")
        result = fetch_ministry_orgs(ministry_name)

        if result.get('error'):
            print(f"  [WARN] {result['error']}")
        else:
            print(f"  직제: {result.get('law_name', 'N/A')}")
            print(f"  조직 수: {result['count']}개")
            if result['orgs']:
                print(f"  샘플: {', '.join(result['orgs'][:5])}...")

        results[ministry_name] = result.get('orgs', [])
        time.sleep(0.5)  # API 부하 방지

    return results


def save_ministry_orgs(data: Dict, output_path: str):
    """결과 저장"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")


if __name__ == "__main__":
    # 전체 수집 실행
    ministry_orgs = collect_all_ministry_orgs()

    # 저장
    output_path = Path(__file__).parent.parent / "data" / "ministry_orgs.json"
    save_ministry_orgs(ministry_orgs, str(output_path))

    # 통계 출력
    print("\n" + "=" * 60)
    print("수집 결과 요약")
    print("=" * 60)
    total = 0
    for ministry, orgs in ministry_orgs.items():
        count = len(orgs)
        total += count
        print(f"  {ministry}: {count}개")
    print(f"\n총 조직명: {total}개")
