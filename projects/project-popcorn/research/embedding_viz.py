"""
t-SNE 유사도 시각화 실험

국회법 조문 간 의미적 거리를 시각화하여
임베딩 품질 검증
"""
import numpy as np
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt


def visualize_embeddings(embeddings: np.ndarray, labels: list[str]):
    """
    임베딩 벡터를 2D로 시각화

    Args:
        embeddings: (N, D) 임베딩 벡터 배열
        labels: 각 벡터의 레이블
    """
    # t-SNE 차원 축소
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings)-1))
    reduced = tsne.fit_transform(embeddings)

    # 시각화
    plt.figure(figsize=(12, 8))
    plt.scatter(reduced[:, 0], reduced[:, 1], alpha=0.7)

    for i, label in enumerate(labels):
        plt.annotate(label[:20], (reduced[i, 0], reduced[i, 1]), fontsize=8)

    plt.title("국회법 조문 임베딩 시각화 (t-SNE)")
    plt.xlabel("Dimension 1")
    plt.ylabel("Dimension 2")
    plt.tight_layout()
    plt.savefig("embedding_viz.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    # 테스트용 더미 데이터
    dummy_embeddings = np.random.randn(10, 768)
    dummy_labels = [f"조문 {i+1}" for i in range(10)]
    visualize_embeddings(dummy_embeddings, dummy_labels)
