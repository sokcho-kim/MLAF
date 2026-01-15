"""
getBillInfoList summary 필드 반환 조건 테스트
"""
import os
import requests
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

API_KEY = unquote(os.getenv("DATA_GO_KR_API_KEY", ""))
BASE_URL = "http://apis.data.go.kr/9710000/BillInfoService2"


def test_params(test_name, extra_params):
    """파라미터 조합 테스트"""
    endpoint = f"{BASE_URL}/getBillInfoList"

    params = {
        "ServiceKey": API_KEY,
        "numOfRows": 1,
        "pageNo": 1,
    }
    params.update(extra_params)

    try:
        r = requests.get(endpoint, params=params, timeout=30)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall(".//item")

            if items:
                summary = items[0].findtext("summary", "")
                bill_name = items[0].findtext("billName", "")

                has_summary = "O" if summary else "X"
                summary_preview = summary[:50] + "..." if summary else "(없음)"

                print(f"[{test_name}] summary: {has_summary}")
                if summary:
                    print(f"    내용: {summary_preview}")
                return bool(summary)
            else:
                print(f"[{test_name}] 결과 없음")
        else:
            print(f"[{test_name}] HTTP {r.status_code}")

    except Exception as e:
        print(f"[{test_name}] Error: {e}")

    return False


print("=" * 60)
print("getBillInfoList summary 필드 반환 조건 테스트")
print("=" * 60)

# 테스트 케이스
tests = [
    ("기본 (파라미터 없음)", {}),
    ("ord=A01", {"ord": "A01"}),
    ("gbn=dae_num_name", {"gbn": "dae_num_name"}),
    ("start_ord=22", {"start_ord": 22}),
    ("bill_kind_cd=B04", {"bill_kind_cd": "B04"}),
    ("gbn + start_ord", {"gbn": "dae_num_name", "start_ord": 22}),
    ("gbn + bill_kind_cd", {"gbn": "dae_num_name", "bill_kind_cd": "B04"}),
    ("start_ord + bill_kind_cd", {"start_ord": 22, "bill_kind_cd": "B04"}),
    ("gbn + start_ord + bill_kind_cd", {"gbn": "dae_num_name", "start_ord": 22, "bill_kind_cd": "B04"}),
    ("proposer_kind_cd=F01", {"proposer_kind_cd": "F01"}),  # 의원 발의
]

print()
results = []
for name, params in tests:
    has_summary = test_params(name, params)
    results.append((name, has_summary))

print("\n" + "=" * 60)
print("결과 요약")
print("=" * 60)
for name, has_summary in results:
    status = "O (summary 포함)" if has_summary else "X"
    print(f"  {name}: {status}")
