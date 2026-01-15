"""
법안 샘플링

- 22대 국회 법안에서 소관위별 균등 샘플링
- 임베딩 모델 비교 테스트용
"""
import os
import json
import requests
import random
from pathlib import Path
from typing import List, Dict
from collections import defaultdict
from dotenv import load_dotenv
import time

load_dotenv()

# API 설정
API_KEY = os.getenv("OPEN_ASSEMBLY_API_KEY", "")
BASE_URL = "https://open.assembly.go.kr/portal/openapi"

# 주요 상임위원회 (10개)
TARGET_COMMITTEES = [
    "산업통상자원중소벤처기업위원회",
    "기획재정위원회",
    "환경노동위원회",
    "국토교통위원회",
    "보건복지위원회",
    "교육위원회",
    "과학기술정보방송통신위원회",
    "농림축산식품해양수산위원회",
    "법제사법위원회",
    "행정안전위원회",
]

# 샘플링 설정
BILLS_PER_COMMITTEE = 10
TOTAL_BILLS = 100


def fetch_bills_by_committee(committee: str, page_size: int = 100) -> List[Dict]:
    """
    특정 상임위 법안 조회
    """
    endpoint = f"{BASE_URL}/TVBPMBILL11"

    params = {
        "Key": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": page_size,
        "AGE": 22,
        "CURR_COMMITTEE": committee,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        api_data = data.get("TVBPMBILL11", [])
        if not api_data or len(api_data) < 2:
            return []

        rows = api_data[1].get("row", [])
        return rows

    except Exception as e:
        print(f"[ERROR] {committee} 조회 실패: {e}")
        return []


def sample_bills():
    """
    소관위별 균등 샘플링
    """
    print("=" * 60)
    print("법안 샘플링 (22대 국회)")
    print("=" * 60)
    print(f"목표: {len(TARGET_COMMITTEES)}개 상임위 × {BILLS_PER_COMMITTEE}건 = {TOTAL_BILLS}건")
    print()

    all_samples = []
    committee_stats = {}

    for committee in TARGET_COMMITTEES:
        print(f"[수집] {committee}...")

        bills = fetch_bills_by_committee(committee, page_size=200)

        if not bills:
            print(f"  [WARN] 법안 없음")
            committee_stats[committee] = 0
            continue

        # 법률안만 필터링 (의안명에 '법률안' 포함)
        law_bills = [b for b in bills if '법률안' in b.get('BILL_NAME', '')]

        if len(law_bills) < BILLS_PER_COMMITTEE:
            print(f"  [WARN] 법률안 {len(law_bills)}건 (목표 미달)")
            sampled = law_bills
        else:
            # 랜덤 샘플링
            sampled = random.sample(law_bills, BILLS_PER_COMMITTEE)

        committee_stats[committee] = len(sampled)
        print(f"  조회: {len(bills)}건 → 법률안: {len(law_bills)}건 → 샘플: {len(sampled)}건")

        # 샘플 데이터 정리
        for bill in sampled:
            sample = {
                "bill_id": bill.get("BILL_ID"),
                "bill_no": bill.get("BILL_NO"),
                "bill_name": bill.get("BILL_NAME"),
                "proposer": bill.get("PROPOSER"),
                "committee": committee,
                "propose_dt": bill.get("PROPOSE_DT"),
                "proc_result": bill.get("PROC_RESULT"),
                "detail_link": bill.get("DETAIL_LINK"),
            }
            all_samples.append(sample)

        time.sleep(0.3)  # API 부하 방지

    print()
    print("=" * 60)
    print(f"샘플링 완료: 총 {len(all_samples)}건")
    print("=" * 60)

    for committee, count in committee_stats.items():
        short_name = committee[:10] + "..." if len(committee) > 10 else committee
        print(f"  {short_name}: {count}건")

    return all_samples, committee_stats


def save_samples(samples: List[Dict], output_path: str):
    """샘플 저장"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "description": "22대 국회 법안 샘플 (임베딩 비교 테스트용)",
        "sampling_method": "소관위별 균등 샘플링",
        "total_count": len(samples),
        "committees": list(set(s['committee'] for s in samples)),
        "bills": samples,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")


if __name__ == "__main__":
    # 랜덤 시드 고정 (재현성)
    random.seed(42)

    # 샘플링 실행
    samples, stats = sample_bills()

    # 저장
    output_path = Path(__file__).parent.parent / "data" / "test_bills.json"
    save_samples(samples, str(output_path))

    # 샘플 출력
    print("\n[샘플 미리보기]")
    for sample in samples[:5]:
        print(f"  - {sample['bill_name'][:40]}... ({sample['committee'][:10]})")
