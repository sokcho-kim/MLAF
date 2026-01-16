"""
임베딩 모듈

OpenAI text-embedding-3-small을 사용하여 텍스트를 벡터로 변환합니다.
v2 전략: 법안 제목 + 제안이유(summary)를 함께 임베딩
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class Embedder:
    """텍스트 임베딩 클래스"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        cache_dir: Optional[Path] = None,
    ):
        """
        Args:
            model: OpenAI 임베딩 모델명
            cache_dir: 캐시 저장 디렉토리 (None이면 캐시 비활성화)
        """
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.cache_dir = cache_dir
        self._cache: dict[str, list[float]] = {}

        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache()

    def _get_cache_key(self, text: str) -> str:
        """텍스트의 캐시 키 생성"""
        return hashlib.md5(f"{self.model}:{text}".encode()).hexdigest()

    def _load_cache(self) -> None:
        """캐시 파일 로드"""
        if not self.cache_dir:
            return

        cache_file = self.cache_dir / "embedding_cache.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                self._cache = json.load(f)

    def _save_cache(self) -> None:
        """캐시 파일 저장"""
        if not self.cache_dir:
            return

        cache_file = self.cache_dir / "embedding_cache.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f)

    def embed_text(self, text: str, use_cache: bool = True) -> list[float]:
        """
        텍스트를 임베딩 벡터로 변환

        Args:
            text: 임베딩할 텍스트
            use_cache: 캐시 사용 여부

        Returns:
            1536차원 임베딩 벡터
        """
        # 캐시 확인
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                return self._cache[cache_key]

        # API 호출
        truncated = text[:8000]  # 토큰 제한 대응
        response = self.client.embeddings.create(
            model=self.model,
            input=truncated,
        )
        embedding = response.data[0].embedding

        # 캐시 저장
        if use_cache:
            self._cache[cache_key] = embedding
            self._save_cache()

        return embedding

    def embed_bill(self, bill: dict) -> list[float]:
        """
        법안을 임베딩 (v2 전략: 제목 + summary)

        Args:
            bill: 법안 딕셔너리 (bill_name, summary 필드 필요)

        Returns:
            1536차원 임베딩 벡터
        """
        title = bill.get("bill_name", "")
        summary = bill.get("summary", "")

        # v2 전략: 제목 + summary 결합
        if summary:
            text = f"{title}\n\n{summary}"
        else:
            text = title  # fallback: 제목만

        return self.embed_text(text)

    def embed_batch(
        self,
        bills: list[dict],
        show_progress: bool = True,
    ) -> list[list[float]]:
        """
        여러 법안을 배치로 임베딩

        Args:
            bills: 법안 딕셔너리 리스트
            show_progress: 진행 상황 출력 여부

        Returns:
            임베딩 벡터 리스트
        """
        embeddings = []
        total = len(bills)

        for i, bill in enumerate(bills):
            emb = self.embed_bill(bill)
            embeddings.append(emb)

            if show_progress and (i + 1) % 10 == 0:
                print(f"  Embedding: {i + 1}/{total}")

        return embeddings


# 편의 함수
_default_embedder: Optional[Embedder] = None


def get_embedder(cache_dir: Optional[Path] = None) -> Embedder:
    """기본 Embedder 인스턴스 반환 (싱글톤)"""
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = Embedder(cache_dir=cache_dir)
    return _default_embedder


def embed_text(text: str) -> list[float]:
    """텍스트 임베딩 (편의 함수)"""
    return get_embedder().embed_text(text)


def embed_bill(bill: dict) -> list[float]:
    """법안 임베딩 (편의 함수)"""
    return get_embedder().embed_bill(bill)


if __name__ == "__main__":
    # 테스트
    embedder = Embedder()

    test_text = "산업통상자원부 관련 법안 테스트"
    emb = embedder.embed_text(test_text)
    print(f"Text: {test_text}")
    print(f"Embedding dim: {len(emb)}")
    print(f"First 5 values: {emb[:5]}")
