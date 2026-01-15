"""
의안 API 분석 리포트 생성

1. 열린국회정보 API 전체 스캔
2. 공공데이터포털 의안 API 분석
3. 제안이유/주요내용 필드 포함 API 식별
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPEN_ASSEMBLY_KEY = os.getenv("OPEN_ASSEMBLY_API_KEY", "")
DATA_GO_KR_KEY = os.getenv("DATA_GO_KR_API_KEY", "")

OUTPUT_DIR = Path(__file__).parent / "results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def analyze_open_assembly_apis():
    """열린국회정보 API 전체 분석"""
    print("=" * 60)
    print("[1] 열린국회정보 API 분석")
    print("=" * 60)

    # API 목록 조회
    url = "https://open.assembly.go.kr/portal/openapi/OPENSRVAPI"
    params = {"Key": OPEN_ASSEMBLY_KEY, "Type": "json", "pIndex": 1, "pSize": 500}

    r = requests.get(url, params=params, timeout=30)
    data = r.json()

    apis = data.get("OPENSRVAPI", [{}])
    if len(apis) < 2:
        print("API 목록 조회 실패")
        return []

    total = apis[0].get("head", [{}])[0].get("list_total_count", 0)
    rows = apis[1].get("row", [])
    print(f"총 API 수: {total}")
    print(f"조회된 API: {len(rows)}")

    # 의안 관련 API 필터링
    bill_apis = []
    keywords = ["의안", "법률", "제안", "발의", "심사", "처리", "BILL"]

    for item in rows:
        nm = item.get("INF_NM", "")
        exp = item.get("INF_EXP", "")
        inf_id = item.get("INF_ID", "")

        if any(k in nm + exp for k in keywords):
            bill_apis.append({
                "inf_id": inf_id,
                "name": nm,
                "description": exp,
            })

    print(f"의안 관련 API: {len(bill_apis)}개")
    return bill_apis


def test_api_fields(api_id: str, api_name: str):
    """특정 API의 필드 구조 분석"""
    # API ID가 영문 소문자로 된 경우만 실제 API
    if not api_id.islower():
        return None

    url = f"https://open.assembly.go.kr/portal/openapi/{api_id}"
    params = {"Key": OPEN_ASSEMBLY_KEY, "Type": "json", "pIndex": 1, "pSize": 1, "AGE": 22}

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        api_data = data.get(api_id, [{}])
        if len(api_data) > 1 and api_data[1].get("row"):
            row = api_data[1]["row"][0]
            fields = list(row.keys())

            # 제안이유/주요내용 관련 필드 확인
            summary_fields = [f for f in fields if any(k in f.upper() for k in ["SUMMARY", "REASON", "CONTENT", "DETAIL"])]

            return {
                "api_id": api_id,
                "name": api_name,
                "total_fields": len(fields),
                "fields": fields,
                "summary_fields": summary_fields,
                "sample": {k: str(v)[:100] for k, v in list(row.items())[:5]}
            }
    except Exception as e:
        pass

    return None


def find_summary_api():
    """제안이유/주요내용 포함 API 찾기"""
    print("\n" + "=" * 60)
    print("[2] 제안이유/주요내용 API 탐색")
    print("=" * 60)

    # 알려진 의안 관련 API 엔드포인트
    known_apis = [
        ("TVBPMBILL11", "의안검색"),
        ("nzmimeepazxkubdpn", "국회의원발의법률안"),
        ("nwbpacrgavhjryiph", "의안상세정보"),
        ("ALLBILL", "의안정보통합"),
        ("nvobjaqtvdfluqyg", "법률안제안이유및주요내용"),  # 추정
    ]

    results = []
    for api_id, name in known_apis:
        print(f"\n[{api_id}] {name}")
        result = test_api_fields(api_id, name)
        if result:
            print(f"  필드 수: {result['total_fields']}")
            print(f"  Summary 관련: {result['summary_fields']}")
            results.append(result)
        else:
            print(f"  조회 실패")

    return results


def scan_all_apis_for_summary():
    """모든 API에서 SUMMARY 필드 포함 여부 스캔"""
    print("\n" + "=" * 60)
    print("[3] 전체 API SUMMARY 필드 스캔")
    print("=" * 60)

    # 가능한 API 엔드포인트 패턴 테스트
    # 열린국회정보 API는 소문자 영문으로 된 ID를 사용

    url = "https://open.assembly.go.kr/portal/openapi/OPENSRVAPI"
    params = {"Key": OPEN_ASSEMBLY_KEY, "Type": "json", "pIndex": 1, "pSize": 500}

    r = requests.get(url, params=params, timeout=30)
    data = r.json()

    apis = data.get("OPENSRVAPI", [{}])
    if len(apis) < 2:
        return []

    rows = apis[1].get("row", [])

    # DDC_URL에서 실제 API 엔드포인트 추출
    summary_apis = []

    for item in rows:
        inf_id = item.get("INF_ID", "")
        nm = item.get("INF_NM", "")
        exp = item.get("INF_EXP", "")
        ddc_url = item.get("DDC_URL", "")

        # 제안이유, 주요내용 키워드 포함
        if "제안이유" in nm + exp or "주요내용" in nm + exp:
            summary_apis.append({
                "inf_id": inf_id,
                "name": nm,
                "description": exp,
                "ddc_url": ddc_url,
            })
            print(f"[FOUND] {inf_id}: {nm}")

    return summary_apis


def main():
    """메인 분석 실행"""
    report = {
        "open_assembly": {},
        "summary_apis": [],
    }

    # 1. 열린국회정보 API 분석
    bill_apis = analyze_open_assembly_apis()
    report["open_assembly"]["bill_apis_count"] = len(bill_apis)
    report["open_assembly"]["bill_apis"] = bill_apis[:20]  # 상위 20개

    # 2. 제안이유 API 찾기
    summary_apis = scan_all_apis_for_summary()
    report["summary_apis"] = summary_apis

    # 3. 알려진 API 필드 분석
    known_results = find_summary_api()
    report["known_api_fields"] = known_results

    # 결과 저장
    output_path = OUTPUT_DIR / "api_analysis_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"분석 완료: {output_path}")
    print("=" * 60)

    # 요약 출력
    print("\n[요약]")
    print(f"- 의안 관련 API: {len(bill_apis)}개")
    print(f"- 제안이유/주요내용 API 후보: {len(summary_apis)}개")

    if summary_apis:
        print("\n[제안이유 API 후보]")
        for api in summary_apis:
            print(f"  - {api['inf_id']}: {api['name']}")


if __name__ == "__main__":
    main()
