# Project Popcorn 구현 계획

> 작성일: 2026-01-14
> 기반 문서: `docs/plan/PRD_260114_2.md`

---

## 1. 개요

**목표:** 타 상임위 법안 내 '보이지 않는 규제'를 선제 감지하는 입법 리스크 레이더 MVP 구축

**핵심 전략:** Dual-Track 데이터 수집
- Track 1 (Base): 공공데이터포털 → 과거 데이터 학습용
- Track 2 (Radar): 열린국회정보 API → 실시간 감지용

---

## 2. 구현 Phase

### Phase 1: 데이터 수집 인프라

| 작업 | 세부 내용 | 산출물 |
|------|----------|--------|
| 1-1. Track 1 수집기 | 공공데이터포털 국회의안목록정보 API 연동 | `src/ingest_base.py` |
| 1-2. Track 2 수집기 | 열린국회정보 TVBPMBILL11 API 연동 | `src/ingest_radar.py` |
| 1-3. Fallback 크롤러 | 의안정보시스템 웹 크롤링 (API 장애 대비) | `src/fallback_crawler.py` |
| 1-4. 데이터 정규화 | 두 소스 통합 스키마 설계 | `data/schema.json` |

**API 정보:**
```
[Track 1] 공공데이터포털
- 엔드포인트: data.go.kr/국회의안목록정보
- 수집 범위: 20~22대 국회 (약 30,000건)
- 주요 필드: 의안ID, 의안명, 제안자, 소관위, 의결결과

[Track 2] 열린국회정보
- 엔드포인트: open.assembly.go.kr/TVBPMBILL11
- 수집 주기: 1시간 폴링
- 주요 필드: 의안번호, 제안이유, 주요내용, 소관위
```

---

### Phase 2: Vector DB 구축

| 작업 | 세부 내용 | 산출물 |
|------|----------|--------|
| 2-1. Qdrant 세팅 | Docker Compose로 로컬 구동 | `docker-compose.yml` ✅ |
| 2-2. 임베딩 파이프라인 | Solar Embedding으로 벡터화 | `src/embedding.py` |
| 2-3. 컬렉션 설계 | 법안/부처R&R 컬렉션 스키마 | Qdrant collections |

**컬렉션 스키마 (예정):**
```python
# bills 컬렉션
{
    "id": "의안ID",
    "vector": [768 dims],  # Solar Embedding
    "payload": {
        "title": "의안명",
        "proposer": "제안자",
        "committee": "소관위",
        "summary": "제안이유",
        "status": "처리상태",
        "date": "제안일자"
    }
}

# ministry_rr 컬렉션
{
    "id": "부처코드",
    "vector": [768 dims],
    "payload": {
        "name": "부처명",
        "rr_text": "업무분장 원문"
    }
}
```

---

### Phase 3: 리스크 감지 엔진

| 작업 | 세부 내용 | 산출물 |
|------|----------|--------|
| 3-1. 부처 R&R 벡터 | 산업부 등 부처별 업무분장 벡터화 | `data/ministry_rr.json` |
| 3-2. Radar 로직 | Cross-Domain 유사도 계산 | `src/radar.py` |
| 3-3. 알림 시스템 | 임계값 초과 시 경고 발령 | Alert mechanism |

**감지 로직:**
```python
# 리스크 판정 조건
if (bill.committee != ministry.committee  # 소관위 불일치
    and dot_product(bill.vector, ministry.vector) > 0.82  # 유사도 임계값
    and contains_regulation_keywords(bill.text)):  # 규제 키워드

    trigger_alert(bill, ministry)
```

---

### Phase 4: 보고서 생성

| 작업 | 세부 내용 | 산출물 |
|------|----------|--------|
| 4-1. LangGraph 워크플로우 | 감지→검색→생성 병렬 처리 | `src/agent.py` |
| 4-2. HWP 템플릿 | 공문 양식 누름틀 설계 | `templates/report.hwp` |
| 4-3. Slot-Filling | 분석 결과 자동 주입 | `src/report.py` |

**LangGraph 워크플로우:**
```
[START]
   │
   ▼
┌──────────────┐
│ detect_node  │  ← 리스크 감지
└──────────────┘
   │
   ▼
┌──────────────────────────────────┐
│         (parallel)               │
│  ┌─────────┐  ┌─────────────┐   │
│  │ search  │  │ analyze     │   │
│  │ _node   │  │ _node       │   │
│  └─────────┘  └─────────────┘   │
└──────────────────────────────────┘
   │
   ▼
┌──────────────┐
│ generate     │  ← HWP 생성
│ _report_node │
└──────────────┘
   │
   ▼
[END]
```

