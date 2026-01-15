"""
공공데이터포털 summary 수집기

BillInfoService2 API에서 법률안의 summary(제안이유/주요내용)를 수집합니다.

주의:
- bill_kind_cd=B04 파라미터 필수 (summary 반환 조건)
- end_ord=22로 22대 국회 법안 수집
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
BASE_URL = "http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList"
DATA_DIR = Path(__file__).parent.parent / "data"


def fetch_summaries(max_pages: int = 200, age: int = 22) -> dict:
    """
    BillInfoService2에서 summary 수집

    Args:
        max_pages: 최대 페이지 수
        age: 국회 대수

    Returns:
        {bill_no: {"bill_id": ..., "bill_name": ..., "summary": ...}, ...}
    """
    print("=" * 60)
    print(f"BillInfoService2 summary 수집 ({age}대 국회)")
    print("=" * 60)

    bills_by_no = {}
    page = 1
    rows_per_page = 100

    while page <= max_pages:
        params = {
            "ServiceKey": API_KEY,
            "bill_kind_cd": "B04",  # 법률안 - summary 반환 필수!
            "end_ord": age,
            "ord": "D01",  # 최신순
            "numOfRows": rows_per_page,
            "pageNo": page,
        }

        try:
            r = requests.get(BASE_URL, params=params, timeout=30)

            if r.status_code != 200:
                print(f"[Page {page}] HTTP {r.status_code}")
                break

            root = ET.fromstring(r.text)

            # 에러 체크
            result_code = root.find(".//resultCode")
            if result_code is not None and result_code.text != "00":
                result_msg = root.find(".//resultMsg")
                print(f"[Page {page}] API Error: {result_msg.text if result_msg else 'Unknown'}")
                break

            items = root.findall(".//item")

            if not items:
                print(f"[Page {page}] 더 이상 데이터 없음")
                break

            for item in items:
                bill_no = item.findtext("billNo", "")
                if bill_no:
                    bills_by_no[bill_no] = {
                        "bill_id": item.findtext("billId", ""),
                        "bill_name": item.findtext("billName", ""),
                        "summary": item.findtext("summary", ""),
                    }

            if page % 10 == 0:
                with_summary = sum(1 for v in bills_by_no.values() if v.get("summary"))
                print(f"[Page {page}] 누적: {len(bills_by_no)}건 (summary: {with_summary}건)")

            page += 1
            time.sleep(0.1)  # Rate limit

        except Exception as e:
            print(f"[Page {page}] Error: {e}")
            break

    return bills_by_no


def analyze_quality(bills: dict) -> dict:
    """데이터 품질 분석"""
    total = len(bills)
    if total == 0:
        return {}

    with_summary = sum(1 for v in bills.values() if v.get("summary"))
    summary_lengths = [len(v.get("summary", "")) for v in bills.values() if v.get("summary")]

    return {
        "total": total,
        "with_summary": with_summary,
        "summary_rate": f"{with_summary/total*100:.1f}%",
        "avg_summary_length": int(sum(summary_lengths) / len(summary_lengths)) if summary_lengths else 0,
        "min_summary_length": min(summary_lengths) if summary_lengths else 0,
        "max_summary_length": max(summary_lengths) if summary_lengths else 0,
    }


def main():
    """메인 실행"""
    # 데이터 수집 (전체 페이지)
    bills = fetch_summaries(max_pages=200)

    if not bills:
        print("수집된 데이터 없음")
        return

    # 품질 분석
    print("\n" + "=" * 60)
    print("데이터 품질 분석")
    print("=" * 60)
    stats = analyze_quality(bills)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 저장
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "bills_raw_summary.json"

    result = {
        "description": "BillInfoService2 summary 수집 결과",
        "source": "공공데이터포털 BillInfoService2",
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": "bill_kind_cd=B04, end_ord=22",
        "stats": stats,
        "bills": bills,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")
    print(f"총 {len(bills)}건")


if __name__ == "__main__":
    main()
