"""
유사도 계산 모듈

코사인 유사도 기반으로 법안과 부처 R&R 간 관련성을 스코어링합니다.
"""
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AlertLevel(Enum):
    """경고 수준"""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ScoreResult:
    """스코어링 결과"""
    score: float
    alert_level: AlertLevel
    is_relevant: bool


class Scorer:
    """유사도 스코어링 클래스"""

    # 기본 임계값 (임베딩 v2 테스트 결과 기반)
    DEFAULT_THRESHOLD = 0.45

    # Alert Level 임계값
    LEVEL_THRESHOLDS = {
        AlertLevel.LOW: 0.45,
        AlertLevel.MEDIUM: 0.55,
        AlertLevel.HIGH: 0.65,
        AlertLevel.CRITICAL: 0.75,
    }

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        """
        Args:
            threshold: 관련 법안 판정 임계값
        """
        self.threshold = threshold

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """
        코사인 유사도 계산

        Args:
            vec_a: 벡터 A
            vec_b: 벡터 B

        Returns:
            -1.0 ~ 1.0 범위의 유사도
        """
        a = np.array(vec_a)
        b = np.array(vec_b)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))

    def get_alert_level(self, score: float) -> AlertLevel:
        """
        스코어에 따른 경고 수준 결정

        Args:
            score: 유사도 스코어

        Returns:
            AlertLevel enum
        """
        if score >= self.LEVEL_THRESHOLDS[AlertLevel.CRITICAL]:
            return AlertLevel.CRITICAL
        elif score >= self.LEVEL_THRESHOLDS[AlertLevel.HIGH]:
            return AlertLevel.HIGH
        elif score >= self.LEVEL_THRESHOLDS[AlertLevel.MEDIUM]:
            return AlertLevel.MEDIUM
        elif score >= self.LEVEL_THRESHOLDS[AlertLevel.LOW]:
            return AlertLevel.LOW
        else:
            return AlertLevel.NONE

    def score_bill(
        self,
        bill_vector: list[float],
        rr_vector: list[float],
    ) -> ScoreResult:
        """
        법안과 R&R 간 유사도 스코어링

        Args:
            bill_vector: 법안 임베딩 벡터
            rr_vector: 부처 R&R 임베딩 벡터

        Returns:
            ScoreResult 객체
        """
        score = self.cosine_similarity(bill_vector, rr_vector)
        alert_level = self.get_alert_level(score)
        is_relevant = score >= self.threshold

        return ScoreResult(
            score=score,
            alert_level=alert_level,
            is_relevant=is_relevant,
        )

    def score_batch(
        self,
        bill_vectors: list[list[float]],
        rr_vector: list[float],
    ) -> list[ScoreResult]:
        """
        여러 법안 배치 스코어링

        Args:
            bill_vectors: 법안 임베딩 벡터 리스트
            rr_vector: 부처 R&R 임베딩 벡터

        Returns:
            ScoreResult 리스트
        """
        return [
            self.score_bill(bill_vec, rr_vector)
            for bill_vec in bill_vectors
        ]

    def filter_relevant(
        self,
        bill_vectors: list[list[float]],
        rr_vector: list[float],
        bills: list[dict],
    ) -> list[tuple[dict, ScoreResult]]:
        """
        관련 법안만 필터링

        Args:
            bill_vectors: 법안 임베딩 벡터 리스트
            rr_vector: 부처 R&R 임베딩 벡터
            bills: 법안 딕셔너리 리스트

        Returns:
            (법안, ScoreResult) 튜플 리스트 (관련 법안만)
        """
        results = []
        for bill, bill_vec in zip(bills, bill_vectors):
            score_result = self.score_bill(bill_vec, rr_vector)
            if score_result.is_relevant:
                results.append((bill, score_result))

        # 스코어 내림차순 정렬
        results.sort(key=lambda x: x[1].score, reverse=True)
        return results


# 편의 함수
_default_scorer: Optional[Scorer] = None


def get_scorer(threshold: float = Scorer.DEFAULT_THRESHOLD) -> Scorer:
    """기본 Scorer 인스턴스 반환"""
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = Scorer(threshold=threshold)
    return _default_scorer


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """코사인 유사도 계산 (편의 함수)"""
    return Scorer.cosine_similarity(vec_a, vec_b)


if __name__ == "__main__":
    # 테스트
    scorer = Scorer()

    # 테스트 벡터
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]

    print(f"Same vector similarity: {scorer.cosine_similarity(vec_a, vec_b)}")
    print(f"Orthogonal similarity: {scorer.cosine_similarity(vec_a, vec_c)}")

    # 임계값 테스트
    test_scores = [0.40, 0.45, 0.55, 0.65, 0.75, 0.85]
    for score in test_scores:
        level = scorer.get_alert_level(score)
        print(f"Score {score:.2f} -> {level.value}")
