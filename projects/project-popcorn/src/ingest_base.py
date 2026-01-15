"""
Track 1: 열린국회정보 의안목록 API 수집기 (Base Data)

- 엔드포인트: open.assembly.go.kr
- 수집 범위: 20~22대 국회 (약 110,000건)
- 주요 API:
  - TVBPMBILL11: 의안검색 (전체 의안)
  - nzmimeepazxkubdpn: 국회의원 발의법률안
  - ALLBILL: 의안정보 통합
"""
import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# API 설정
API_KEY = os.getenv("OPEN_ASSEMBLY_API_KEY", "")
BASE_URL = "https://open.assembly.go.kr/portal/openapi"

# 출력 경로
DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "bills"


def get_bill_list(
    age: int = 22,
    p_index: int = 1,
    p_size: int = 10
) -> dict | None:
    """
    의안목록 조회 (TVBPMBILL11)

    Args:
        age: 대수 (20, 21, 22 등)
        p_index: 페이지 번호
        p_size: 페이지당 건수

    Returns:
        API 응답 dict 또는 None
    """
    endpoint = f"{BASE_URL}/TVBPMBILL11"

    params = {
        "Key": API_KEY,
        "Type": "json",
        "pIndex": p_index,
        "pSize": p_size,
        "AGE": age,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API 요청 실패: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 실패: {e}")
        print(f"[DEBUG] Response: {response.text[:500]}")
        return None


def get_proposer_bills(
    age: int = 22,
    p_index: int = 1,
    p_size: int = 10
) -> dict | None:
    """
    국회의원 발의법률안 조회 (nzmimeepazxkubdpn)
    - 대표발의자/공동발의자 구분 가능

    Args:
        age: 대수 (20, 21, 22 등)
        p_index: 페이지 번호
        p_size: 페이지당 건수

    Returns:
        API 응답 dict 또는 None
    """
    endpoint = f"{BASE_URL}/nzmimeepazxkubdpn"

    params = {
        "Key": API_KEY,
        "Type": "json",
        "pIndex": p_index,
        "pSize": p_size,
        "AGE": age,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API 요청 실패: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 실패: {e}")
        print(f"[DEBUG] Response: {response.text[:500]}")
        return None


def save_bills(bills: list[dict], age: int, api_name: str = "bills"):
    """의안 데이터 저장"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DATA_DIR / f"{api_name}_{age}th.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(bills, f, ensure_ascii=False, indent=2)

    print(f"[INFO] {len(bills)}건 저장 완료: {output_path}")


def test_api_connection():
    """API 연결 테스트"""
    print("=" * 60)
    print("열린국회정보 의안목록 API 연동 테스트")
    print("=" * 60)
    print(f"[INFO] API Key (앞 10자): {API_KEY[:10]}...")
    print(f"[INFO] Base URL: {BASE_URL}")
    print()

    # 1. TVBPMBILL11 (의안검색) 테스트
    print("[TEST 1] TVBPMBILL11 - 22대 국회 의안검색 (5건)...")
    print("-" * 60)
    result = get_bill_list(age=22, p_size=5)

    if result is None:
        print("[FAIL] API 응답 없음")
        return False

    # 응답 구조 확인 (열린국회정보 API 응답 형식)
    api_data = result.get("TVBPMBILL11", [])

    if not api_data:
        print(f"[FAIL] 응답 데이터 없음")
        print(f"[DEBUG] Response keys: {result.keys()}")
        return False

    # 첫 번째 요소는 메타데이터
    head = api_data[0].get("head", [{}])
    total_count = head[0].get("list_total_count", 0) if head else 0

    # 두 번째 요소는 실제 데이터
    rows = api_data[1].get("row", []) if len(api_data) > 1 else []

    print(f"[INFO] 전체 의안 수: {total_count:,}건")
    print(f"[INFO] 조회된 의안 수: {len(rows)}건")
    print()

    # 샘플 데이터 출력
    print("[SAMPLE] 의안 목록:")
    for i, item in enumerate(rows[:3], 1):
        print(f"{i}. {item.get('BILL_NAME', 'N/A')}")
        print(f"   - 의안번호: {item.get('BILL_NO', 'N/A')}")
        print(f"   - 의안ID: {item.get('BILL_ID', 'N/A')}")
        print(f"   - 제안자: {item.get('PROPOSER', 'N/A')}")
        print(f"   - 소관위: {item.get('CURR_COMMITTEE', 'N/A')}")
        print(f"   - 처리상태: {item.get('PROC_RESULT', 'N/A')}")
        print()

    # 2. 국회의원 발의법률안 API 테스트
    print("=" * 60)
    print("[TEST 2] nzmimeepazxkubdpn - 국회의원 발의법률안 (5건)...")
    print("-" * 60)
    result2 = get_proposer_bills(age=22, p_size=5)

    if result2:
        api_data2 = result2.get("nzmimeepazxkubdpn", [])
        if api_data2 and len(api_data2) > 1:
            rows2 = api_data2[1].get("row", [])
            head2 = api_data2[0].get("head", [{}])
            total2 = head2[0].get("list_total_count", 0) if head2 else 0

            print(f"[INFO] 전체 발의법률안 수: {total2:,}건")
            print()
            for i, item in enumerate(rows2[:2], 1):
                print(f"{i}. {item.get('BILL_NAME', 'N/A')}")
                print(f"   - 대표발의자: {item.get('RST_PROPOSER', 'N/A')}")
                print(f"   - 공동발의자수: {item.get('PUBL_PROPOSER', 'N/A')}")
                print()
    else:
        print("[WARN] 발의법률안 API 응답 없음")

    print("=" * 60)
    print("[SUCCESS] API 연동 테스트 완료!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_api_connection()
