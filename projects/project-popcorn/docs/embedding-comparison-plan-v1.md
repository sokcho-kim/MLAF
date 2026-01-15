# 임베딩 모델 비교 테스트 계획 v1

> **버전:** v1
> **작성일시:** 2026-01-15 14:30
> **이전 버전:** -
> **변경사항:** 초기 작성
>
> 목적: Project Popcorn 벡터 검색에 최적인 임베딩 모델 선정

---

## 1. 개요

### 1.1 배경

- 입법 리스크 레이더 시스템은 **부처 R&R ↔ 법안** 간 유사도 계산이 핵심
- 한국어 법률 텍스트에 최적화된 임베딩 모델 선정 필요
- 비용, 성능, 속도를 종합적으로 평가하여 최적 모델 결정

### 1.2 목표

1. 5가지 임베딩 모델의 한국어 법안 데이터 성능 비교
2. Dense / Sparse / Hybrid 방식 효과 검증
3. 비용 대비 성능 최적 모델 선정

---

## 2. 비교 대상 모델

| # | 모델 | 언어 | 유형 | 차원 | Provider | 비용 |
|---|------|------|------|------|----------|------|
| 1 | **Solar Embedding** | 한국어 특화 | Dense | 4096 | Upstage API | $0.00015/1K tokens |
| 2 | **BGE-M3** | 다국어 | Dense + Sparse | 1024 | fastembed (로컬) | 무료 |
| 3 | **multilingual-e5-large** | 다국어 | Dense | 1024 | fastembed (로컬) | 무료 |
| 4 | **text-embedding-3-small** | 다국어 | Dense | 1536 | OpenAI API | $0.00002/1K tokens |
| 5 | **KoSimCSE-roberta** | 한국어 특화 | Dense | 768 | HuggingFace (로컬) | 무료 |

### 2.1 모델 상세

#### Solar Embedding (Upstage)
- 한국어 특화 임베딩 모델
- 4096 차원 고밀도 벡터
- API 기반, 안정적인 서비스

#### BGE-M3 (BAAI)
- 다국어 지원 (100+ 언어)
- Dense + Sparse 하이브리드 검색 지원
- fastembed로 로컬 ONNX 런타임 실행

#### multilingual-e5-large (Microsoft)
- 다국어 지원
- MTEB 벤치마크 상위권
- fastembed 로컬 실행 가능

#### text-embedding-3-small (OpenAI)
- 범용 다국어 모델
- 가장 저렴한 API 비용
- 1536 차원

#### KoSimCSE-roberta (BM-K)
- 한국어 문장 유사도 특화
- SimCSE 기반 contrastive learning
- HuggingFace에서 로컬 실행

---

## 3. 테스트 데이터

### 3.1 부처 R&R 데이터

| 항목 | 내용 |
|------|------|
| 파일 | `data/ministry_rr.json` |
| 건수 | 21개 (18개 행정각부 + 3개 국무총리소속처) |
| 출처 | 정부조직법 (2025.10.1 개정) |

### 3.2 법안 데이터

| 항목 | 내용 |
|------|------|
| 출처 | 열린국회정보 API (TVBPMBILL11) |
| 대상 | 22대 국회 법안 |
| 샘플 크기 | 100건 (소관위별 균등 샘플링) |
| 필드 | 의안명, 제안이유, 주요내용 |

### 3.3 샘플링 전략

```
소관위별 균등 샘플링 (10개 소관위 × 10건)
- 산업통상자원중소벤처기업위원회
- 기획재정위원회
- 환경노동위원회
- 국토교통위원회
- 보건복지위원회
- 교육위원회
- 과학기술정보방송통신위원회
- 농림축산식품해양수산위원회
- 법제사법위원회
- 행정안전위원회
```

---

## 4. 평가 지표

### 4.1 정량 지표

| 지표 | 설명 | 측정 방법 |
|------|------|----------|
| **소관위 일치도** | 같은 소관위 법안끼리 유사도가 높은지 | Precision@K, MRR |
| **Cross-Domain 감지율** | 타 소관위 법안 중 R&R 유사도 높은 케이스 | Recall, F1-Score |
| **클러스터링 품질** | 소관위별 군집화 품질 | Silhouette Score, NMI |
| **처리 속도** | 100건 임베딩 소요 시간 | 초 단위 |
| **비용** | 테스트 데이터 임베딩 비용 | USD |

