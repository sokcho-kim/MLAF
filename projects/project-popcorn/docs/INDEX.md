# Project Popcorn 문서 인덱스

> **최종 수정:** 2026-01-19

---

## 📚 핵심 문서

| 문서 | 설명 | 대상 |
|------|------|------|
| [README.md](./README.md) | 프로젝트 개요, 주요 기능 | 모든 사용자 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 시스템 아키텍처, 모듈 구조 | 개발자 |
| [QUICKSTART.md](./QUICKSTART.md) | 설치 및 실행 가이드 | 신규 사용자 |
| [OPERATIONS.md](./OPERATIONS.md) | 운영 가이드 (일배치, 스케줄러) | 운영자 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | 배포 가이드 (Docker, Native) | DevOps |

---

## 📂 폴더 구조

```
docs/
├── README.md              # 프로젝트 개요
├── ARCHITECTURE.md        # 아키텍처
├── QUICKSTART.md          # 빠른 시작
├── INDEX.md               # 문서 인덱스 (현재 문서)
│
├── plans/                 # 📋 계획 문서
│   ├── pipeline-v2-plan.md
│   ├── production-workflow-v1.md
│   └── documentation-roadmap.md
│
├── analysis/              # 📊 분석 리포트
│   ├── embedding-v2-report.md
│   ├── overnight-batch-analysis-v1.md
│   ├── overnight-batch-analysis-v1.html
│   ├── *.qmd              # Quarto 소스
│   └── figures/           # 시각화 이미지
│
└── archive/               # 📦 구버전/완료 문서
    ├── implementation-plan.md
    ├── data-collection-plan.md
    └── ...
```

---

## 📋 계획 문서 (plans/)

| 문서 | 설명 | 상태 |
|------|------|------|
| [pipeline-v2-plan.md](./plans/pipeline-v2-plan.md) | Phase 1-2 파이프라인 설계 | ✅ 완료 |
| [production-workflow-v1.md](./plans/production-workflow-v1.md) | Phase 3 운영 파이프라인 설계 | 🟡 진행중 |
| [documentation-roadmap.md](./plans/documentation-roadmap.md) | 문서화 로드맵 | ✅ 완료 |

---

## 📊 분석 리포트 (analysis/)

| 문서 | 설명 | 형식 |
|------|------|------|
| [embedding-v2-report.md](./analysis/embedding-v2-report.md) | 임베딩 v2 전략 테스트 결과 | MD |
| [embedding-v2-report.qmd](./analysis/embedding-v2-report.qmd) | 임베딩 v2 Quarto 버전 | QMD |
| [overnight-batch-analysis-v1.md](./analysis/overnight-batch-analysis-v1.md) | 야간 배치 분석 (부처별/임계값) | MD |
| [overnight-batch-analysis-v1.html](./analysis/overnight-batch-analysis-v1.html) | 야간 배치 분석 HTML | HTML |

### 주요 분석 결과

**부처별 감지율 (TOP 5):**
| 순위 | 부처 | 감지율 |
|------|------|--------|
| 1 | 행정안전부 | 75.2% |
| 2 | 산업통상부 | 60.1% |
| 3 | 보건복지부 | 53.5% |
| 4 | 법무부 | 50.9% |
| 5 | 국방부 | 39.4% |

**임계값 권장:**
- 범용형 부처: 0.50~0.52
- 중간형 부처: 0.45
- 특화형 부처: 0.42

---

## 📦 아카이브 (archive/)

| 문서 | 설명 | 비고 |
|------|------|------|
| implementation-plan.md | 초기 구현 계획 | 구버전 |
| data-collection-plan.md | 데이터 수집 계획 | 완료 |
| embedding-comparison-plan-v1.md | 임베딩 비교 계획 v1 | 완료 |
| embedding-comparison-plan-v2.md | 임베딩 비교 계획 v2 | 완료 |
| api-analysis-report.md | API 분석 결과 | 완료 |
| api-test-report.md | API 테스트 결과 | 완료 |
| data-sync-report.md | 데이터 동기화 결과 | 완료 |

---

## 🔜 작성 예정

| 문서 | 설명 | 우선순위 |
|------|------|----------|
| CONFIGURATION.md | 설정 가이드 (임계값, 키워드) | P2 |
| TROUBLESHOOTING.md | 문제 해결 가이드 | P2 |
| CHANGELOG.md | 변경 이력 | P3 |

✅ **완료:** OPERATIONS.md, DEPLOYMENT.md

---

## 🔗 관련 문서

- **작업일지**: `/docs/worklog/YYYY-MM-DD.md`
- **프로젝트 지침**: `/CLAUDE.md`
- **데이터 파이프라인**: `/docs/data-pipeline.md`

---

*Last updated: 2026-01-19*
