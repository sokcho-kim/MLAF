# 프로덕션 파이프라인 v2 적용 계획

> **버전**: v1.0
> **작성일**: 2026-01-16
> **상태**: 승인 대기

---

## 개요

**목표**: 제목+Summary 임베딩 전략을 프로덕션 파이프라인에 적용하여 Cross-Domain 법안 감지 자동화

**배경**: 임베딩 v2 테스트 결과, 제목+Summary 전략이 제목만 사용하는 것보다 평균 29.4% 높은 Cross-Domain 감지율을 보임 (특히 Hard 케이스에서 +30.6%)

---

## API 검증 (2026-01-16)

```
OpenAI API Test: SUCCESS
- Model: text-embedding-3-small
- Embedding dim: 1536
- Key prefix: sk-proj-Ph...
```

---

## 1. 현재 상태

### 보유 자산
| 항목 | 파일 | 상태 |
|------|------|------|
| 법안 데이터 | `bills_merged.json` | 1,021건 (summary 99.6%) |
| 산업부 R&R | `ministry_rr_augmented.json` | 822자 (증강 버전) |
| 임베딩 테스트 | `embedding_comparison.py` | 완료 |
| 레이더 모듈 | `src/radar.py` | 스켈레톤 (TODO) |

### 검증된 파라미터
- **임베딩 모델**: OpenAI `text-embedding-3-small` (권장)
- **임베딩 전략**: 제목 + Summary (v2)
- **임계값**: 0.45 이상 → 관련 법안
- **Hard 케이스 향상률**: +30.6%

---

## 2. 파이프라인 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline v2 Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [1. Ingest]         [2. Embed]          [3. Score]             │
│  ┌──────────┐       ┌──────────┐        ┌──────────┐            │
│  │ 국회 API │──────▶│ OpenAI   │───────▶│ Cosine   │            │
│  │ 신규법안 │       │ Embedding│        │ Similarity│            │
│  └──────────┘       └──────────┘        └──────────┘            │
│       │                  │                   │                   │
│       ▼                  ▼                   ▼                   │
│  ┌──────────┐       ┌──────────┐        ┌──────────┐            │
│  │ title +  │       │ 1536-dim │        │ score >= │            │
│  │ summary  │       │ vector   │        │ 0.45?    │            │
│  └──────────┘       └──────────┘        └──────────┘            │
│                                              │                   │
│                          ┌───────────────────┴───────────────┐  │
│                          ▼                                   ▼  │
│                    [4. Alert]                         [5. Skip] │
│                    ┌──────────┐                               │  │
│                    │ RiskAlert│                               │  │
│                    │ 생성     │                               │  │
│                    └──────────┘                               │  │
│                          │                                      │
│                          ▼                                      │
│                    [6. Report]                                  │
│                    ┌──────────┐                                 │
│                    │ 일일/주간 │                                 │
│                    │ 리포트    │                                 │
│                    └──────────┘                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 구현 계획

### Phase 1: 핵심 모듈 구현 (Day 1)

#### 3.1 `src/embedder.py` - 임베딩 모듈
```python
# 주요 기능
- embed_text(text: str) -> list[float]
- embed_bill(bill: dict) -> list[float]  # title + summary
- embed_batch(bills: list[dict]) -> list[list[float]]
- cache 지원 (중복 임베딩 방지)
```

#### 3.2 `src/scorer.py` - 유사도 계산 모듈
```python
# 주요 기능
- cosine_similarity(vec_a, vec_b) -> float
- score_bill(bill_vec, rr_vec) -> float
- score_batch(bill_vecs, rr_vec) -> list[float]
- threshold 적용 (default: 0.45)
```

#### 3.3 `src/radar.py` 업데이트 - 레이더 모듈
```python
# 주요 기능
- detect_cross_domain_risk() 구현
- scan_new_bills() 구현
- create_risk_alert() 구현
- alert_level 결정 로직:
  - 0.45-0.55: LOW
  - 0.55-0.65: MEDIUM
  - 0.65-0.75: HIGH
  - 0.75+: CRITICAL
```

### Phase 2: 파이프라인 통합 (Day 2)