---

### Phase 5: 연구 과제

| 작업 | 세부 내용 | 산출물 |
|------|----------|--------|
| 5-1. Tokenizer 비교 | tiktoken vs Solar tokenizer | `research/tokenizer_lab.py` |
| 5-2. Embedding 시각화 | t-SNE 군집화 분석 | `research/embedding_viz.py` |

---

## 3. 자원 산정

### 인프라 비용 (월간)

| 항목 | 비용 | 비고 |
|------|------|------|
| AWS Lightsail | $20 | 4GB RAM, 2 vCPU |
| Qdrant | $0 | Self-hosted (Docker) |
| **소계** | **$20** | |

### API 비용 (월간)

| 항목 | 단가 | 예상 사용량 | 비용 |
|------|------|------------|------|
| Solar Pro LLM | $0.003/1K tokens | ~1M tokens | ~$30 |
| Solar Embedding | $0.00015/1K tokens | ~5M tokens | ~$7.5 |
| 공공데이터포털 | 무료 | 일 1,000건 | $0 |
| 열린국회정보 | 무료 | 일 1,000건 | $0 |
| **소계** | | | **~$40** |

### 초기 구축 비용 (일회성)

| 항목 | 예상 규모 | 비용 |
|------|----------|------|
| 과거 법안 임베딩 (20-25대) | ~30,000건 | ~$15 |
| 검토보고서 텍스트 | ~50MB | ~$10 |
| 부처 R&R 문서 | ~20개 부처 | ~$1 |
| **소계** | | **~$26** |

### 총 예산

| 구분 | 비용 |
|------|------|
| 월간 운영비 | ~$60 |
| 초기 구축비 | ~$26 (일회성) |
| 예비비 | ~$24 |
| **합계** | **~$110/월 (15만원 예산 내)** ✅ |

---

## 4. 리스크 관리

| 리스크 | 확률 | 영향 | 대응 방안 |
|--------|------|------|----------|
| 열린국회 API 불안정 | 중 | 높음 | Fallback 크롤러 구현 |
| Solar 토큰 비용 초과 | 하 | 중 | 캐싱, 배치 처리 최적화 |
| HWP 생성 라이브러리 한계 | 중 | 중 | pyhwpx 등 대안 검토 |
| 벡터 유사도 오탐 | 중 | 중 | 임계값 튜닝, 규제 키워드 필터 강화 |

---

## 5. 디렉토리 구조 (최종)

```
project-popcorn/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
├── app.py                    # Streamlit 메인
│
├── data/
│   ├── schema.json           # 통합 스키마
│   ├── ministry_rr.json      # 부처 R&R
│   └── raw/                  # 원본 데이터
│
├── docs/
│   ├── implementation-plan.md  # 본 문서
│   ├── architecture.md         # 기술 설계 (예정)
│   └── api-spec.md             # API 명세 (예정)
│
├── src/
│   ├── __init__.py
│   ├── ingest.py             # 데이터 적재 (통합)
│   ├── ingest_base.py        # Track 1 수집기
│   ├── ingest_radar.py       # Track 2 수집기
│   ├── fallback_crawler.py   # Fallback 크롤러
│   ├── embedding.py          # 임베딩 파이프라인
│   ├── radar.py              # 리스크 감지
│   ├── agent.py              # LangGraph 워크플로우
│   └── report.py             # HWP 생성
│
├── templates/
│   └── report.hwp            # HWP 템플릿
│
└── research/
    ├── tokenizer_lab.py
    ├── embedding_viz.py
    └── radar_test.py
```

---

## 6. 진행 현황

### 완료 (2026-01-14)
- [x] 프로젝트 세팅 및 디렉토리 구조 생성
- [x] API 키 설정 (.env)
- [x] 부처 R&R 데이터 수집 (정부조직법 기반) → `data/ministry_rr.json`

### 다음 할 일
1. [ ] Phase 1-1: 공공데이터포털 API 연동 테스트
2. [ ] Phase 1-2: 열린국회정보 API 연동 테스트
3. [ ] Phase 2-1: Qdrant Docker 실행
4. [ ] Phase 2-2: Solar Embedding 테스트 (부처 R&R 벡터화)
5. [ ] 과거 법안 데이터 수집 (20~22대)
