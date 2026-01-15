"""
의안상세정보 API 수집기

열린국회정보 의안상세정보(nwbpacrgavhjryiph) API에서
22대 국회 법률안 전체를 수집합니다.

수집 필드:
- bill_no, bill_id, bill_name
- committee (소관위) - 99%
- proc_result (처리결과) - 100%
- vote_info (투표정보) - 92%
- propose_dt, proposer
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv()

API_KEY = os.getenv("OPEN_ASSEMBLY_API_KEY", "")
BASE_URL = "https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph"
DATA_DIR = Path(__file__).parent.parent / "data"


def fetch_assembly_bills(age: int = 22, page_size: int = 1000) -> list:
    """
    의안상세정보 API에서 법률안 수집

    Args:
        age: 국회 대수 (22 = 22대)
        page_size: 페이지당 건수

    Returns:
        법률안 목록
    """
    print("=" * 60)
    print(f"의안상세정보 수집 ({age}대 국회)")
    print("=" * 60)

    all_bills = []
    page = 1

    while True:
        params = {
            "Key": API_KEY,
            "Type": "json",
            "pIndex": page,
            "pSize": page_size,
            "AGE": age,
        }

        try:
            r = requests.get(BASE_URL, params=params, timeout=30)
            data = r.json()

            if "nwbpacrgavhjryiph" not in data:
                print(f"[Page {page}] API 응답 오류: {data}")
                break

            # 총 건수 확인 (첫 페이지에서만)
            if page == 1:
                head = data["nwbpacrgavhjryiph"][0].get("head", [{}])
                if head:
                    total_count = head[0].get("list_total_count", 0)
                    print(f"총 건수: {total_count}")

            rows = data["nwbpacrgavhjryiph"][1].get("row", [])

            if not rows:
                print(f"[Page {page}] 더 이상 데이터 없음")
                break

            # 데이터 정규화
            for row in rows:
                bill = {
                    "bill_no": row.get("BILL_NO", ""),
                    "bill_id": row.get("BILL_ID", ""),
                    "bill_name": row.get("BILL_NM", ""),
                    "committee": row.get("COMMITTEE_NM", ""),
                    "proc_result": row.get("PROC_RESULT_CD", ""),
                    "vote_info": {
                        "total": _safe_int(row.get("VOTE_TCNT")),
                        "yes": _safe_int(row.get("YES_TCNT")),
                        "no": _safe_int(row.get("NO_TCNT")),
                        "blank": _safe_int(row.get("BLANK_TCNT")),
                    },
                    "propose_dt": row.get("PROPOSE_DT", ""),
                    "proposer": row.get("PROPOSER", ""),
                    "bill_kind": row.get("BILL_KIND", ""),
                    "link_url": row.get("LINK_URL", ""),
                }
                all_bills.append(bill)

            print(f"[Page {page}] {len(rows)}건 수집 (누적: {len(all_bills)})")

            page += 1
            time.sleep(0.2)  # Rate limit

        except Exception as e:
            print(f"[Page {page}] Error: {e}")
            break

    return all_bills


def _safe_int(value) -> int:
    """안전한 int 변환"""
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def analyze_quality(bills: list) -> dict:
    """데이터 품질 분석"""
    total = len(bills)
    if total == 0:
        return {}

    stats = {
        "total": total,
        "committee_filled": sum(1 for b in bills if b.get("committee")),
        "proc_result_filled": sum(1 for b in bills if b.get("proc_result")),
        "vote_filled": sum(1 for b in bills if b["vote_info"]["total"] > 0),
    }

    stats["committee_rate"] = f"{stats['committee_filled']/total*100:.1f}%"
    stats["proc_result_rate"] = f"{stats['proc_result_filled']/total*100:.1f}%"
    stats["vote_rate"] = f"{stats['vote_filled']/total*100:.1f}%"

    return stats


def main():
    """메인 실행"""
    # 데이터 수집
    bills = fetch_assembly_bills(age=22)

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

    # 처리결과 분포
    proc_results = {}
    for b in bills:
        pr = b.get("proc_result") or "(미처리)"
        proc_results[pr] = proc_results.get(pr, 0) + 1

    print("\n처리결과 분포:")
    for pr, count in sorted(proc_results.items(), key=lambda x: -x[1]):
        print(f"  {pr}: {count}건")

    # 소관위 분포
    committees = {}
    for b in bills:
        cm = b.get("committee") or "(없음)"
        committees[cm] = committees.get(cm, 0) + 1

    print("\n소관위 분포 (상위 10개):")
    for cm, count in sorted(committees.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cm}: {count}건")

    # 저장
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "bills_raw_assembly.json"

    result = {
        "description": "의안상세정보 API 수집 결과",
        "source": "열린국회정보 nwbpacrgavhjryiph",
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "age": 22,
        "stats": stats,
        "bills": bills,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")
    print(f"총 {len(bills)}건")


if __name__ == "__main__":
    main()
