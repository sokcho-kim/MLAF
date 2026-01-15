"""
BillInfoService2 API summary 필드 테스트

API 문서에 따르면 summary 필드에 "제안이유 및 주요내용"이 포함됨
실제로 이 필드가 반환되는지 확인
"""
import os
import requests
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

API_KEY = unquote(os.getenv("DATA_GO_KR_API_KEY", ""))
BASE_URL = "http://apis.data.go.kr/9710000/BillInfoService2"


def test_get_bill_info_list():
    """getBillInfoList 오퍼레이션 테스트"""
    print("=" * 60)
    print("[1] getBillInfoList 테스트")
    print("=" * 60)

    endpoint = f"{BASE_URL}/getBillInfoList"
    params = {
        "ServiceKey": API_KEY,
        "numOfRows": 3,
        "pageNo": 1,
        "ord": "A01",  # 제안일 기준 정렬
    }

    try:
        r = requests.get(endpoint, params=params, timeout=30)
        print(f"Status: {r.status_code}")

        if r.status_code == 200:
            root = ET.fromstring(r.text)

            # 에러 체크
            result_code = root.find(".//resultCode")
            if result_code is not None:
                print(f"Result Code: {result_code.text}")

            # 모든 item 출력
            items = root.findall(".//item")
            print(f"총 {len(items)}건 조회")

            if items:
                item = items[0]
                print("\n[첫 번째 item의 모든 필드]")
                for child in item:
                    value = child.text or "(empty)"
                    if len(value) > 100:
                        value = value[:100] + "..."
                    print(f"  {child.tag}: {value}")

                # summary 필드 확인
                summary = item.find("summary")
                if summary is not None and summary.text:
                    print(f"\n[summary 필드 발견!]")
                    print(f"  길이: {len(summary.text)}자")
                    print(f"  내용 미리보기: {summary.text[:200]}...")
                else:
                    print("\n[summary 필드 없음]")

    except Exception as e:
        print(f"Error: {e}")


def test_other_operations():
    """다른 오퍼레이션 테스트"""
    operations = [
        "getBillSummaryList",
        "getRecentBillList",
        "getBillProcResultList",
    ]

    for op in operations:
        print(f"\n{'=' * 60}")
        print(f"[{op}] 테스트")
        print("=" * 60)

        endpoint = f"{BASE_URL}/{op}"
        params = {
            "ServiceKey": API_KEY,
            "numOfRows": 1,
            "pageNo": 1,
        }

        try:
            r = requests.get(endpoint, params=params, timeout=30)
            print(f"Status: {r.status_code}")

            if r.status_code == 200 and r.text.strip():
                # XML인지 확인
                if r.text.startswith("<?xml"):
                    root = ET.fromstring(r.text)
                    result_code = root.find(".//resultCode")
                    result_msg = root.find(".//resultMsg")
                    if result_code is not None:
                        print(f"Result: {result_code.text} - {result_msg.text if result_msg is not None else ''}")

                    items = root.findall(".//item")
                    if items:
                        print(f"item 수: {len(items)}")
                        print("필드 목록:", [child.tag for child in items[0]])
                else:
                    print(f"Response: {r.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")


def test_open_assembly_api():
    """열린국회정보 API에서 제안이유 필드 찾기"""
    print(f"\n{'=' * 60}")
    print("[열린국회정보 API 테스트]")
    print("=" * 60)

    open_key = os.getenv("OPEN_ASSEMBLY_API_KEY", "")

    # 알려진 API들 테스트
    apis = [
        ("nzmimeepazxkubdpn", "국회의원발의법률안"),
        ("nwbpacrgavhjryiph", "의안상세정보"),
    ]

    for api_id, name in apis:
        print(f"\n[{name}] ({api_id})")

        url = f"https://open.assembly.go.kr/portal/openapi/{api_id}"
        params = {
            "Key": open_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 1,
            "AGE": 22,
        }

        try:
            r = requests.get(url, params=params, timeout=10)
            print(f"Status: {r.status_code}")

            if r.status_code == 200:
                data = r.json()
                api_data = data.get(api_id, [{}])

                if len(api_data) > 1 and api_data[1].get("row"):
                    row = api_data[1]["row"][0]
                    fields = list(row.keys())
                    print(f"필드 수: {len(fields)}")

                    # 제안이유 관련 필드 찾기
                    summary_fields = [f for f in fields if any(k in f.upper() for k in
                                     ["SUMMARY", "REASON", "CONTENT", "DETAIL", "PROPOSE"])]
                    print(f"Summary 관련 필드: {summary_fields}")

                    # 모든 필드 출력
                    print("모든 필드:")
                    for k, v in row.items():
                        v_str = str(v)[:80] if v else "(empty)"
                        print(f"  {k}: {v_str}")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    test_get_bill_info_list()
    test_other_operations()
    test_open_assembly_api()
