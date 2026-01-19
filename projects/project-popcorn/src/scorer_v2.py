"""
동적 스코어링 모듈 v2

기능:
- 부처별 동적 임계값
- 키워드 가산점 로직
- 설정 파일 기반 운영

공식:
  최종 스코어 = CosineSim(법안, R&R) + 키워드 가산점
  키워드 가산점 = min(매칭수 × keyword_bonus, max_bonus)
"""
import re
import yaml
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from .scorer import AlertLevel, ScoreResult, Scorer
except ImportError:
    from scorer import AlertLevel, ScoreResult, Scorer


@dataclass
class ScoreResultV2:
    """v2 스코어링 결과"""
    base_score: float          # 기본 유사도
    keyword_bonus: float       # 키워드 가산점
    matched_keywords: list[str]  # 매칭된 키워드
    final_score: float         # 최종 스코어
    threshold: float           # 적용된 임계값
    alert_level: str           # Alert Level
    is_relevant: bool          # 관련 여부


class MinistryConfig:
    """부처 설정 로더"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "ministry_config.yaml"

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """설정 파일 로드"""
        if not self.config_path.exists():
            print(f"[Config] 설정 파일 없음: {self.config_path}")
            return {"ministries": {}, "global": {}}

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_ministry(self, ministry_name: str) -> dict:
        """부처 설정 조회"""
        ministries = self.config.get("ministries", {})
        default = self.config.get("global", {}).get("default", {})

        # 정확한 매칭
        if ministry_name in ministries:
            return ministries[ministry_name]

        # 부분 매칭 (산업통상자원부 → 산업통상부)
        for name, config in ministries.items():
            if name in ministry_name or ministry_name in name:
                return config

        return default

    def get_global(self) -> dict:
        """글로벌 설정 조회"""
        return self.config.get("global", {})

    def list_ministries(self) -> list[str]:
        """부처 목록 조회"""
        return list(self.config.get("ministries", {}).keys())


class ScorerV2:
    """동적 스코어링 클래스 v2"""

    def __init__(
        self,
        ministry_name: str,
        config: Optional[MinistryConfig] = None,
    ):
        """
        Args:
            ministry_name: 타겟 부처명
            config: MinistryConfig 인스턴스
        """
        self.ministry_name = ministry_name
        self.config = config or MinistryConfig()

        # 부처 설정 로드
        ministry_config = self.config.get_ministry(ministry_name)
        global_config = self.config.get_global()

        self.threshold = ministry_config.get("threshold", 0.45)
        self.ministry_type = ministry_config.get("type", "중간형")
        self.keywords = ministry_config.get("keywords", [])
        self.keyword_bonus = ministry_config.get("keyword_bonus", 0.02)
        self.max_bonus = global_config.get("max_keyword_bonus", 0.05)

        # Alert Level 설정
        self.alert_thresholds = global_config.get("alert_levels", {
            "CRITICAL": 0.75,
            "HIGH": 0.65,
            "MEDIUM": 0.55,
            "LOW": self.threshold,
        })

        print(f"[ScorerV2] {ministry_name}: threshold={self.threshold}, keywords={len(self.keywords)}")

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """코사인 유사도 계산"""
        a = np.array(vec_a)
        b = np.array(vec_b)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))

    def calculate_keyword_bonus(self, bill: dict) -> tuple[float, list[str]]:
        """
        키워드 가산점 계산

        Args:
            bill: 법안 딕셔너리

        Returns:
            (가산점, 매칭된 키워드 목록)
        """
        if not self.keywords:
            return 0.0, []

        title = bill.get("bill_name", "")
        matched = []

        for keyword in self.keywords:
            # 대소문자 무시, 부분 매칭
            if keyword.lower() in title.lower():
                matched.append(keyword)

        bonus = min(len(matched) * self.keyword_bonus, self.max_bonus)
        return bonus, matched

    def get_alert_level(self, score: float) -> str:
        """스코어에 따른 Alert Level 결정"""
        if score >= self.alert_thresholds.get("CRITICAL", 0.75):
            return "CRITICAL"
        elif score >= self.alert_thresholds.get("HIGH", 0.65):
            return "HIGH"
        elif score >= self.alert_thresholds.get("MEDIUM", 0.55):
            return "MEDIUM"
        elif score >= self.threshold:
            return "LOW"
        else:
            return "NONE"

    def score_bill(
        self,
        bill: dict,
        bill_vector: list[float],
        rr_vector: list[float],
    ) -> ScoreResultV2:
        """
        법안 스코어링 (v2)

        Args:
            bill: 법안 딕셔너리
            bill_vector: 법안 임베딩 벡터
            rr_vector: 부처 R&R 임베딩 벡터

        Returns:
            ScoreResultV2 객체
        """
        # 1. 기본 유사도
        base_score = self.cosine_similarity(bill_vector, rr_vector)

        # 2. 키워드 가산점
        keyword_bonus, matched_keywords = self.calculate_keyword_bonus(bill)

        # 3. 최종 스코어
        final_score = base_score + keyword_bonus

        # 4. Alert Level
        alert_level = self.get_alert_level(final_score)

        # 5. 관련 여부
        is_relevant = final_score >= self.threshold

        return ScoreResultV2(
            base_score=round(base_score, 4),
            keyword_bonus=round(keyword_bonus, 4),
            matched_keywords=matched_keywords,
            final_score=round(final_score, 4),
            threshold=self.threshold,
            alert_level=alert_level,
            is_relevant=is_relevant,
        )

    def score_batch(
        self,
        bills: list[dict],
        bill_vectors: list[list[float]],
        rr_vector: list[float],
    ) -> list[ScoreResultV2]:
        """
        배치 스코어링

        Args:
            bills: 법안 목록
            bill_vectors: 법안 임베딩 벡터 목록
            rr_vector: 부처 R&R 임베딩 벡터

        Returns:
            ScoreResultV2 목록
        """
        results = []
        for bill, vec in zip(bills, bill_vectors):
            result = self.score_bill(bill, vec, rr_vector)
            results.append(result)
        return results


def demo():
    """데모 실행"""
    print("=" * 60)
    print("ScorerV2 데모")
    print("=" * 60)

    # 설정 로드
    config = MinistryConfig()
    print(f"\n등록된 부처: {config.list_ministries()}")

    # 산업통상부 스코어러
    scorer = ScorerV2("산업통상부", config)
    print(f"\n산업통상부 설정:")
    print(f"  - threshold: {scorer.threshold}")
    print(f"  - keywords: {scorer.keywords}")
    print(f"  - keyword_bonus: {scorer.keyword_bonus}")

    # 테스트 케이스
    test_bills = [
        {"bill_name": "탄소중립·녹색성장 기본법 일부개정법률안"},
        {"bill_name": "에너지이용 합리화법 일부개정법률안"},
        {"bill_name": "도로교통법 일부개정법률안"},  # 키워드 없음
    ]

    print(f"\n키워드 가산점 테스트:")
    for bill in test_bills:
        bonus, matched = scorer.calculate_keyword_bonus(bill)
        print(f"  {bill['bill_name'][:30]}...")
        print(f"    → 매칭: {matched}, 가산점: +{bonus}")


if __name__ == "__main__":
    demo()
