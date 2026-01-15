"""
법안 제안이유/주요내용 수집

공공데이터포털 BillInfoService2 API 사용
"""
import os
import json
import requests
from pathlib import Path
from urllib.parse import unquote
from dotenv import load_dotenv
import time

load_dotenv()

# API 설정
API_KEY = unquote(os.getenv("DATA_GO_KR_API_KEY", ""))
BASE_URL = "http://apis.data.go.kr/9710000/BillInfoService2"

DATA_DIR = Path(__file__).parent.parent / "data"


def get_bill_content(bill_id: str) -> dict | None:
    """
    법안 제안이유/주요내용 조회

    Args:
        bill_id: 의안ID (예: PRC_K2J5I0P8O0N7M1G0F5E6N0W4V9S5I9)

    Returns:
        법안 상세 정보 dict

    Note:
        bill_kind_cd=B04 (법률안) 파라미터 필수 - summary 필드 반환 조건
    """
    endpoint = f"{BASE_URL}/getBillInfoList"

    params = {
        "ServiceKey": API_KEY,
        "bill_id": bill_id,
        "bill_kind_cd": "B04",  # 법률안 - summary 필드 반환 필수 조건
        "numOfRows": 1,
        "pageNo": 1,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()

        # XML 파싱
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.text)

        # 에러 체크
        result_code = root.find(".//resultCode")
        if result_code is not None and result_code.text != "00":
            result_msg = root.find(".//resultMsg")
            print(f"    [ERROR] API error: {result_msg.text if result_msg is not None else 'Unknown'}")
            return None

        # 데이터 추출
        item = root.find(".//item")
        if item is None:
            return None

        return {
            "bill_id": bill_id,
            "bill_name": item.findtext("billName", ""),
            "proposer": item.findtext("proposer", ""),
            "summary": item.findtext("summary", ""),  # 제안이유 및 주요내용
            "proc_result": item.findtext("procResult", ""),
        }

    except Exception as e:
        print(f"    [ERROR] {bill_id}: {e}")
        return None


def fetch_bill_contents():
    """테스트 법안 + Golden Set 법안의 제안이유 수집"""
    print("=" * 60)
    print("법안 제안이유/주요내용 수집")
    print("=" * 60)

    # 테스트 법안 로드
    test_bills = json.load(open(DATA_DIR / "test_bills.json", encoding="utf-8"))
    bills = test_bills["bills"]

    # Golden Set 로드
    golden_data = json.load(open(DATA_DIR / "golden_set.json", encoding="utf-8"))
    golden_bills = golden_data["bills"]

    # Golden Set 법안 추가 (중복 제거)
    bill_ids = {b["bill_id"] for b in bills}
    for g in golden_bills:
        if g["bill_id"] not in bill_ids:
            bills.append({
                "bill_id": g["bill_id"],
                "bill_name": g["bill_name"],
                "committee": g.get("committee", ""),
            })

    print(f"총 {len(bills)}건 수집 시작...")
    print()

    results = []
    success_count = 0

    for i, bill in enumerate(bills):
        bill_id = bill["bill_id"]
        print(f"[{i+1}/{len(bills)}] {bill['bill_name'][:30]}...")

        content = get_bill_content(bill_id)

        if content and content.get("summary"):
            bill["summary"] = content["summary"]
            success_count += 1
            print(f"    [O] {len(content['summary'])}자")
        else:
            bill["summary"] = ""
            print(f"    [X] 수집 실패")

        results.append(bill)
        time.sleep(0.2)  # Rate limit

    print()
    print("=" * 60)
    print(f"수집 완료: {success_count}/{len(bills)}건 성공")
    print("=" * 60)

    return results


def save_results(bills: list, output_path: str):
    """결과 저장"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "description": "법안 샘플 + 제안이유/주요내용",
        "total_count": len(bills),
        "with_summary": len([b for b in bills if b.get("summary")]),
        "bills": bills,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {output_path}")


if __name__ == "__main__":
    bills = fetch_bill_contents()

    output_path = DATA_DIR / "test_bills_with_content.json"
    save_results(bills, str(output_path))
