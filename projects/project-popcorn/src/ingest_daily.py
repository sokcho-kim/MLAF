"""
일일 법안 수집 모듈

매일 실행하여 신규 법안을 수집하고 마스터 데이터에 병합합니다.

기능:
- 어제 이후 제안된 법안 수집
- 마스터 데이터와 병합 (중복 제거)
- 일별 수집 데이터 저장
"""
import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import time

load_dotenv()

API_KEY = os.getenv("OPEN_ASSEMBLY_API_KEY", "")
BASE_URL = "https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph"

# 경로 설정
DATA_DIR = Path(__file__).parent.parent / "data"
DAILY_DIR = DATA_DIR / "daily"
MASTER_FILE = DATA_DIR / "bills_master.json"


def fetch_bills_since(since_date: str, age: int = 22) -> list[dict]:
    """
    특정 날짜 이후 제안된 법안 수집

    Args:
        since_date: 기준 날짜 (YYYY-MM-DD)
        age: 국회 대수

    Returns:
        법안 목록
    """
    print(f"[Ingest] 법안 수집 시작 (since: {since_date})")

    all_bills = []
    page = 1
    page_size = 1000

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
                print(f"[Ingest] API 응답 오류")
                break

            rows = data["nwbpacrgavhjryiph"][1].get("row", [])
            if not rows:
                break

            # 날짜 필터링
            for row in rows:
                propose_dt = row.get("PROPOSE_DT", "")
                if propose_dt >= since_date:
                    bill = _normalize_bill(row)
                    all_bills.append(bill)

            print(f"[Ingest] Page {page}: {len(rows)}건 조회, 필터 후 누적 {len(all_bills)}건")

            # 마지막 페이지의 제안일이 since_date보다 이전이면 종료
            last_dt = rows[-1].get("PROPOSE_DT", "")
            if last_dt < since_date:
                break

            page += 1
            time.sleep(0.2)

        except Exception as e:
            print(f"[Ingest] Error: {e}")
            break

    print(f"[Ingest] 수집 완료: {len(all_bills)}건")
    return all_bills


def _normalize_bill(row: dict) -> dict:
    """API 응답을 정규화"""
    return {
        "bill_no": row.get("BILL_NO", ""),
        "bill_id": row.get("BILL_ID", ""),
        "bill_name": row.get("BILL_NM", ""),
        "committee": row.get("COMMITTEE_NM", ""),
        "proc_result": row.get("PROC_RESULT_CD", ""),
        "propose_dt": row.get("PROPOSE_DT", ""),
        "proposer": row.get("PROPOSER", ""),
        "bill_kind": row.get("BILL_KIND", ""),
        "link_url": row.get("LINK_URL", ""),
        "summary": "",  # 별도 수집 필요
        "collected_at": datetime.now().isoformat(),
    }


def load_master() -> dict:
    """마스터 데이터 로드"""
    if not MASTER_FILE.exists():
        return {"bills": [], "bill_ids": set()}

    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    bills = data.get("bills", [])
    bill_ids = set(b.get("bill_id") for b in bills)

    return {"bills": bills, "bill_ids": bill_ids}


def save_master(bills: list[dict]) -> None:
    """마스터 데이터 저장"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "description": "법안 마스터 데이터 (누적)",
        "updated_at": datetime.now().isoformat(),
        "total_count": len(bills),
        "bills": bills,
    }

    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[Ingest] 마스터 저장: {MASTER_FILE} ({len(bills)}건)")


def save_daily(bills: list[dict], date_str: str) -> Path:
    """일별 수집 데이터 저장"""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DAILY_DIR / f"{date_str}_bills.json"

    data = {
        "description": f"{date_str} 신규 법안",
        "collected_at": datetime.now().isoformat(),
        "count": len(bills),
        "bills": bills,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[Ingest] 일별 저장: {output_path} ({len(bills)}건)")
    return output_path


def merge_to_master(new_bills: list[dict]) -> dict:
    """
    신규 법안을 마스터에 병합

    Args:
        new_bills: 신규 법안 목록

    Returns:
        병합 결과 통계
    """
    master = load_master()
    existing_ids = master["bill_ids"]

    added = []
    skipped = 0

    for bill in new_bills:
        bill_id = bill.get("bill_id")
        if bill_id and bill_id not in existing_ids:
            master["bills"].append(bill)
            existing_ids.add(bill_id)
            added.append(bill)
        else:
            skipped += 1

    if added:
        save_master(master["bills"])

    result = {
        "new_count": len(new_bills),
        "added_count": len(added),
        "skipped_count": skipped,
        "total_count": len(master["bills"]),
    }

    print(f"[Ingest] 병합 완료: 신규 {len(new_bills)} → 추가 {len(added)}, 중복 {skipped}")
    return result


def run_daily_ingest(
    since_date: Optional[str] = None,
    save_daily_file: bool = True,
) -> dict:
    """
    일일 수집 실행

    Args:
        since_date: 기준 날짜 (기본: 어제)
        save_daily_file: 일별 파일 저장 여부

    Returns:
        수집 결과
    """
    if since_date is None:
        yesterday = datetime.now() - timedelta(days=1)
        since_date = yesterday.strftime("%Y-%m-%d")

    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"일일 법안 수집")
    print(f"{'='*60}")
    print(f"기준일: {since_date}")
    print(f"실행일: {today}")

    # 1. 신규 법안 수집
    new_bills = fetch_bills_since(since_date)

    result = {
        "since_date": since_date,
        "collected_at": datetime.now().isoformat(),
        "new_bills_count": len(new_bills),
        "new_bills": new_bills,
    }

    if not new_bills:
        print("[Ingest] 신규 법안 없음")
        return result

    # 2. 일별 파일 저장
    if save_daily_file:
        daily_path = save_daily(new_bills, today)
        result["daily_file"] = str(daily_path)

    # 3. 마스터 병합
    merge_result = merge_to_master(new_bills)
    result.update(merge_result)

    print(f"\n[Ingest] 완료!")
    return result


def init_master_from_merged():
    """
    기존 bills_merged.json에서 마스터 초기화

    최초 1회 실행용
    """
    merged_path = DATA_DIR / "bills_merged.json"

    if not merged_path.exists():
        print(f"[Ingest] bills_merged.json 없음")
        return

    with open(merged_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bills = data.get("bills", [])

    # collected_at 필드 추가
    for bill in bills:
        if "collected_at" not in bill:
            bill["collected_at"] = data.get("merged_at", datetime.now().isoformat())

    save_master(bills)
    print(f"[Ingest] 마스터 초기화 완료: {len(bills)}건")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="일일 법안 수집")
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="기준 날짜 (YYYY-MM-DD), 기본: 어제",
    )
    parser.add_argument(
        "--init-master",
        action="store_true",
        help="bills_merged.json에서 마스터 초기화",
    )

    args = parser.parse_args()

    if args.init_master:
        init_master_from_merged()
    else:
        run_daily_ingest(since_date=args.since)
