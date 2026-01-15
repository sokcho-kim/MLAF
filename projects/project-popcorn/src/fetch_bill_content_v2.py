"""
법안 제안이유/주요내용 수집 v2

BillInfoService2 API에서 전체 법안 목록을 가져와서
bill_no로 매칭하여 summary 필드 추출
"""
import os
import json
import requests
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from dotenv import load_dotenv
import time

load_dotenv()

API_KEY = unquote(os.getenv("DATA_GO_KR_API_KEY", ""))
BASE_URL = "http://apis.data.go.kr/9710000/BillInfoService2"
DATA_DIR = Path(__file__).parent.parent / "data"


def fetch_all_bills_with_summary(max_pages: int = 200, age: int = 22) -> dict:
    """
    전체 법률안 목록과 summary 수집

    Args:
        max_pages: 최대 페이지 수
        age: 대수 (22 = 22대 국회)

    Returns:
        {bill_no: {"bill_id": ..., "bill_name": ..., "summary": ...}, ...}
    """
    print("=" * 60)
    print(f"법률안 목록 수집 (summary 포함, {age}대 국회)")
    print("=" * 60)

    endpoint = f"{BASE_URL}/getBillInfoList"
    bills_by_no = {}

    page = 1
    rows_per_page = 100

    while page <= max_pages:
        params = {
            "ServiceKey": API_KEY,
            "end_ord": age,  # 22대 국회까지
            "ord": "D01",  # 최신순 정렬
            "numOfRows": rows_per_page,
            "pageNo": page,
        }

        try:
            r = requests.get(endpoint, params=params, timeout=30)

            if r.status_code != 200:
                print(f"[Page {page}] HTTP {r.status_code}")
                break

            root = ET.fromstring(r.text)
            items = root.findall(".//item")

            if not items:
                print(f"[Page {page}] 더 이상 결과 없음")
                break

            for item in items:
                bill_no = item.findtext("billNo", "")
                bill_id = item.findtext("billId", "")
                bill_name = item.findtext("billName", "")
                summary = item.findtext("summary", "")

                if bill_no:
                    bills_by_no[bill_no] = {
                        "bill_id": bill_id,
                        "bill_name": bill_name,
                        "summary": summary,
                    }

            if page % 10 == 0:
                print(f"[Page {page}] 수집: {len(bills_by_no)}건")

            page += 1
            time.sleep(0.1)  # Rate limit

        except Exception as e:
            print(f"[Page {page}] Error: {e}")
            break

    print(f"\n총 수집: {len(bills_by_no)}건")
    return bills_by_no


def match_and_update_bills(target_bills: list, all_bills: dict) -> list:
    """
    타겟 법안들을 전체 목록과 매칭하여 summary 추가
    """
    updated = []
    matched = 0

    for bill in target_bills:
        bill_no = bill.get("bill_no", "")

        if bill_no and bill_no in all_bills:
            bill["summary"] = all_bills[bill_no]["summary"]
            matched += 1
        else:
            bill["summary"] = ""

        updated.append(bill)

    print(f"매칭 완료: {matched}/{len(target_bills)}건")
    return updated


def main():
    """메인 실행"""
    # 1. 전체 법안 목록 수집 (최대 20페이지 = 2000건 테스트)
    all_bills = fetch_all_bills_with_summary(max_pages=20)

    # 캐시 저장
    cache_path = DATA_DIR / "bill_summary_cache.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_bills, f, ensure_ascii=False, indent=2)
    print(f"캐시 저장: {cache_path}")

    # 2. 테스트 법안 로드
    test_bills = json.load(open(DATA_DIR / "test_bills.json", encoding="utf-8"))
    golden_set = json.load(open(DATA_DIR / "golden_set.json", encoding="utf-8"))

    # 병합
    all_target_bills = test_bills["bills"] + golden_set["bills"]

    # 중복 제거
    seen_ids = set()
    unique_bills = []
    for b in all_target_bills:
        if b["bill_id"] not in seen_ids:
            seen_ids.add(b["bill_id"])
            unique_bills.append(b)

    print(f"\n타겟 법안: {len(unique_bills)}건")

    # 3. 매칭
    updated_bills = match_and_update_bills(unique_bills, all_bills)

    # 4. 결과 저장
    result = {
        "description": "법안 + 제안이유/주요내용",
        "total_count": len(updated_bills),
        "with_summary": len([b for b in updated_bills if b.get("summary")]),
        "bills": updated_bills,
    }

    output_path = DATA_DIR / "test_bills_with_content.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")
    print(f"summary 포함: {result['with_summary']}/{result['total_count']}건")


if __name__ == "__main__":
    main()
