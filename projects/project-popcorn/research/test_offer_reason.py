"""
BillInfoService2 제안이유 API 테스트

발견된 오퍼레이션:
- getOfferReasonList: 제안이유/주요내용 목록 정보조회
- getBillReceiptInfo: summaryLink 필드 포함
"""
import os
import requests
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

API_KEY = unquote(os.getenv("DATA_GO_KR_API_KEY", ""))
BASE_URL = "http://apis.data.go.kr/9710000/BillInfoService2"


def test_get_offer_reason_list():
    """getOfferReasonList 오퍼레이션 테스트"""
    print("=" * 60)
    print("[1] getOfferReasonList 테스트 (제안이유/주요내용)")
    print("=" * 60)

    endpoint = f"{BASE_URL}/getOfferReasonList"
    params = {
        "ServiceKey": API_KEY,
        "numOfRows": 5,
        "pageNo": 1,
    }

    try:
        r = requests.get(endpoint, params=params, timeout=30)
        print(f"Status: {r.status_code}")
        print(f"URL: {endpoint}")

        if r.status_code == 200:
            # XML 파싱
            root = ET.fromstring(r.text)

            result_code = root.find(".//resultCode")
            result_msg = root.find(".//resultMsg")
            if result_code is not None:
                print(f"Result: {result_code.text} - {result_msg.text if result_msg is not None else ''}")

            total = root.find(".//totalCount")
            if total is not None:
                print(f"Total Count: {total.text}")

            items = root.findall(".//item")
            print(f"Items: {len(items)}")

            if items:
                print("\n[첫 번째 item 전체 필드]")
                for child in items[0]:
                    value = child.text or "(empty)"
                    if len(value) > 150:
                        value = value[:150] + "..."
                    print(f"  {child.tag}: {value}")
        else:
            print(f"Response: {r.text[:500]}")

    except Exception as e:
        print(f"Error: {e}")


def test_get_bill_receipt_info():
    """getBillReceiptInfo 테스트 (summaryLink 필드 확인)"""
    print("\n" + "=" * 60)
    print("[2] getBillReceiptInfo 테스트 (summaryLink)")
    print("=" * 60)

    # 먼저 법안 ID를 가져옴
    endpoint = f"{BASE_URL}/getBillInfoList"
    params = {
        "ServiceKey": API_KEY,
        "numOfRows": 1,
        "pageNo": 1,
        "start_ord": 22,  # 22대 국회
    }

    try:
        r = requests.get(endpoint, params=params, timeout=30)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            item = root.find(".//item")
            if item is not None:
                bill_id = item.findtext("billId", "")
                bill_name = item.findtext("billName", "")
                print(f"테스트 법안: {bill_name}")
                print(f"Bill ID: {bill_id}")

                # getBillReceiptInfo 호출
                endpoint2 = f"{BASE_URL}/getBillReceiptInfo"
                params2 = {
                    "ServiceKey": API_KEY,
                    "bill_id": bill_id,
                }

                r2 = requests.get(endpoint2, params=params2, timeout=30)
                print(f"\nStatus: {r2.status_code}")

                if r2.status_code == 200:
                    root2 = ET.fromstring(r2.text)

                    result_code = root2.find(".//resultCode")
                    if result_code is not None:
                        print(f"Result Code: {result_code.text}")

                    items = root2.findall(".//item")
                    if items:
                        print("\n[응답 필드]")
                        for child in items[0]:
                            value = child.text or "(empty)"
                            if len(value) > 200:
                                value = value[:200] + "..."
                            print(f"  {child.tag}: {value}")

                        # summaryLink 확인
                        summary_link = items[0].findtext("summaryLink", "")
                        summary = items[0].findtext("summary", "")

                        if summary_link:
                            print(f"\n[summaryLink 발견!]")
                            print(f"  {summary_link}")
                        if summary:
                            print(f"\n[summary 발견!]")
                            print(f"  {summary[:300]}...")

    except Exception as e:
        print(f"Error: {e}")


def test_get_bill_info_with_params():
    """getBillInfoList에 특정 파라미터로 summary 필드 조회"""
    print("\n" + "=" * 60)
    print("[3] getBillInfoList 상세 파라미터 테스트")
    print("=" * 60)

    endpoint = f"{BASE_URL}/getBillInfoList"

    # 문서에서 본 예시 파라미터 적용
    params = {
        "ServiceKey": API_KEY,
        "numOfRows": 1,
        "pageNo": 1,
        "gbn": "dae_num_name",
        "start_ord": 22,
        "end_ord": 22,
        "bill_kind_cd": "B04",  # 법률안
    }

    try:
        r = requests.get(endpoint, params=params, timeout=30)
        print(f"Status: {r.status_code}")

        if r.status_code == 200:
            root = ET.fromstring(r.text)

            items = root.findall(".//item")
            if items:
                print(f"\n[응답 필드 목록]")
                for child in items[0]:
                    value = child.text or "(empty)"
                    if len(value) > 100:
                        value = value[:100] + "..."
                    print(f"  {child.tag}: {value}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_get_offer_reason_list()
    test_get_bill_receipt_info()
    test_get_bill_info_with_params()