#### 3.4 `src/pipeline.py` - 메인 파이프라인
```python
class BillRadarPipeline:
    def __init__(self, ministry: str = "산업통상자원부"):
        self.embedder = Embedder()
        self.scorer = Scorer(threshold=0.45)
        self.ministry_rr = load_ministry_rr(ministry)
        self.rr_vector = self.embedder.embed_text(self.ministry_rr)

    def run_daily(self):
        """일일 스캔"""
        new_bills = fetch_new_bills(since=yesterday)
        alerts = []
        for bill in new_bills:
            score = self.score_bill(bill)
            if score >= self.threshold:
                alert = self.create_alert(bill, score)
                alerts.append(alert)
        return alerts

    def run_full_scan(self):
        """전체 스캔 (1,021건)"""
        ...
```

#### 3.5 `src/reporter.py` - 리포트 모듈
```python
# 주요 기능
- generate_daily_report(alerts: list[RiskAlert])
- generate_weekly_summary()
- export_to_markdown()
- export_to_json()
```

### Phase 3: 자동화 (Day 3)

#### 3.6 스케줄러 설정
```python
# 옵션 1: Python schedule
schedule.every().day.at("09:00").do(pipeline.run_daily)

# 옵션 2: GitHub Actions (권장)
# .github/workflows/daily-scan.yml
```

#### 3.7 알림 시스템
- Slack 웹훅 (선택)
- 이메일 알림 (선택)
- 로컬 로그

---

## 4. 파일 구조 (예정)

```
src/
├── __init__.py
├── embedder.py      # [NEW] 임베딩 모듈
├── scorer.py        # [NEW] 유사도 계산 모듈
├── radar.py         # [UPDATE] 레이더 모듈
├── pipeline.py      # [NEW] 메인 파이프라인
├── reporter.py      # [NEW] 리포트 모듈
├── ingest.py        # 기존 유지
└── ...
```

---

## 5. 의존성

```
# requirements.txt 추가 필요
openai>=1.0.0        # 임베딩 API
numpy>=1.24.0        # 벡터 연산
schedule>=1.2.0      # 스케줄링 (선택)
```

---

## 6. 테스트 계획

### 6.1 단위 테스트
- [ ] `test_embedder.py` - 임베딩 정상 동작
- [ ] `test_scorer.py` - 유사도 계산 정확도
- [ ] `test_radar.py` - 알림 레벨 결정 로직

### 6.2 통합 테스트
- [ ] Golden Set 5건 감지 테스트
- [ ] 전체 1,021건 스캔 테스트
- [ ] 임계값 경계 테스트 (0.44, 0.45, 0.46)

### 6.3 성능 테스트
- [ ] 1,021건 처리 시간 측정
- [ ] API 비용 추정

---

## 7. 예상 비용

| 항목 | 계산 | 비용 |
|------|------|------|
| 초기 전체 스캔 (1,021건) | 1,021 × $0.00002/1K tokens × ~500 tokens | ~$0.01 |
| 일일 스캔 (평균 10건/일) | 10 × 30일 × $0.00002 × 500 | ~$0.003/월 |
| R&R 임베딩 (1회) | 1 × $0.00002 × 500 | ~$0.00001 |

**총 예상 비용: ~$0.02/월** (매우 저렴)

---

## 8. 마일스톤

| Phase | 작업 | 예상 |
|-------|------|------|
| **Phase 1** | embedder, scorer, radar 구현 | Day 1 |
| **Phase 2** | pipeline, reporter 통합 | Day 2 |
| **Phase 3** | 자동화, 알림 | Day 3 |
| **Phase 4** | 다른 부처 확장 | Day 4+ |

---

## 9. 리스크 및 대응

| 리스크 | 대응 |
|--------|------|
| API 장애 | 로컬 캐시, 재시도 로직 |
| 임계값 튜닝 필요 | A/B 테스트, 피드백 루프 |
| 새 법안 summary 미제공 | 제목만으로 fallback |

---

## 10. 다음 액션

1. **즉시**: 계획 승인 후 Phase 1 착수
2. **Phase 1 완료 후**: 전체 1,021건 스캔 실행
3. **결과 검토 후**: 임계값 조정 여부 결정
