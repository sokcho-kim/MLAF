# 임베딩 모델 비교 테스트 계획 v2

> **버전:** v2
> **작성일시:** 2026-01-15 15:03
> **이전 버전:** v1
> **변경사항:**
> - R&R 데이터 증강 전략 추가 (소관 법령 + 하부 조직명)
> - 비교 모델 5개 → 3개 축소 (Long Context 모델만)
> - Golden Set 평가 방식 추가 (Recall@Top10)
> - KoSimCSE, multilingual-e5 제외 (512토큰 제한)

---

## 1. 개요

### 1.1 배경

- 입법 리스크 레이더 시스템은 **부처 R&R ↔ 법안** 간 유사도 계산이 핵심
- 한국어 법률 텍스트에 최적화된 임베딩 모델 선정 필요
- 비용, 성능, 속도를 종합적으로 평가하여 최적 모델 결정

### 1.2 목표

1. 3가지 Long Context 임베딩 모델의 한국어 법안 데이터 성능 비교
2. Dense / Sparse / Hybrid 방식 효과 검증
3. 비용 대비 성능 최적 모델 선정

---

## 2. 핵심 이슈: 추상화 레벨 불일치

### 2.1 문제 정의

| 데이터 | 특성 | 예시 |
|--------|------|------|
| **부처 R&R (Query)** | 추상적/포괄적 | "산업통상자원부는 상업, 무역, 공업... 사무를 관장한다." |
| **법안 (Document)** | 구체적/세부적 | "제3조(설비 기준) 반도체 제조 시설의..." |

임베딩 모델은 추상화 레벨이 다를 때 유사도를 낮게 평가하는 경향이 있음.

### 2.2 해결 전략: R&R 데이터 증강

#### 증강 소스 ①: 소관 법령 목록

| 부처 | 소관 법령 예시 |
|------|---------------|
| 산업통상자원부 | 반도체 집적회로의 배치설계에 관한 법률, 산업집적활성화 및 공장설립에 관한 법률, 송유관 안전관리법 |

**적용:** R&R 텍스트 뒤에 소관 법률명 리스트 추가

#### 증강 소스 ②: 하부 조직명 (실/국/과)

| 부처 | 하부 조직 예시 |
|------|---------------|
| 산업통상자원부 | 반도체디스플레이과, 원전산업정책과, 재생에너지보급과, 섬유탄소나노과 |

**적용:** 직제 규정(대통령령)에서 국/과 이름 추출하여 R&R에 추가

#### 증강 결과 예시

```
[Before]
산업통상자원부는 상업, 무역, 공업, 통상, 통상교섭... 사무를 관장한다.

[After]
산업통상자원부는 상업, 무역, 공업, 통상, 통상교섭... 사무를 관장한다.
[소관법령] 반도체법, 공장설립법, 전력산업구조개편법, 송유관안전관리법...
[조직] 반도체디스플레이과, 원전산업정책과, 재생에너지보급과, 섬유탄소나노과...
```

---

## 3. 비교 대상 모델 (3개)

### 3.1 선정 기준

- **Long Context 지원** (4096+ 토큰): 법안 텍스트 truncation 방지
- **공정한 비교 조건**: 입력 길이 제한으로 인한 성능 왜곡 배제

### 3.2 제외 모델

| 모델 | 제외 사유 |
|------|----------|
| ~~KoSimCSE-roberta~~ | 512 토큰 제한 |
| ~~multilingual-e5-large~~ | 512 토큰 제한 |

### 3.3 최종 비교 대상

| # | 모델 | Context | 차원 | 유형 | Provider | 비용 |
|---|------|---------|------|------|----------|------|
| 1 | **Solar Embedding** | 4K | 4096 | Dense | Upstage API | $0.00015/1K tokens |
| 2 | **text-embedding-3-small** | 8K | 1536 | Dense | OpenAI API | $0.00002/1K tokens |
| 3 | **BGE-M3** | 8K | 1024 | Dense + Sparse | fastembed (로컬) | 무료 |

---

## 4. 테스트 데이터

### 4.1 부처 R&R 데이터 (증강 후)

| 항목 | 내용 |
|------|------|
| 원본 파일 | `data/ministry_rr.json` |
| 증강 파일 | `data/ministry_rr_augmented.json` |
| 건수 | 21개 (18개 행정각부 + 3개 국무총리소속처) |
| 증강 내용 | 소관 법령 목록 + 하부 조직명 |

### 4.2 법안 데이터

| 항목 | 내용 |
|------|------|
| 출처 | 열린국회정보 API (TVBPMBILL11) |
| 대상 | 22대 국회 법안 |
| 샘플 크기 | 100건 (소관위별 균등 샘플링) |
| 필드 | 의안명, 제안이유, 주요내용 |

### 4.3 Golden Set (수동 마킹)

| 항목 | 내용 |
|------|------|
| 목적 | Cross-Domain 감지 평가용 Ground Truth |
| 방법 | 100건 중 "산업부가 반드시 검토해야 할" 법안 5개 수동 선정 |
| 예시 | 환경노동위 탄소중립 법안, 과방위 반도체 관련 법안 등 |

