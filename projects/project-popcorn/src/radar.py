"""
Cross-Domain Radar: 리스크 감지 모듈

기능: 신규 법안 텍스트 vs 부처 R&R 벡터 간 의미적 유사도 분석
로직: 임베딩 v2 전략 (제목+summary) + 임계값 0.45 기반 감지
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .embedder import Embedder, get_embedder
    from .scorer import Scorer, AlertLevel, ScoreResult
except ImportError:
    from embedder import Embedder, get_embedder
    from scorer import Scorer, AlertLevel, ScoreResult


@dataclass
class RiskAlert:
    """리스크 경고 데이터 클래스"""
    bill_id: str
    bill_no: str
    bill_name: str
    committee: str  # 소관 상임위
    target_ministry: str  # 영향받는 부처
    similarity_score: float
    alert_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    propose_dt: str
    proposer: str
    summary_preview: str  # summary 앞 200자
    detected_at: str

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return asdict(self)


class CrossDomainRadar:
    """Cross-Domain 법안 감지 레이더"""

    def __init__(
        self,
        ministry_name: str = "산업통상부",
        threshold: float = 0.45,
        data_dir: Optional[Path] = None,
    ):
        """
        Args:
            ministry_name: 타겟 부처명
            threshold: 관련 법안 판정 임계값
            data_dir: 데이터 디렉토리 경로
        """
        self.ministry_name = ministry_name
        self.threshold = threshold
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"

        # 모듈 초기화
        self.embedder = Embedder(
            cache_dir=self.data_dir / "cache"
        )
        self.scorer = Scorer(threshold=threshold)

        # R&R 로드 및 임베딩
        self.ministry_rr = self._load_ministry_rr()
        self.rr_vector = self.embedder.embed_text(self.ministry_rr)

    def _load_ministry_rr(self) -> str:
        """부처 R&R 텍스트 로드"""
        rr_path = self.data_dir / "ministry_rr_augmented.json"

        with open(rr_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for ministry in data["ministries"]:
            if self.ministry_name in ministry["ministry_name"]:
                return ministry.get("augmented_text", ministry.get("rr_text", ""))

        raise ValueError(f"Ministry not found: {self.ministry_name}")

    def detect_risk(self, bill: dict) -> Optional[RiskAlert]:
        """
        단일 법안에 대해 Cross-Domain 리스크 감지

        Args:
            bill: 법안 딕셔너리

        Returns:
            RiskAlert if risk detected, None otherwise
        """
        # 법안 임베딩
        bill_vector = self.embedder.embed_bill(bill)

        # 스코어링
        result = self.scorer.score_bill(bill_vector, self.rr_vector)

        # 임계값 미달 시 None
        if not result.is_relevant:
            return None

        # RiskAlert 생성
        summary = bill.get("summary", "")
        return RiskAlert(
            bill_id=bill.get("bill_id", ""),
            bill_no=bill.get("bill_no", ""),
            bill_name=bill.get("bill_name", ""),
            committee=bill.get("committee", ""),
            target_ministry=self.ministry_name,
            similarity_score=round(result.score, 4),
            alert_level=result.alert_level.value,
            propose_dt=bill.get("propose_dt", ""),
            proposer=bill.get("proposer", ""),
            summary_preview=summary[:200] + "..." if len(summary) > 200 else summary,
            detected_at=datetime.now().isoformat(),
        )

    def scan_bills(
        self,
        bills: list[dict],
        show_progress: bool = True,
    ) -> list[RiskAlert]:
        """
        여러 법안 스캔

        Args:
            bills: 법안 딕셔너리 리스트
            show_progress: 진행 상황 출력 여부

        Returns:
            감지된 RiskAlert 리스트
        """
        alerts = []
        total = len(bills)

        for i, bill in enumerate(bills):
            alert = self.detect_risk(bill)
            if alert:
                alerts.append(alert)

            if show_progress and (i + 1) % 50 == 0:
                print(f"  Scanned: {i + 1}/{total} (alerts: {len(alerts)})")

        # 스코어 내림차순 정렬
        alerts.sort(key=lambda x: x.similarity_score, reverse=True)

        if show_progress:
            print(f"  Complete: {total} bills scanned, {len(alerts)} alerts")

        return alerts

    def scan_from_file(
        self,
        bills_file: Optional[Path] = None,
    ) -> list[RiskAlert]:
        """
        파일에서 법안 로드 후 스캔

        Args:
            bills_file: 법안 JSON 파일 경로

        Returns:
            감지된 RiskAlert 리스트
        """
        if bills_file is None:
            bills_file = self.data_dir / "bills_merged.json"

        with open(bills_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        bills = data.get("bills", data)  # bills 키 또는 직접 리스트
        return self.scan_bills(bills)

    def export_alerts(
        self,
        alerts: list[RiskAlert],
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        알림을 JSON으로 저장

        Args:
            alerts: RiskAlert 리스트
            output_path: 출력 파일 경로

        Returns:
            저장된 파일 경로
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.data_dir / f"alerts_{timestamp}.json"

        result = {
            "ministry": self.ministry_name,
            "threshold": self.threshold,
            "scanned_at": datetime.now().isoformat(),
            "total_alerts": len(alerts),
            "alerts_by_level": {
                level.value: len([a for a in alerts if a.alert_level == level.value])
                for level in AlertLevel
                if level != AlertLevel.NONE
            },
            "alerts": [alert.to_dict() for alert in alerts],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return output_path

    def print_summary(self, alerts: list[RiskAlert]) -> None:
        """알림 요약 출력"""
        print(f"\n{'='*60}")
        print(f"Cross-Domain Radar Results: {self.ministry_name}")
        print(f"{'='*60}")
        print(f"Threshold: {self.threshold}")
        print(f"Total Alerts: {len(alerts)}")
        print()

        # Level별 집계
        for level in [AlertLevel.CRITICAL, AlertLevel.HIGH, AlertLevel.MEDIUM, AlertLevel.LOW]:
            count = len([a for a in alerts if a.alert_level == level.value])
            if count > 0:
                print(f"  {level.value}: {count}")

        # Top 10 출력
        print(f"\n{'─'*60}")
        print("Top 10 Alerts:")
        print(f"{'─'*60}")

        for i, alert in enumerate(alerts[:10], 1):
            print(f"\n{i}. [{alert.alert_level}] {alert.bill_name[:40]}...")
            print(f"   Score: {alert.similarity_score:.4f} | Committee: {alert.committee}")
            print(f"   Proposer: {alert.proposer} | Date: {alert.propose_dt}")


# 편의 함수
def scan_bills_for_ministry(
    ministry_name: str = "산업통상부",
    threshold: float = 0.45,
) -> list[RiskAlert]:
    """특정 부처에 대해 법안 스캔 (편의 함수)"""
    radar = CrossDomainRadar(
        ministry_name=ministry_name,
        threshold=threshold,
    )
    return radar.scan_from_file()


if __name__ == "__main__":
    # 테스트 실행
    print("Cross-Domain Radar Test")
    print("=" * 60)

    radar = CrossDomainRadar(
        ministry_name="산업통상부",
        threshold=0.45,
    )

    print(f"Ministry: {radar.ministry_name}")
    print(f"R&R length: {len(radar.ministry_rr)} chars")
    print(f"R&R vector dim: {len(radar.rr_vector)}")

    # Golden Set 테스트
    golden_path = radar.data_dir / "golden_set_v2.json"
    if golden_path.exists():
        print(f"\nTesting with Golden Set...")
        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)

        alerts = radar.scan_bills(golden["bills"], show_progress=False)
        radar.print_summary(alerts)
