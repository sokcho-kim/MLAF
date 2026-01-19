# Project Popcorn 문서화 로드맵

> **작성일:** 2026-01-19
> **목적:** 문서화 작업 범위 및 우선순위 정의

---

## 1. 현재 문서 현황

### 1.1 기존 문서 (13개)

| 분류 | 파일 | 상태 | 비고 |
|------|------|------|------|
| **계획** | `implementation-plan.md` | 🔵 구버전 | 초기 계획 |
| | `data-collection-plan.md` | 🔵 구버전 | 데이터 수집 계획 |
| | `embedding-comparison-plan-v1.md` | 🔵 완료 | 임베딩 비교 계획 |
| | `embedding-comparison-plan-v2.md` | 🔵 완료 | v2 계획 |
| | `pipeline-v2-plan.md` | 🟢 현행 | Phase 1-2 계획 |
| | `production-workflow-v1.md` | 🟢 현행 | Phase 3 운영 설계 |
| **분석** | `api-analysis-report.md` | 🔵 완료 | API 분석 |
| | `api-test-report.md` | 🔵 완료 | API 테스트 |
| | `data-sync-report.md` | 🔵 완료 | 데이터 동기화 |
| | `embedding-v2-report.md` | 🟢 현행 | 임베딩 v2 결과 |
| | `embedding-v2-report.qmd` | 🟢 현행 | Quarto 버전 |
| | `overnight-batch-analysis-v1.md` | 🟢 현행 | 야간 배치 분석 |
| | `overnight-batch-analysis-v1.qmd` | 🟢 현행 | Quarto 버전 |

### 1.2 현재 모듈 (20개)

| 분류 | 모듈 | 역할 | 문서화 |
|------|------|------|--------|
| **핵심** | `embedder.py` | 임베딩 | ✅ docstring |
| | `scorer.py` | 스코어링 | ✅ docstring |
| | `radar.py` | 레이더 | ✅ docstring |
| | `pipeline.py` | 파이프라인 | ✅ docstring |
| | `reporter.py` | 리포트 | ✅ docstring |
| **수집** | `ingest.py` | 기본 수집 | ⚠️ 미흡 |
| | `ingest_base.py` | 수집 베이스 | ⚠️ 미흡 |
| | `collect_assembly_bills.py` | 의안 수집 | ⚠️ 미흡 |
| | `collect_summary.py` | 요약 수집 | ⚠️ 미흡 |
| | `merge_bill_data.py` | 병합 | ⚠️ 미흡 |
| **유틸** | `fetch_*.py` (6개) | API fetch | ⚠️ 미흡 |
| | `augment_rr.py` | R&R 증강 | ⚠️ 미흡 |
| | `sample_bills.py` | 샘플링 | ⚠️ 미흡 |
| **기타** | `agent.py` | 에이전트 | ⚠️ 미흡 |
| | `report.py` | HWP 리포트 | 🔴 스켈레톤 |

---

## 2. 필요한 문서

### 2.1 필수 문서 (Must Have)

| # | 문서 | 용도 | 우선순위 |
|---|------|------|----------|
| 1 | **README.md** | 프로젝트 개요, 빠른 시작 | 🔴 P0 |
| 2 | **ARCHITECTURE.md** | 시스템 아키텍처, 모듈 구조 | 🔴 P0 |
| 3 | **QUICKSTART.md** | 설치, 실행, 설정 가이드 | 🔴 P0 |
| 4 | **OPERATIONS.md** | 운영 가이드 (일배치, 모니터링) | 🟠 P1 |
| 5 | **CONFIGURATION.md** | 설정 파일 설명 | 🟠 P1 |

### 2.2 선택 문서 (Nice to Have)

| # | 문서 | 용도 | 우선순위 |
|---|------|------|----------|
| 6 | `API_REFERENCE.md` | 모듈/함수 레퍼런스 | 🟡 P2 |
| 7 | `TROUBLESHOOTING.md` | 문제 해결 가이드 | 🟡 P2 |
| 8 | `CHANGELOG.md` | 변경 이력 | 🟡 P2 |

---

## 3. 문서화 작업 계획

### Phase A: 핵심 문서 (Today)

```
docs/
├── README.md              # [NEW] 프로젝트 개요
├── ARCHITECTURE.md        # [NEW] 아키텍처
└── QUICKSTART.md          # [NEW] 빠른 시작
```

**README.md 목차:**
1. 프로젝트 소개
2. 주요 기능
3. 빠른 시작
4. 아키텍처 개요
5. 문서 구조
6. 라이선스

**ARCHITECTURE.md 목차:**
1. 시스템 개요
2. 모듈 구조
3. 데이터 흐름
4. 핵심 알고리즘 (임베딩, 스코어링, 키워드 가산점)
5. 외부 의존성

**QUICKSTART.md 목차:**
1. 사전 요구사항
2. 설치
3. 환경 설정 (.env)
4. 첫 실행
5. 결과 확인

### Phase B: 운영 문서 (Day 2)

```
docs/
├── OPERATIONS.md          # [NEW] 운영 가이드
└── CONFIGURATION.md       # [NEW] 설정 가이드
```

**OPERATIONS.md 목차:**
1. 일배치 실행
2. 수동 스캔
3. 알림 설정
4. 로그 확인
5. 모니터링

**CONFIGURATION.md 목차:**
1. 환경 변수 (.env)
2. 부처 설정 (ministry_config.yaml)
3. 임계값 조정
4. 키워드 추가

### Phase C: 기존 문서 정리 (Day 3)

| 작업 | 내용 |
|------|------|
| 아카이브 | 구버전 문서를 `docs/archive/`로 이동 |
| 정리 | 현행 문서만 `docs/`에 유지 |
| 인덱스 | `docs/INDEX.md` 문서 목록 생성 |

**정리 후 구조:**
```
docs/
├── README.md
├── ARCHITECTURE.md
├── QUICKSTART.md
├── OPERATIONS.md
├── CONFIGURATION.md
├── INDEX.md                    # 문서 인덱스
├── analysis/                   # 분석 리포트
│   ├── embedding-v2-report.md
│   ├── overnight-batch-analysis-v1.md
│   └── *.qmd
├── plans/                      # 계획 문서
│   ├── pipeline-v2-plan.md
│   └── production-workflow-v1.md
└── archive/                    # 구버전/완료 문서
    ├── implementation-plan.md
    ├── data-collection-plan.md
    └── ...
```

---

## 4. 문서 작성 원칙

### 4.1 포맷
- **언어:** 한국어 (코드/명령어는 영어)
- **형식:** Markdown
- **버전:** 주요 문서는 버전 관리 (v1, v2...)

### 4.2 헤더
```markdown
# 문서 제목

> **버전:** v1
> **작성일:** 2026-01-19
> **최종 수정:** 2026-01-19
```

### 4.3 코드 블록
- 실행 가능한 명령어 제공
- 복사-붙여넣기 가능하게

---

## 5. 작업 순서

| 순서 | 작업 | 예상 시간 |
|------|------|-----------|
| 1 | README.md 작성 | 20분 |
| 2 | ARCHITECTURE.md 작성 | 30분 |
| 3 | QUICKSTART.md 작성 | 20분 |
| 4 | 기존 문서 폴더 정리 | 10분 |
| 5 | INDEX.md 생성 | 10분 |

**총 예상: ~1.5시간**

---

## 6. 승인 후 진행

- [ ] 로드맵 검토
- [ ] README.md 작성 시작
- [ ] ARCHITECTURE.md 작성
- [ ] QUICKSTART.md 작성
- [ ] 폴더 구조 정리

---

*검토 후 작업 시작합니다.*
