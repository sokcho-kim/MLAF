"""
부처별 소관 법령 목록 수집

- 법제처 API를 활용하여 각 부처 소관 법령 조회
- R&R 데이터 증강용
"""
import os
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
import time

load_dotenv()

BASE_URL = "https://www.law.go.kr/DRF"
DEFAULT_OC = "chetera"

# 부처명 매핑 (정부조직법 기준 → API 검색용)
MINISTRY_SEARCH_NAMES = {
    "재정경제부": ["재정경제부", "기획재정부"],  # 2025년 개정으로 변경
    "과학기술정보통신부": ["과학기술정보통신부"],
    "교육부": ["교육부"],
    "외교부": ["외교부"],
    "통일부": ["통일부"],
    "법무부": ["법무부"],
    "국방부": ["국방부"],
    "행정안전부": ["행정안전부"],
    "국가보훈부": ["국가보훈부", "국가보훈처"],
    "문화체육관광부": ["문화체육관광부"],
    "농림축산식품부": ["농림축산식품부"],
    "산업통상부": ["산업통상부", "산업통상자원부"],  # 2025년 개정으로 변경
    "보건복지부": ["보건복지부"],
    "기후에너지환경부": ["기후에너지환경부", "환경부"],  # 2025년 개정으로 변경
    "고용노동부": ["고용노동부"],
    "성평등가족부": ["성평등가족부", "여성가족부"],  # 2025년 개정으로 변경
    "국토교통부": ["국토교통부"],
    "해양수산부": ["해양수산부"],
    "식품의약품안전처": ["식품의약품안전처"],
    "국가데이터처": ["국가데이터처", "통계청"],
    "지식재산처": ["지식재산처", "특허청"],
}


def search_laws_by_department(dept_name: str, oc: str = DEFAULT_OC, max_results: int = 100) -> List[Dict]:
    """
    소관부처명으로 법령 검색

    Args:
        dept_name: 소관부처명
        oc: API 인증키
        max_results: 최대 검색 결과 수

    Returns:
        법령 목록
    """
    url = f"{BASE_URL}/lawSearch.do"
    params = {
        "OC": oc,
        "target": "law",
        "type": "XML",
        "org": dept_name,  # 소관부처로 검색 시도
        "display": max_results
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.encoding = 'utf-8'

        root = ET.fromstring(response.text)
        laws = []

        for law_elem in root.findall('.//law'):
            law = {
                'law_id': law_elem.findtext('법령ID', ''),
                'name': law_elem.findtext('법령명한글', ''),
                'department': law_elem.findtext('소관부처명', ''),
                'enforcement_date': law_elem.findtext('시행일자', ''),
            }
            laws.append(law)

        return laws

    except Exception as e:
        print(f"[ERROR] {dept_name} 검색 실패: {e}")
        return []


def search_laws_by_query(query: str, oc: str = DEFAULT_OC, max_results: int = 50) -> List[Dict]:
    """
    키워드로 법령 검색
    """
    url = f"{BASE_URL}/lawSearch.do"
    params = {
        "OC": oc,
        "target": "law",
        "type": "XML",
        "query": query,
        "display": max_results
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.encoding = 'utf-8'

        root = ET.fromstring(response.text)
        laws = []

        for law_elem in root.findall('.//law'):
            law = {
                'law_id': law_elem.findtext('법령ID', ''),
                'name': law_elem.findtext('법령명한글', ''),
                'department': law_elem.findtext('소관부처명', ''),
            }
            laws.append(law)

        return laws

    except Exception as e:
        print(f"[ERROR] '{query}' 검색 실패: {e}")
        return []


def get_all_current_laws(oc: str = DEFAULT_OC) -> List[Dict]:
    """
    현행 법률 전체 목록 조회 (법률만, 시행령/시행규칙 제외)
    """
    url = f"{BASE_URL}/lawSearch.do"
    all_laws = []
    page = 1

    while True:
        params = {
            "OC": oc,
            "target": "law",
            "type": "XML",
            "display": 100,
            "page": page,
            "sort": "efcdt",  # 시행일자순
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.encoding = 'utf-8'

            root = ET.fromstring(response.text)
            total_cnt = int(root.findtext('totalCnt', '0'))

            laws = root.findall('.//law')
            if not laws:
                break

            for law_elem in laws:
                law_name = law_elem.findtext('법령명한글', '')
                # 법률만 필터링 (시행령, 시행규칙 제외)
                if '시행령' in law_name or '시행규칙' in law_name:
                    continue

                law = {
                    'law_id': law_elem.findtext('법령ID', ''),
                    'name': law_name,
                    'department': law_elem.findtext('소관부처명', ''),
                }
                all_laws.append(law)

            print(f"  페이지 {page}: {len(laws)}건 조회 (누적: {len(all_laws)}건)")

            if page * 100 >= total_cnt:
                break

            page += 1
            time.sleep(0.5)  # API 부하 방지

        except Exception as e:
            print(f"[ERROR] 페이지 {page} 조회 실패: {e}")
            break

    return all_laws


def filter_laws_by_ministry(all_laws: List[Dict], ministry_name: str) -> List[str]:
    """
    전체 법령에서 특정 부처 소관 법령 필터링
    """
    search_names = MINISTRY_SEARCH_NAMES.get(ministry_name, [ministry_name])

    ministry_laws = []
    for law in all_laws:
        dept = law.get('department', '')
        for search_name in search_names:
            if search_name in dept:
                ministry_laws.append(law['name'])
                break

    return ministry_laws


def collect_ministry_laws():
    """
    모든 부처의 소관 법령 목록 수집
    """
    print("=" * 60)
    print("부처별 소관 법령 목록 수집")
    print("=" * 60)

    # 1. 현행 법률 전체 목록 조회
    print("\n[1/2] 현행 법률 전체 목록 조회 중...")
    all_laws = get_all_current_laws()
    print(f"  총 {len(all_laws)}개 법률 조회 완료")

    # 2. 부처별 필터링
    print("\n[2/2] 부처별 소관 법령 필터링 중...")
    ministry_laws = {}

    for ministry_name in MINISTRY_SEARCH_NAMES.keys():
        laws = filter_laws_by_ministry(all_laws, ministry_name)
        ministry_laws[ministry_name] = laws
        print(f"  {ministry_name}: {len(laws)}개 법령")

    return ministry_laws


def test_api():
    """API 테스트"""
    print("=" * 60)
    print("법제처 API 테스트")
    print("=" * 60)

    # 산업통상자원부 관련 법령 검색 테스트
    print("\n[TEST] '반도체' 키워드 검색...")
    laws = search_laws_by_query("반도체")
    print(f"  검색 결과: {len(laws)}건")
    for law in laws[:5]:
        print(f"    - {law['name']} ({law['department']})")

    print("\n[TEST] '산업' 키워드 검색...")
    laws = search_laws_by_query("산업")
    print(f"  검색 결과: {len(laws)}건")

    # 소관부처별 카운트
    dept_count = {}
    for law in laws:
        dept = law['department']
        dept_count[dept] = dept_count.get(dept, 0) + 1

    print("  소관부처별:")
    for dept, count in sorted(dept_count.items(), key=lambda x: -x[1])[:10]:
        print(f"    {dept}: {count}건")


def save_ministry_laws(ministry_laws: Dict, output_path: str):
    """결과 저장"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ministry_laws, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")


if __name__ == "__main__":
    # 전체 수집 실행
    ministry_laws = collect_ministry_laws()

    # 저장
    output_path = Path(__file__).parent.parent / "data" / "ministry_laws.json"
    save_ministry_laws(ministry_laws, str(output_path))