### 4.2 정성 지표

| 지표 | 설명 |
|------|------|
| **유사 법안 품질** | Top-K 유사 법안이 실제로 관련 있는지 |
| **이상 탐지 품질** | Cross-Domain 감지 결과가 실제 리스크인지 |

---

## 5. 테스트 시나리오

### 5.1 Scenario 1: 소관위 일치도 테스트

```python
# 동일 소관위 법안 간 유사도 vs 타 소관위 법안 간 유사도
for bill in test_bills:
    same_committee_sim = avg_similarity(bill, same_committee_bills)
    diff_committee_sim = avg_similarity(bill, diff_committee_bills)

    # same_committee_sim > diff_committee_sim 이어야 함
```

**기대 결과:** 동일 소관위 법안 간 유사도가 타 소관위보다 높아야 함

### 5.2 Scenario 2: Cross-Domain 리스크 감지

```python
# 부처 R&R과 타 소관위 법안 간 유사도
for ministry in ministries:
    for bill in other_committee_bills:
        sim = similarity(ministry.rr_vector, bill.vector)
        if sim > THRESHOLD:
            flag_as_risk(bill, ministry)
```

**기대 결과:** 실제 업무 관련성이 있는 법안이 높은 유사도로 감지되어야 함

### 5.3 Scenario 3: 검색 정확도 테스트

```python
# 부처 R&R로 관련 법안 검색
for ministry in ministries:
    results = search_similar_bills(ministry.rr_vector, top_k=10)
    precision = calculate_precision(results, ground_truth)
```

**평가:** Precision@5, Precision@10, MRR

---

## 6. 실험 설계

### 6.1 실험 환경

| 항목 | 내용 |
|------|------|
| Python | 3.11+ |
| GPU | 선택 (로컬 모델 가속용) |
| 벡터 DB | Qdrant (로컬 Docker) |

### 6.2 필요 패키지

```
fastembed>=0.2.0      # BGE-M3, multilingual-e5
openai>=1.0.0         # text-embedding-3-small
sentence-transformers # KoSimCSE
httpx                 # Upstage API
qdrant-client         # 벡터 저장/검색
scikit-learn          # 평가 지표 계산
```

### 6.3 실험 절차

```
1. 테스트 데이터 준비
   ├── 부처 R&R 21건 로드
   └── 법안 100건 샘플링 및 저장

2. 모델별 임베딩 생성
   ├── Solar Embedding (API)
   ├── BGE-M3 (fastembed)
   ├── multilingual-e5-large (fastembed)
   ├── text-embedding-3-small (API)
   └── KoSimCSE-roberta (HuggingFace)

3. 평가 지표 계산
   ├── 소관위 일치도
   ├── Cross-Domain 감지율
   ├── 클러스터링 품질
   └── 처리 속도 / 비용

4. 결과 분석 및 시각화
   ├── 모델별 성능 비교 차트
   ├── t-SNE 군집화 시각화
   └── 비용 대비 성능 분석

5. 최종 모델 선정
```

---

## 7. 산출물

| 산출물 | 파일명 |
|--------|--------|
| 테스트 스크립트 | `research/embedding_comparison.py` |
| 결과 데이터 | `research/results/embedding_comparison.json` |
| 시각화 | `research/results/embedding_viz.png` |
| 최종 보고서 | `docs/embedding-comparison-report.md` |

---

## 8. 일정

| 단계 | 작업 |
|------|------|
| Step 1 | 테스트 데이터 준비 (법안 100건 샘플링) |
| Step 2 | 5개 모델 임베딩 생성 |
| Step 3 | 평가 지표 계산 |
| Step 4 | 결과 분석 및 보고서 작성 |

---

## 9. 참고자료

- [Upstage Solar Embedding](https://developers.upstage.ai/docs/apis/embeddings)
- [BGE-M3 Paper](https://arxiv.org/abs/2402.03216)
- [fastembed GitHub](https://github.com/qdrant/fastembed)
- [KoSimCSE](https://huggingface.co/BM-K/KoSimCSE-roberta)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
