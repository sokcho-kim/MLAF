"""
Golden Set 법안 수집

Cross-Domain 감지 테스트용 Golden Set 5건 수집
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPEN_ASSEMBLY_API_KEY", "")
BASE_URL = "https://open.assembly.go.kr/portal/openapi"

# Golden Set 정의
GOLDEN_SET = [
    {
        "id": "golden_1",
        "difficulty": "Easy",
        "keyword": "탄소중립기본법",
        "target_committee": "환경노동위원회",
        "risk_description": "탄소 배출권, 공장 가동 규제 이슈",
    },
    {
        "id": "golden_2",
        "difficulty": "Easy",
        "keyword": "중대재해",
        "target_committee": "법제사법위원회",
        "risk_description": "산업 현장 안전, 경영자 처벌 이슈",
    },
    {
        "id": "golden_3",
        "difficulty": "Medium",
        "keyword": "개인정보 보호법",
        "target_committee": "정무위원회",
        "risk_description": "자율주행, AI 등 신산업 데이터 활용 규제 이슈",
    },
    {
        "id": "golden_4",
        "difficulty": "Hard",
        "keyword": "약사법",
        "target_committee": "보건복지위원회",
        "risk_description": "의약품 제조 시설(공장) 설비 기준 강화 이슈 (핵심 타겟)",
    },
    {
        "id": "golden_5",
        "difficulty": "Hard",
        "keyword": "국유재산특례제한법",
        "target_committee": "기획재정위원회",
        "risk_description": "산업단지/경제자유구역 세제 혜택 제한 이슈",
    },
]


def search_bill(keyword: str, age: int = 22) -> dict | None:
    """법안 검색"""
    endpoint = f"{BASE_URL}/TVBPMBILL11"

    params = {
        "Key": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 20,
        "AGE": age,
        "BILL_NAME": keyword,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        api_data = data.get("TVBPMBILL11", [])
        if not api_data or len(api_data) < 2:
            return None

        rows = api_data[1].get("row", [])
        if not rows:
            return None

        # 가장 최신 법안 반환
        return rows[0]

    except Exception as e:
        print(f"[ERROR] '{keyword}' 검색 실패: {e}")
        return None


def fetch_golden_set():
    """Golden Set 수집"""
    print("=" * 60)
    print("Golden Set 법안 수집")
    print("=" * 60)

    results = []

    for item in GOLDEN_SET:
        print(f"\n[{item['difficulty']}] {item['keyword']}...")

        bill = search_bill(item['keyword'])

        if bill:
            golden_bill = {
                "golden_id": item['id'],
                "difficulty": item['difficulty'],
                "risk_description": item['risk_description'],
                "bill_id": bill.get("BILL_ID"),
                "bill_no": bill.get("BILL_NO"),
                "bill_name": bill.get("BILL_NAME"),
                "proposer": bill.get("PROPOSER"),
                "committee": bill.get("CURR_COMMITTEE") or item['target_committee'],
                "propose_dt": bill.get("PROPOSE_DT"),
                "proc_result": bill.get("PROC_RESULT"),
            }
            results.append(golden_bill)
            print(f"  [O] {golden_bill['bill_name'][:40]}...")
            print(f"      소관위: {golden_bill['committee']}")
        else:
            print(f"  [X] 검색 실패")
            # 수동 입력용 placeholder
            results.append({
                "golden_id": item['id'],
                "difficulty": item['difficulty'],
                "risk_description": item['risk_description'],
                "bill_id": None,
                "bill_name": f"{item['keyword']} (검색 실패)",
                "committee": item['target_committee'],
            })

    return results


def save_golden_set(data: list, output_path: str):
    """저장"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "description": "Cross-Domain 감지 테스트용 Golden Set",
        "target_ministry": "산업통상자원부",
        "total_count": len(data),
        "difficulty_breakdown": {
            "Easy": len([d for d in data if d['difficulty'] == 'Easy']),
            "Medium": len([d for d in data if d['difficulty'] == 'Medium']),
            "Hard": len([d for d in data if d['difficulty'] == 'Hard']),
        },
        "bills": data,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")


if __name__ == "__main__":
    golden_bills = fetch_golden_set()

    output_path = Path(__file__).parent.parent / "data" / "golden_set.json"
    save_golden_set(golden_bills, str(output_path))

    print("\n" + "=" * 60)
    print("Golden Set 요약")
    print("=" * 60)
    for bill in golden_bills:
        status = "O" if bill.get('bill_id') else "X"
        print(f"[{status}] [{bill['difficulty']}] {bill.get('bill_name', 'N/A')[:35]}")
