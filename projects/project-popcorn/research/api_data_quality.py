"""
API 데이터 품질 분석

각 API별 필드 제공 현황 및 null 비율 확인
"""
import os
import json
import requests
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

# API Keys
DATA_GO_KR_KEY = unquote(os.getenv("DATA_GO_KR_API_KEY", ""))
OPEN_ASSEMBLY_KEY = os.getenv("OPEN_ASSEMBLY_API_KEY", "")


def analyze_open_assembly_bills():
    """열린국회정보 - 국회의원발의법률안 (nzmimeepazxkubdpn)"""
    print("=" * 60)
    print("[1] 열린국회정보 - 국회의원발의법률안")
    print("=" * 60)

    url = "https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn"
    params = {
        "Key": OPEN_ASSEMBLY_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "AGE": 22,  # 22대 국회
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()

        if "nzmimeepazxkubdpn" not in data:
            print(f"Error: {data}")
            return None

        rows = data["nzmimeepazxkubdpn"][1].get("row", [])
        print(f"샘플 건수: {len(rows)}")

        if not rows:
            return None

        # 필드별 null 비율 계산
        fields = list(rows[0].keys())
        print(f"총 필드 수: {len(fields)}")
        print(f"필드 목록: {fields}")

        field_stats = {}
        for field in fields:
            non_null = sum(1 for r in rows if r.get(field) and r.get(field) != "None")
            field_stats[field] = {
                "total": len(rows),
                "non_null": non_null,
                "rate": f"{non_null/len(rows)*100:.1f}%"
            }

        # 주요 필드 출력
        key_fields = ["BILL_ID", "BILL_NO", "BILL_NAME", "COMMITTEE", "PROC_RESULT", "PROPOSE_DT"]
        print("\n주요 필드 현황:")
        for f in key_fields:
            if f in field_stats:
                stats = field_stats[f]
                print(f"  {f}: {stats['non_null']}/{stats['total']} ({stats['rate']})")

        # COMMITTEE 값 샘플
        committees = [r.get("COMMITTEE", "") for r in rows[:10]]
        print(f"\nCOMMITTEE 샘플: {committees[:5]}")

        # PROC_RESULT 값 샘플
        proc_results = [r.get("PROC_RESULT", "") for r in rows[:10]]
        print(f"PROC_RESULT 샘플: {proc_results[:5]}")

        return {"name": "국회의원발의법률안", "fields": fields, "stats": field_stats, "sample_count": len(rows)}

    except Exception as e:
        print(f"Error: {e}")
        return None


def analyze_open_assembly_detail():
    """열린국회정보 - 의안상세정보 (nwbpacrgavhjryiph)"""
    print("\n" + "=" * 60)
    print("[2] 열린국회정보 - 의안상세정보")
    print("=" * 60)

    url = "https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph"
    params = {
        "Key": OPEN_ASSEMBLY_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "AGE": 22,
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()

        if "nwbpacrgavhjryiph" not in data:
            print(f"Error: {data}")
            return None

        rows = data["nwbpacrgavhjryiph"][1].get("row", [])
        print(f"샘플 건수: {len(rows)}")

        if not rows:
            return None

        fields = list(rows[0].keys())
        print(f"총 필드 수: {len(fields)}")
        print(f"필드 목록: {fields}")

        field_stats = {}
        for field in fields:
            non_null = sum(1 for r in rows if r.get(field) and r.get(field) != "None")
            field_stats[field] = {
                "total": len(rows),
                "non_null": non_null,
                "rate": f"{non_null/len(rows)*100:.1f}%"
            }

        # 주요 필드 출력
        key_fields = ["BILL_NO", "BILL_NM", "COMMITTEE_NM", "PROC_RESULT_CD", "VOTE_TCNT"]
        print("\n주요 필드 현황:")
        for f in key_fields:
            if f in field_stats:
                stats = field_stats[f]
                print(f"  {f}: {stats['non_null']}/{stats['total']} ({stats['rate']})")

        # 처리완료 법안 확인
        proc_results = [r.get("PROC_RESULT_CD", "") for r in rows]
        unique_results = set(proc_results)
        print(f"\nPROC_RESULT_CD 값들: {unique_results}")

        # 투표 정보 있는 법안
        with_votes = sum(1 for r in rows if r.get("VOTE_TCNT") and int(r.get("VOTE_TCNT", 0) or 0) > 0)
        print(f"투표 정보 있는 법안: {with_votes}/{len(rows)}")

        return {"name": "의안상세정보", "fields": fields, "stats": field_stats, "sample_count": len(rows)}

    except Exception as e:
        print(f"Error: {e}")
        return None


def analyze_data_go_kr():
    """공공데이터포털 - BillInfoService2"""
    print("\n" + "=" * 60)
    print("[3] 공공데이터포털 - BillInfoService2")
    print("=" * 60)

    endpoint = "http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList"
    params = {
        "ServiceKey": DATA_GO_KR_KEY,
        "bill_kind_cd": "B04",  # 법률안 - summary 반환 필수
        "end_ord": 22,
        "ord": "D01",
        "numOfRows": 100,
        "pageNo": 1,
    }

    try:
        r = requests.get(endpoint, params=params, timeout=30)
        root = ET.fromstring(r.text)

        items = root.findall(".//item")
        print(f"샘플 건수: {len(items)}")

        if not items:
            return None

        # 첫 번째 item에서 필드 목록 추출
        fields = [child.tag for child in items[0]]
        print(f"총 필드 수: {len(fields)}")
        print(f"필드 목록: {fields}")

        # 필드별 통계
        field_stats = {}
        for field in fields:
            non_null = sum(1 for item in items if item.findtext(field, ""))
            field_stats[field] = {
                "total": len(items),
                "non_null": non_null,
                "rate": f"{non_null/len(items)*100:.1f}%"
            }

        # 주요 필드 출력
        key_fields = ["billId", "billNo", "billName", "summary", "proposer", "committee"]
        print("\n주요 필드 현황:")
        for f in key_fields:
            if f in field_stats:
                stats = field_stats[f]
                print(f"  {f}: {stats['non_null']}/{stats['total']} ({stats['rate']})")
            else:
                print(f"  {f}: (필드 없음)")

        # summary 길이 샘플
        summaries = [item.findtext("summary", "") for item in items[:5]]
        print(f"\nsummary 길이 샘플: {[len(s) for s in summaries]}")

        return {"name": "BillInfoService2", "fields": fields, "stats": field_stats, "sample_count": len(items)}

    except Exception as e:
        print(f"Error: {e}")
        return None


def analyze_local_data():
    """로컬 수집 데이터 분석"""
    print("\n" + "=" * 60)
    print("[4] 로컬 수집 데이터 현황")
    print("=" * 60)

    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    files_to_check = [
        ("test_bills.json", ["bill_id", "bill_name", "committee", "proc_result"]),
        ("test_bills_with_content.json", ["bill_id", "bill_name", "committee", "proc_result", "summary"]),
        ("golden_set.json", ["bill_id", "bill_name", "committee", "expected_depts"]),
        ("bill_summary_cache.json", None),  # dict 형태
    ]

    results = {}
    for filename, key_fields in files_to_check:
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            print(f"\n{filename}: 파일 없음")
            continue

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        print(f"\n{filename}:")

        if isinstance(data, dict) and "bills" in data:
            bills = data["bills"]
            print(f"  총 건수: {len(bills)}")

            if key_fields and bills:
                for field in key_fields:
                    non_null = sum(1 for b in bills if b.get(field))
                    print(f"  {field}: {non_null}/{len(bills)} ({non_null/len(bills)*100:.1f}%)")

            results[filename] = {"count": len(bills), "type": "bills_array"}

        elif isinstance(data, dict) and "bills" not in data:
            # bill_summary_cache.json 형태
            print(f"  총 건수: {len(data)}")
            if data:
                sample_key = list(data.keys())[0]
                sample = data[sample_key]
                print(f"  필드: {list(sample.keys())}")

                # summary 채워진 비율
                with_summary = sum(1 for v in data.values() if v.get("summary"))
                print(f"  summary 있음: {with_summary}/{len(data)} ({with_summary/len(data)*100:.1f}%)")

            results[filename] = {"count": len(data), "type": "dict"}

    return results


if __name__ == "__main__":
    print("API 데이터 품질 분석")
    print("=" * 60)
    print()

    results = {}

    # 1. 열린국회정보 - 국회의원발의법률안
    results["open_assembly_bills"] = analyze_open_assembly_bills()

    # 2. 열린국회정보 - 의안상세정보
    results["open_assembly_detail"] = analyze_open_assembly_detail()

    # 3. 공공데이터포털
    results["data_go_kr"] = analyze_data_go_kr()

    # 4. 로컬 데이터
    results["local"] = analyze_local_data()

    print("\n" + "=" * 60)
    print("분석 완료")
    print("=" * 60)
