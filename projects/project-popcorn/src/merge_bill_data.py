"""
데이터 조인 스크립트

bills_raw_assembly.json + bills_raw_summary.json
→ bills_merged.json

조인 키: bill_no
"""
import json
from pathlib import Path
from collections import Counter
import random

DATA_DIR = Path(__file__).parent.parent / "data"


def load_data():
    """수집 데이터 로드"""
    assembly_path = DATA_DIR / "bills_raw_assembly.json"
    summary_path = DATA_DIR / "bills_raw_summary.json"

    if not assembly_path.exists():
        raise FileNotFoundError(f"파일 없음: {assembly_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"파일 없음: {summary_path}")

    with open(assembly_path, encoding="utf-8") as f:
        assembly_data = json.load(f)

    with open(summary_path, encoding="utf-8") as f:
        summary_data = json.load(f)

    return assembly_data, summary_data


def merge_data(assembly_data: dict, summary_data: dict) -> list:
    """
    데이터 조인

    Args:
        assembly_data: 의안상세정보 데이터
        summary_data: BillInfoService2 데이터

    Returns:
        조인된 법안 목록
    """
    print("=" * 60)
    print("데이터 조인")
    print("=" * 60)

    assembly_bills = assembly_data.get("bills", [])
    summary_bills = summary_data.get("bills", {})

    print(f"의안상세정보: {len(assembly_bills)}건")
    print(f"BillInfoService2: {len(summary_bills)}건")

    # 조인
    merged = []
    matched = 0
    with_summary = 0

    for bill in assembly_bills:
        bill_no = bill.get("bill_no", "")

        # summary 조인
        if bill_no and bill_no in summary_bills:
            summary_info = summary_bills[bill_no]
            bill["summary"] = summary_info.get("summary", "")
            matched += 1
            if bill["summary"]:
                with_summary += 1
        else:
            bill["summary"] = ""

        merged.append(bill)

    print(f"\n조인 결과:")
    print(f"  총 건수: {len(merged)}")
    print(f"  매칭 성공: {matched} ({matched/len(merged)*100:.1f}%)")
    print(f"  summary 있음: {with_summary} ({with_summary/len(merged)*100:.1f}%)")

    # 조인 실패 분석
    assembly_bill_nos = {b["bill_no"] for b in assembly_bills}
    summary_bill_nos = set(summary_bills.keys())

    only_assembly = assembly_bill_nos - summary_bill_nos
    only_summary = summary_bill_nos - assembly_bill_nos

    print(f"\n조인 분석:")
    print(f"  의안상세정보에만 있음: {len(only_assembly)}건")
    print(f"  BillInfoService2에만 있음: {len(only_summary)}건")

    return merged


def analyze_merged(bills: list) -> dict:
    """조인된 데이터 품질 분석"""
    total = len(bills)
    if total == 0:
        return {}

    stats = {
        "total": total,
        "committee_filled": sum(1 for b in bills if b.get("committee")),
        "proc_result_filled": sum(1 for b in bills if b.get("proc_result")),
        "summary_filled": sum(1 for b in bills if b.get("summary")),
        "vote_filled": sum(1 for b in bills if b.get("vote_info", {}).get("total", 0) > 0),
    }

    stats["committee_rate"] = f"{stats['committee_filled']/total*100:.1f}%"
    stats["proc_result_rate"] = f"{stats['proc_result_filled']/total*100:.1f}%"
    stats["summary_rate"] = f"{stats['summary_filled']/total*100:.1f}%"
    stats["vote_rate"] = f"{stats['vote_filled']/total*100:.1f}%"

    return stats


def sample_bills(bills: list, n: int = 100, require_summary: bool = True) -> list:
    """
    소관위별 균등 샘플링

    Args:
        bills: 전체 법안 목록
        n: 샘플 크기
        require_summary: summary 있는 법안만 선택

    Returns:
        샘플링된 법안 목록
    """
    print("\n" + "=" * 60)
    print(f"샘플링 ({n}건)")
    print("=" * 60)

    # 필터링
    if require_summary:
        candidates = [b for b in bills if b.get("summary") and b.get("committee")]
        print(f"후보 (summary+committee 있음): {len(candidates)}건")
    else:
        candidates = [b for b in bills if b.get("committee")]
        print(f"후보 (committee 있음): {len(candidates)}건")

    # 소관위별 그룹화
    by_committee = {}
    for b in candidates:
        cm = b.get("committee", "")
        if cm not in by_committee:
            by_committee[cm] = []
        by_committee[cm].append(b)

    print(f"소관위 수: {len(by_committee)}")

    # 균등 샘플링
    per_committee = max(1, n // len(by_committee))
    sampled = []

    for cm, cm_bills in by_committee.items():
        sample_size = min(per_committee, len(cm_bills))
        sampled.extend(random.sample(cm_bills, sample_size))

    # 부족하면 추가 샘플링
    remaining = n - len(sampled)
    if remaining > 0:
        not_sampled = [b for b in candidates if b not in sampled]
        if not_sampled:
            sampled.extend(random.sample(not_sampled, min(remaining, len(not_sampled))))

    # 초과하면 자르기
    sampled = sampled[:n]

    # 샘플 분포 확인
    sample_committees = Counter(b.get("committee") for b in sampled)
    print(f"\n샘플 소관위 분포:")
    for cm, count in sample_committees.most_common(10):
        print(f"  {cm}: {count}건")

    return sampled


def main():
    """메인 실행"""
    # 데이터 로드
    assembly_data, summary_data = load_data()

    # 조인
    merged = merge_data(assembly_data, summary_data)

    # 품질 분석
    print("\n" + "=" * 60)
    print("통합 데이터 품질")
    print("=" * 60)
    stats = analyze_merged(merged)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 처리결과 분포
    proc_results = Counter(b.get("proc_result") or "(미처리)" for b in merged)
    print("\n처리결과 분포:")
    for pr, count in proc_results.most_common():
        print(f"  {pr}: {count}건")

    # 저장: 전체 데이터
    import time
    output_path = DATA_DIR / "bills_merged.json"
    result = {
        "description": "의안상세정보 + summary 조인 결과",
        "merged_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stats": stats,
        "bills": merged,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n전체 데이터 저장: {output_path}")

    # 저장: 샘플 100건
    sampled = sample_bills(merged, n=100, require_summary=True)
    sample_path = DATA_DIR / "bills_sample_100.json"
    sample_result = {
        "description": "테스트용 법안 샘플 (소관위별 균등)",
        "sampled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(sampled),
        "bills": sampled,
    }

    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(sample_result, f, ensure_ascii=False, indent=2)
    print(f"샘플 데이터 저장: {sample_path}")


if __name__ == "__main__":
    main()
