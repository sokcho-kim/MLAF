"""
열린국회정보 전체 API에서 제안이유/주요내용 제공 API 찾기
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPEN_KEY = os.getenv("OPEN_ASSEMBLY_API_KEY", "")


def scan_all_apis():
    """전체 API 스캔하여 제안이유 관련 API 찾기"""
    print("=" * 70)
    print("열린국회정보 전체 API 스캔")
    print("=" * 70)

    url = "https://open.assembly.go.kr/portal/openapi/OPENSRVAPI"
    params = {"Key": OPEN_KEY, "Type": "json", "pIndex": 1, "pSize": 1000}

    r = requests.get(url, params=params, timeout=30)
    data = r.json()

    apis = data.get("OPENSRVAPI", [{}])
    if len(apis) < 2:
        print("API 목록 조회 실패")
        return

    total = apis[0].get("head", [{}])[0].get("list_total_count", 0)
    rows = apis[1].get("row", [])
    print(f"총 API 수: {total}")
    print(f"조회된 API: {len(rows)}")

    # 제안이유, 주요내용 키워드 검색
    keywords = ["제안이유", "주요내용", "summary", "요약", "제안사유"]
    found_apis = []

    for item in rows:
        nm = item.get("INF_NM", "")
        exp = item.get("INF_EXP", "")
        inf_id = item.get("INF_ID", "")
        url_path = item.get("URL_PATH", "")
        ddc_url = item.get("DDC_URL", "")

        if any(k in (nm + exp).lower() for k in keywords):
            found_apis.append({
                "inf_id": inf_id,
                "name": nm,
                "description": exp,
                "url_path": url_path,
                "ddc_url": ddc_url,
            })

    print(f"\n[제안이유/주요내용 관련 API: {len(found_apis)}개]")
    for api in found_apis:
        print(f"\n  ID: {api['inf_id']}")
        print(f"  이름: {api['name']}")
        print(f"  설명: {api['description']}")
        print(f"  URL: {api['url_path']}")
        print(f"  DDC: {api['ddc_url']}")

    return found_apis


def test_api_endpoint(api_id: str):
    """특정 API 엔드포인트 테스트"""
    # 소문자로만 된 ID가 실제 API 엔드포인트
    if not api_id or not api_id.islower():
        return None

    url = f"https://open.assembly.go.kr/portal/openapi/{api_id}"
    params = {
        "Key": OPEN_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 1,
        "AGE": 22,
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            api_data = data.get(api_id, [{}])

            if len(api_data) > 1 and api_data[1].get("row"):
                row = api_data[1]["row"][0]
                return list(row.keys())
    except:
        pass

    return None


def find_api_with_summary_field():
    """모든 의안 관련 API에서 summary 필드를 가진 API 찾기"""
    print("\n" + "=" * 70)
    print("의안 관련 API에서 Summary 필드 검색")
    print("=" * 70)

    url = "https://open.assembly.go.kr/portal/openapi/OPENSRVAPI"
    params = {"Key": OPEN_KEY, "Type": "json", "pIndex": 1, "pSize": 1000}

    r = requests.get(url, params=params, timeout=30)
    data = r.json()

    apis = data.get("OPENSRVAPI", [{}])
    rows = apis[1].get("row", []) if len(apis) > 1 else []

    # 의안 관련 API 필터링
    bill_keywords = ["의안", "법률", "법안", "BILL"]
    bill_apis = []

    for item in rows:
        nm = item.get("INF_NM", "")
        exp = item.get("INF_EXP", "")
        url_path = item.get("URL_PATH", "")

        if any(k in nm + exp for k in bill_keywords):
            # URL에서 API ID 추출
            if url_path and "/" in url_path:
                api_id = url_path.split("/")[-1]
                if api_id.islower():
                    bill_apis.append((api_id, nm))

    print(f"의안 관련 API 후보: {len(bill_apis)}개")

    # 각 API 테스트
    summary_apis = []
    for api_id, name in bill_apis[:30]:  # 상위 30개만 테스트
        fields = test_api_endpoint(api_id)
        if fields:
            # summary 관련 필드 확인
            summary_fields = [f for f in fields if any(k in f.upper() for k in
                            ["SUMMARY", "REASON", "CONTENT", "PROPOSE_REASON", "MAIN_CONTENT"])]
            if summary_fields:
                summary_apis.append({
                    "api_id": api_id,
                    "name": name,
                    "fields": fields,
                    "summary_fields": summary_fields,
                })
                print(f"\n[발견!] {name} ({api_id})")
                print(f"  Summary 필드: {summary_fields}")

    return summary_apis


if __name__ == "__main__":
    # 1. 제안이유/주요내용 키워드로 API 찾기
    found = scan_all_apis()

    # 2. 의안 API들에서 summary 필드 찾기
    summary_apis = find_api_with_summary_field()

    print("\n" + "=" * 70)
    print("최종 결과")
    print("=" * 70)
    if summary_apis:
        print(f"Summary 필드를 가진 API: {len(summary_apis)}개")
        for api in summary_apis:
            print(f"  - {api['name']}: {api['summary_fields']}")
    else:
        print("Summary 필드를 직접 제공하는 API를 찾지 못함")
        print("\n대안:")
        print("  1. DETAIL_LINK로 웹페이지 크롤링")
        print("  2. 공공데이터포털 별도 오퍼레이션 확인")
