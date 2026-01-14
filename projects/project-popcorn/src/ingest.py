"""
데이터 벡터화 및 Qdrant 적재 모듈
"""
from qdrant_client import QdrantClient
from dotenv import load_dotenv
import os

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))


def get_qdrant_client() -> QdrantClient:
    """Qdrant 클라이언트 반환"""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ingest_documents(documents: list[dict], collection_name: str = "na_laws"):
    """문서를 벡터화하여 Qdrant에 적재"""
    # TODO: Upstage Solar Embedding 연동
    # TODO: 벡터화 및 적재 로직 구현
    pass


if __name__ == "__main__":
    client = get_qdrant_client()
    print(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
