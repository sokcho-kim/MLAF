"""
Bill Radar Pipeline v2

메인 파이프라인: 법안 스캔 → 리스크 감지 → 리포트 생성
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from .radar import CrossDomainRadar, RiskAlert
    from .reporter import Reporter
except ImportError:
    from radar import CrossDomainRadar, RiskAlert
    from reporter import Reporter


class BillRadarPipeline:
    """Cross-Domain 법안 감지 파이프라인"""

    def __init__(
        self,
        ministry: str = "산업통상부",
        threshold: float = 0.45,
        data_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        Args:
            ministry: 타겟 부처명
            threshold: 관련 법안 판정 임계값
            data_dir: 데이터 디렉토리
            output_dir: 출력 디렉토리
        """
        self.ministry = ministry
        self.threshold = threshold
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.output_dir = output_dir or Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 레이더 초기화
        self.radar = CrossDomainRadar(
            ministry_name=ministry,
            threshold=threshold,
            data_dir=self.data_dir,
        )

        # 리포터 초기화
        self.reporter = Reporter(output_dir=self.output_dir)

    def run_full_scan(
        self,
        bills_file: Optional[Path] = None,
        generate_report: bool = True,
    ) -> dict:
        """
        전체 법안 스캔 (1,021건)

        Args:
            bills_file: 법안 JSON 파일 경로
            generate_report: 리포트 생성 여부

        Returns:
            스캔 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"Full Scan: {self.ministry}")
        print(f"{'='*60}")
        print(f"Threshold: {self.threshold}")
        print(f"Data dir: {self.data_dir}")

        # 법안 로드
        if bills_file is None:
            bills_file = self.data_dir / "bills_merged.json"

        print(f"\nLoading bills from: {bills_file}")
        with open(bills_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        bills = data.get("bills", data)
        print(f"Total bills: {len(bills)}")

        # 스캔 실행
        print(f"\nScanning...")
        alerts = self.radar.scan_bills(bills, show_progress=True)

        # 결과 구성
        result = {
            "scan_type": "full_scan",
            "ministry": self.ministry,
            "threshold": self.threshold,
            "scanned_at": datetime.now().isoformat(),
            "total_bills": len(bills),
            "total_alerts": len(alerts),
            "alerts_by_level": self._count_by_level(alerts),
            "alerts": alerts,
        }

        # 결과 저장
        result_path = self._save_result(result, "full_scan")
        print(f"\nResults saved: {result_path}")

        # 리포트 생성
        if generate_report:
            report_path = self.reporter.generate_full_scan_report(result)
            print(f"Report saved: {report_path}")
            result["report_path"] = str(report_path)

        # 요약 출력
        self.radar.print_summary(alerts)

        return result

    def run_daily(
        self,
        since_date: Optional[datetime] = None,
        generate_report: bool = True,
    ) -> dict:
        """
        일일 스캔 (신규 법안만)

        Args:
            since_date: 이 날짜 이후 법안만 스캔 (기본: 어제)
            generate_report: 리포트 생성 여부

        Returns:
            스캔 결과 딕셔너리
        """
        if since_date is None:
            since_date = datetime.now() - timedelta(days=1)

        since_str = since_date.strftime("%Y-%m-%d")

        print(f"\n{'='*60}")
        print(f"Daily Scan: {self.ministry}")
        print(f"{'='*60}")
        print(f"Since: {since_str}")

        # 법안 로드
        bills_file = self.data_dir / "bills_merged.json"
        with open(bills_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        all_bills = data.get("bills", data)

        # 날짜 필터링
        new_bills = [
            bill for bill in all_bills
            if bill.get("propose_dt", "") >= since_str
        ]
        print(f"New bills since {since_str}: {len(new_bills)}")

        if not new_bills:
            print("No new bills to scan.")
            return {
                "scan_type": "daily",
                "ministry": self.ministry,
                "since_date": since_str,
                "total_bills": 0,
                "total_alerts": 0,
                "alerts": [],
            }

        # 스캔 실행
        alerts = self.radar.scan_bills(new_bills, show_progress=True)

        # 결과 구성
        result = {
            "scan_type": "daily",
            "ministry": self.ministry,
            "threshold": self.threshold,
            "since_date": since_str,
            "scanned_at": datetime.now().isoformat(),
            "total_bills": len(new_bills),
            "total_alerts": len(alerts),
            "alerts_by_level": self._count_by_level(alerts),
            "alerts": alerts,
        }

        # 결과 저장
        result_path = self._save_result(result, "daily")
        print(f"\nResults saved: {result_path}")

        # 리포트 생성
        if generate_report and alerts:
            report_path = self.reporter.generate_daily_report(result)
            print(f"Report saved: {report_path}")
            result["report_path"] = str(report_path)

        # 요약 출력
        if alerts:
            self.radar.print_summary(alerts)

        return result

    def run_golden_test(self) -> dict:
        """
        Golden Set 테스트

        Returns:
            테스트 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"Golden Set Test: {self.ministry}")
        print(f"{'='*60}")

        golden_path = self.data_dir / "golden_set_v2.json"
        if not golden_path.exists():
            print(f"Golden set not found: {golden_path}")
            return {"error": "Golden set not found"}

        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)

        bills = golden.get("bills", golden)
        print(f"Golden bills: {len(bills)}")

        # 스캔 실행
        alerts = self.radar.scan_bills(bills, show_progress=False)

        # 결과 구성
        result = {
            "scan_type": "golden_test",
            "ministry": self.ministry,
            "threshold": self.threshold,
            "scanned_at": datetime.now().isoformat(),
            "total_bills": len(bills),
            "detected": len(alerts),
            "detection_rate": len(alerts) / len(bills) if bills else 0,
            "alerts": alerts,
        }

        # 요약 출력
        print(f"\nDetection Rate: {result['detection_rate']:.1%} ({len(alerts)}/{len(bills)})")
        self.radar.print_summary(alerts)

        return result

    def _count_by_level(self, alerts: list[RiskAlert]) -> dict:
        """Alert Level별 집계"""
        from .scorer import AlertLevel
        return {
            level.value: len([a for a in alerts if a.alert_level == level.value])
            for level in AlertLevel
            if level.value != "NONE"
        }

    def _save_result(self, result: dict, scan_type: str) -> Path:
        """결과를 JSON으로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scan_type}_{timestamp}.json"
        output_path = self.output_dir / filename

        # alerts를 직렬화 가능하게 변환
        serializable = result.copy()
        serializable["alerts"] = [
            alert.to_dict() if hasattr(alert, "to_dict") else alert
            for alert in result.get("alerts", [])
        ]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)

        return output_path


def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(description="Bill Radar Pipeline")
    parser.add_argument(
        "--mode",
        choices=["full", "daily", "golden"],
        default="golden",
        help="Scan mode",
    )
    parser.add_argument(
        "--ministry",
        default="산업통상부",
        help="Target ministry name",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.45,
        help="Detection threshold",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip report generation",
    )

    args = parser.parse_args()

    pipeline = BillRadarPipeline(
        ministry=args.ministry,
        threshold=args.threshold,
    )

    if args.mode == "full":
        pipeline.run_full_scan(generate_report=not args.no_report)
    elif args.mode == "daily":
        pipeline.run_daily(generate_report=not args.no_report)
    elif args.mode == "golden":
        pipeline.run_golden_test()


if __name__ == "__main__":
    main()