---

## 5. 평가 지표

### 5.1 정량 지표

| 지표 | 설명 | 측정 방법 |
|------|------|----------|
| **Recall@Top10** | Golden Set 5개가 상위 10개에 포함되는 비율 | (Golden Set ∩ Top10) / 5 |
| **소관위 일치도** | 같은 소관위 법안끼리 유사도가 높은지 | Precision@K, MRR |
| **클러스터링 품질** | 소관위별 군집화 품질 | Silhouette Score |
| **처리 속도** | 100건 임베딩 소요 시간 | 초 단위 |
| **비용** | 테스트 데이터 임베딩 비용 | USD |

### 5.2 핵심 평가: Golden Set Recall

```python
# 평가 로직
ministry_rr = "산업통상자원부 R&R (증강)"
golden_set = [법안A, 법안B, 법안C, 법안D, 법안E]  # 수동 마킹

results = search_similar_bills(ministry_rr, top_k=10)
recall = len(set(results) & set(golden_set)) / len(golden_set)
```

---

## 6. 테스트 시나리오

### 6.1 Scenario 1: Golden Set 감지 (핵심)

```python
# 산업부 R&R로 검색 → Golden Set 5개가 Top10에 들어오는지
for model in [solar, openai, bge_m3]:
    ministry_vector = model.embed(industry_ministry_rr_augmented)
    results = search_top_k(ministry_vector, all_bills, k=10)
    recall = calculate_recall(results, golden_set)
```

**평가:** Recall@Top10

### 6.2 Scenario 2: 소관위 일치도

```python
# 동일 소관위 법안 간 유사도 vs 타 소관위 법안 간 유사도
for bill in test_bills:
    same_committee_sim = avg_similarity(bill, same_committee_bills)
    diff_committee_sim = avg_similarity(bill, diff_committee_bills)
```

**평가:** 동일 소관위 유사도 > 타 소관위 유사도

### 6.3 Scenario 3: Dense vs Hybrid (BGE-M3 전용)

```python
# BGE-M3의 Dense-only vs Dense+Sparse 하이브리드 비교
dense_results = search_dense(query, bills)
hybrid_results = search_hybrid(query, bills, alpha=0.7)
```

**평가:** 하이브리드가 Golden Set Recall 향상시키는지

---

## 7. 실험 설계

### 7.1 실험 환경

| 항목 | 내용 |
|------|------|
| Python | 3.11+ |
| 벡터 DB | Qdrant (로컬 Docker) |
| GPU | 선택 (BGE-M3 가속용) |

### 7.2 필요 패키지

```
fastembed>=0.2.0      # BGE-M3
openai>=1.0.0         # text-embedding-3-small
httpx                 # Upstage Solar API
qdrant-client         # 벡터 저장/검색
scikit-learn          # 평가 지표 계산
```

### 7.3 실험 절차

```
1. 데이터 준비
   ├── R&R 데이터 증강 (소관 법령 + 조직명)
   ├── 법안 100건 샘플링
   └── Golden Set 5개 수동 마킹

2. 모델별 임베딩 생성
   ├── Solar Embedding (API)
   ├── text-embedding-3-small (API)
   └── BGE-M3 (fastembed, Dense + Sparse)

3. 평가 지표 계산
   ├── Golden Set Recall@Top10 (핵심)
   ├── 소관위 일치도
   ├── 클러스터링 품질
   └── 처리 속도 / 비용

4. 결과 분석 및 시각화
   ├── 모델별 성능 비교 차트
   ├── t-SNE 군집화 시각화
   └── 비용 대비 성능 분석

5. 최종 모델 선정
```

---

## 8. 산출물

| 산출물 | 파일명 |
|--------|--------|
| R&R 증강 데이터 | `data/ministry_rr_augmented.json` |
| Golden Set | `data/golden_set.json` |
| 테스트 스크립트 | `research/embedding_comparison.py` |
| 결과 데이터 | `research/results/embedding_comparison.json` |
| 시각화 | `research/results/embedding_viz.png` |
| 최종 보고서 | `docs/embedding-comparison-report.md` |

---

## 9. 작업 순서

| Step | 작업 | 산출물 |
|------|------|--------|
| 1 | R&R 데이터 증강 (소관 법령 + 조직명 수집) | `ministry_rr_augmented.json` |
| 2 | 법안 100건 샘플링 | `test_bills.json` |
| 3 | Golden Set 5개 수동 마킹 | `golden_set.json` |
| 4 | 3개 모델 임베딩 생성 | 벡터 데이터 |
| 5 | 평가 지표 계산 | 성능 결과 |
| 6 | 결과 분석 및 보고서 작성 | 최종 보고서 |

---

## 10. 참고자료

- [Upstage Solar Embedding](https://developers.upstage.ai/docs/apis/embeddings)
- [BGE-M3 Paper](https://arxiv.org/abs/2402.03216)
- [fastembed GitHub](https://github.com/qdrant/fastembed)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
