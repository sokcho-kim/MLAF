"""
BM25 vs Vector 검색 성능 비교 실험

키워드 기반(BM25)과 의미 기반(Vector) 검색의
정확도 및 재현율 비교
"""
from dataclasses import dataclass


@dataclass
class SearchResult:
    """검색 결과"""
    doc_id: str
    score: float
    method: str  # "bm25" or "vector"


def bm25_search(query: str, documents: list[str]) -> list[SearchResult]:
    """BM25 키워드 검색"""
    # TODO: BM25 구현
    pass


def vector_search(query: str, documents: list[str]) -> list[SearchResult]:
    """벡터 유사도 검색"""
    # TODO: Qdrant 벡터 검색 연동
    pass


def hybrid_search(query: str, documents: list[str], alpha: float = 0.5) -> list[SearchResult]:
    """
    하이브리드 검색 (BM25 + Vector)

    Args:
        query: 검색 쿼리
        documents: 문서 리스트
        alpha: BM25 가중치 (1-alpha = Vector 가중치)
    """
    # TODO: 하이브리드 검색 구현
    pass


def evaluate_search_methods():
    """검색 방법 성능 평가"""
    # TODO: 테스트 쿼리셋 구축
    # TODO: Precision, Recall, F1 계산
    pass


if __name__ == "__main__":
    evaluate_search_methods()
