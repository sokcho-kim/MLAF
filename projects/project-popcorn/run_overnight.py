"""
야간 배치 작업: 부처별 스캔 + 임계값 비교
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent))
from src.pipeline import BillRadarPipeline
from src.radar import CrossDomainRadar

OUTPUT_DIR = Path(__file__).parent / "output" / "overnight_batch"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 부처 목록
MINISTRIES = [
    "과학기술정보통신부",
    "교육부",
    "외교부",
    "법무부",
    "국방부",
    "행정안전부",
    "문화체육관광부",
    "농림축산식품부",
    "보건복지부",
    "기후에너지환경부",
    "고용노동부",
    "국토교통부",
    "해양수산부",
    # 산업통상부는 이미 완료
]

# 임계값 목록
THRESHOLDS = [0.40, 0.42, 0.44, 0.45, 0.48, 0.50]


def run_ministry_scans():
    """부처별 스캔"""
    print("\n" + "=" * 60)
    print("PART 1: 부처별 스캔")
    print("=" * 60)

    results = []

    for i, ministry in enumerate(MINISTRIES, 1):
        print(f"\n[{i}/{len(MINISTRIES)}] {ministry}")
        print("-" * 40)

        try:
            pipeline = BillRadarPipeline(
                ministry=ministry,
                threshold=0.45,
                output_dir=OUTPUT_DIR / "ministries",
            )
            result = pipeline.run_full_scan(generate_report=True)

            summary = {
                "ministry": ministry,
                "total_bills": result.get("total_bills", 0),
                "total_alerts": result.get("total_alerts", 0),
                "detection_rate": result.get("total_alerts", 0) / result.get("total_bills", 1),
                "alerts_by_level": result.get("alerts_by_level", {}),
            }
            results.append(summary)

            print(f"  → 감지: {summary['total_alerts']}/{summary['total_bills']} ({summary['detection_rate']:.1%})")

        except Exception as e:
            print(f"  → ERROR: {e}")
            results.append({"ministry": ministry, "error": str(e)})

    # 결과 저장
    output_path = OUTPUT_DIR / "ministry_scan_summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "scanned_at": datetime.now().isoformat(),
            "total_ministries": len(MINISTRIES),
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n부처별 스캔 완료: {output_path}")
    return results


def run_threshold_comparison():
    """임계값 비교 테스트"""
    print("\n" + "=" * 60)
    print("PART 2: 임계값 비교 테스트 (산업통상부 기준)")
    print("=" * 60)

    results = []

    for threshold in THRESHOLDS:
        print(f"\n임계값: {threshold}")
        print("-" * 40)

        try:
            pipeline = BillRadarPipeline(
                ministry="산업통상부",
                threshold=threshold,
                output_dir=OUTPUT_DIR / "thresholds",
            )
            result = pipeline.run_full_scan(generate_report=False)

            summary = {
                "threshold": threshold,
                "total_alerts": result.get("total_alerts", 0),
                "detection_rate": result.get("total_alerts", 0) / result.get("total_bills", 1),
                "alerts_by_level": result.get("alerts_by_level", {}),
            }
            results.append(summary)

            print(f"  → 감지: {summary['total_alerts']} ({summary['detection_rate']:.1%})")

        except Exception as e:
            print(f"  → ERROR: {e}")
            results.append({"threshold": threshold, "error": str(e)})

    # 결과 저장
    output_path = OUTPUT_DIR / "threshold_comparison.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "scanned_at": datetime.now().isoformat(),
            "ministry": "산업통상부",
            "thresholds_tested": THRESHOLDS,
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n임계값 비교 완료: {output_path}")
    return results


def generate_summary_report(ministry_results, threshold_results):
    """최종 요약 리포트 생성"""
    report_path = OUTPUT_DIR / "overnight_summary.md"

    lines = [
        "# 야간 배치 작업 결과",
        "",
        f"> **실행 시간:** {datetime.now().isoformat()}",
        "",
        "---",
        "",
        "## 1. 부처별 스캔 결과",
        "",
        "| 부처 | 감지 법안 | 감지율 | HIGH | MEDIUM | LOW |",
        "|------|----------|--------|------|--------|-----|",
    ]

    for r in ministry_results:
        if "error" in r:
            lines.append(f"| {r['ministry']} | ERROR | - | - | - | - |")
        else:
            levels = r.get("alerts_by_level", {})
            lines.append(
                f"| {r['ministry']} | {r['total_alerts']} | "
                f"{r['detection_rate']:.1%} | "
                f"{levels.get('HIGH', 0)} | "
                f"{levels.get('MEDIUM', 0)} | "
                f"{levels.get('LOW', 0)} |"
            )

    lines.extend([
        "",
        "---",
        "",
        "## 2. 임계값 비교 (산업통상부)",
        "",
        "| 임계값 | 감지 법안 | 감지율 |",
        "|--------|----------|--------|",
    ])

    for r in threshold_results:
        if "error" in r:
            lines.append(f"| {r['threshold']} | ERROR | - |")
        else:
            lines.append(f"| {r['threshold']} | {r['total_alerts']} | {r['detection_rate']:.1%} |")

    lines.extend([
        "",
        "---",
        "",
        f"*Generated at {datetime.now().isoformat()}*",
    ])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n최종 리포트: {report_path}")


def main():
    print("\n" + "=" * 60)
    print("야간 배치 작업 시작")
    print(f"시작 시간: {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. 부처별 스캔
    ministry_results = run_ministry_scans()

    # 2. 임계값 비교
    threshold_results = run_threshold_comparison()

    # 3. 최종 리포트
    generate_summary_report(ministry_results, threshold_results)

    print("\n" + "=" * 60)
    print("야간 배치 작업 완료!")
    print(f"종료 시간: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
