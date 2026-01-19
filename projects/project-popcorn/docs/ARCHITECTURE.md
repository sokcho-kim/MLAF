# Project Popcorn 아키텍처

> **버전:** v1.0
> **최종 수정:** 2026-01-19

---

## 1. 시스템 개요

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Cross-Domain Radar System                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐                                                            │
│  │   External   │                                                            │
│  │   Systems    │                                                            │
│  └──────┬───────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │   Ingest     │───▶│    Embed     │───▶│    Score     │───▶│   Notify   │ │
│  │   Layer      │    │    Layer     │    │    Layer     │    │   Layer    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│         │                   │                   │                   │        │
│         ▼                   ▼                   ▼                   ▼        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  국회 API    │    │  OpenAI API  │    │  동적 임계값  │    │   Teams    │ │
│  │  - 의안정보   │    │  - embedding │    │  - 키워드    │    │  - Webhook │ │
│  └──────────────┘    │  - 캐시      │    │  - 부처별    │    └────────────┘ │
│                      └──────────────┘    └──────────────┘                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          Storage Layer                                   ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       ││
│  │  │  bills  │  │  cache  │  │ config  │  │ output  │  │  logs   │       ││
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 데이터 흐름

```
국회 API ──▶ 신규 법안 수집 ──▶ 임베딩 생성 ──▶ 유사도 계산 ──▶ 필터링 ──▶ 알림
   │              │                 │               │            │          │
   ▼              ▼                 ▼               ▼            ▼          ▼
의안정보     bills_daily.json   embedding_cache  score + bonus  threshold  Teams
BillInfo                         (33MB)          키워드 가산    동적 설정   웹훅
```

---

## 2. 모듈 구조

### 2.1 핵심 모듈

```
src/
├── embedder.py      # 임베딩 생성
├── scorer.py        # 유사도 스코어링
├── radar.py         # Cross-Domain 감지
├── pipeline.py      # 파이프라인 오케스트레이션
└── reporter.py      # 리포트 생성
```

#### 2.1.1 Embedder (`embedder.py`)

```python
class Embedder:
    """텍스트 임베딩 클래스"""

    def embed_text(text: str) -> list[float]
        """텍스트 → 1536차원 벡터"""

    def embed_bill(bill: dict) -> list[float]
        """법안 임베딩 (제목 + summary)"""

    def embed_batch(bills: list[dict]) -> list[list[float]]
        """배치 임베딩"""
```

**특징:**
- OpenAI `text-embedding-3-small` 모델
- MD5 기반 캐시 (중복 API 호출 방지)
- v2 전략: 제목 + 제안이유(summary) 결합

#### 2.1.2 Scorer (`scorer.py`)

```python
class Scorer:
    """유사도 스코어링 클래스"""

    def cosine_similarity(vec_a, vec_b) -> float
        """코사인 유사도 계산"""

    def get_alert_level(score: float) -> AlertLevel
        """스코어 → Alert Level 변환"""

    def score_bill(bill_vec, rr_vec) -> ScoreResult
        """법안-R&R 유사도 스코어링"""
```

**Alert Level 기준:**
| Level | Score 범위 |
|-------|------------|
| CRITICAL | 0.75+ |
| HIGH | 0.65~0.75 |
| MEDIUM | 0.55~0.65 |
| LOW | 0.45~0.55 |
| NONE | 0.45 미만 |

#### 2.1.3 Radar (`radar.py`)

```python
class CrossDomainRadar:
    """Cross-Domain 법안 감지 레이더"""

    def detect_risk(bill: dict) -> RiskAlert | None
        """단일 법안 리스크 감지"""

    def scan_bills(bills: list[dict]) -> list[RiskAlert]
        """다중 법안 스캔"""

    def scan_from_file(bills_file: Path) -> list[RiskAlert]
        """파일에서 로드 후 스캔"""
```

**RiskAlert 데이터:**
```python
@dataclass
class RiskAlert:
    bill_id: str
    bill_name: str
    committee: str           # 소관 상임위
    target_ministry: str     # 영향받는 부처
    similarity_score: float
    alert_level: str         # LOW/MEDIUM/HIGH/CRITICAL
    propose_dt: str
    proposer: str
    summary_preview: str     # 제안이유 200자
    detected_at: str
```

#### 2.1.4 Pipeline (`pipeline.py`)

```python
class BillRadarPipeline:
    """메인 파이프라인"""

    def run_full_scan() -> dict
        """전체 법안 스캔 (1,021건)"""

    def run_daily() -> dict
        """일일 신규 법안 스캔"""

    def run_golden_test() -> dict
        """Golden Set 테스트"""
```

#### 2.1.5 Reporter (`reporter.py`)

```python
class Reporter:
    """리포트 생성 클래스"""

    def generate_full_scan_report(result: dict) -> Path
        """전체 스캔 Markdown 리포트"""

    def generate_daily_report(result: dict) -> Path
        """일일 리포트"""

    def export_to_json(result: dict) -> Path
        """JSON 내보내기"""
```

---

### 2.2 수집 모듈

```
src/
├── ingest.py                 # 기본 수집
├── ingest_base.py            # 수집 베이스 클래스
├── collect_assembly_bills.py # 의안상세정보 수집
├── collect_summary.py        # BillInfoService 수집
└── merge_bill_data.py        # 데이터 병합
```

### 2.3 유틸리티 모듈

```
src/
├── fetch_ministry_rr.py      # 부처 R&R 수집
├── fetch_ministry_orgs.py    # 부처 조직 수집
├── fetch_golden_set.py       # Golden Set 생성
├── augment_rr.py             # R&R 텍스트 증강
└── sample_bills.py           # 법안 샘플링
```

---

## 3. 핵심 알고리즘

### 3.1 임베딩 전략 (v2)

```
입력: 법안 데이터 (bill_name, summary)

텍스트 결합:
  if summary exists:
    text = f"{bill_name}\n\n{summary}"
  else:
    text = bill_name  # fallback

출력: 1536차원 벡터
```

**v2 전략 효과:**
| 전략 | 평균 유사도 | Hard 케이스 |
|------|-------------|-------------|
| v1 (제목만) | 0.38 | 0.38 |
| v2 (제목+요약) | 0.49 | 0.49 (+29%) |

### 3.2 동적 임계값 시스템

```yaml
# config/ministry_config.yaml
ministries:
  산업통상부:
    threshold: 0.45
    type: 중간형
    keywords: [에너지, 탄소, 산업, 통상]
    keyword_bonus: 0.03

  국토교통부:
    threshold: 0.42
    type: 특화형
    keywords: [건설, 도로, 철도, 주택]
    keyword_bonus: 0.02
```

**부처 유형별 임계값:**
| 유형 | 감지율 특성 | 권장 임계값 |
|------|-------------|-------------|
| 범용형 | 50%+ (노이즈 多) | 0.50~0.52 |
| 중간형 | 20~50% | 0.45 |
| 특화형 | 20% 미만 (정밀) | 0.42 |

### 3.3 키워드 가산점 로직

```
최종 스코어 = 기본 유사도 + 키워드 가산점

키워드 가산점 계산:
  matched = count(keyword in bill_name for keyword in keywords)
  bonus = min(matched × keyword_bonus, 0.05)  # 최대 0.05

예시:
  "탄소중립기본법"
  - 기본 유사도: 0.441
  - 키워드 매칭: "탄소" (1개)
  - 가산점: 0.03
  - 최종 스코어: 0.471 → ✅ 감지 (threshold 0.45)
```

---

## 4. 데이터 구조

### 4.1 저장소 구조

```
data/
├── bills_merged.json         # 전체 법안 (1,021건)
├── bills_raw_assembly.json   # 원본 (의안상세정보)
├── bills_raw_summary.json    # 원본 (BillInfoService)
├── golden_set_v2.json        # 테스트 데이터 (5건)
├── ministry_rr_augmented.json # 부처 R&R (18개)
├── daily/                    # 일별 수집
│   └── YYYY-MM-DD_bills.json
└── cache/
    └── embedding_cache.json  # 임베딩 캐시 (~33MB)
```

### 4.2 법안 데이터 스키마

```json
{
  "bill_id": "PRC_V2U5O0Y9Q1U3J1M1K4Q2B0E4D2M2E5",
  "bill_no": "2200001",
  "bill_name": "탄소중립·녹색성장 기본법 일부개정법률안",
  "committee": "산업통상자원중소벤처기업위원회",
  "propose_dt": "2025-06-01",
  "proposer": "홍길동의원 등 10인",
  "summary": "탄소중립 목표 달성을 위해...",
  "proc_result": "계류"
}
```

### 4.3 스캔 결과 스키마

```json
{
  "scan_type": "full_scan",
  "ministry": "산업통상부",
  "threshold": 0.45,
  "scanned_at": "2026-01-19T09:00:00",
  "total_bills": 1021,
  "total_alerts": 614,
  "alerts_by_level": {
    "CRITICAL": 0,
    "HIGH": 2,
    "MEDIUM": 82,
    "LOW": 530
  },
  "alerts": [...]
}
```

---

## 5. 외부 의존성

### 5.1 API

| API | 용도 | 인증 |
|-----|------|------|
| OpenAI Embedding API | 텍스트 임베딩 | API Key |
| 열린국회정보 API | 의안 정보 수집 | API Key |
| 공공데이터포털 API | BillInfoService | API Key |
| Microsoft Teams Webhook | 알림 발송 | Webhook URL |

### 5.2 Python 패키지

```
# 핵심
openai>=1.0.0        # 임베딩 API
numpy>=1.24.0        # 벡터 연산
python-dotenv>=1.0.0 # 환경 변수

# 리포트
pandas>=2.0.0        # 데이터 처리
matplotlib>=3.7.0    # 시각화

# 옵션
jupyter>=1.0.0       # Quarto 렌더링
pyyaml>=6.0.0        # YAML 설정
```

---

## 6. 확장성

### 6.1 부처 확장
- `config/ministry_config.yaml`에 부처 추가
- R&R 텍스트 및 키워드 설정
- 임계값 설정

### 6.2 알림 채널 확장
- `src/notifier.py`에 채널 추가
- Slack, Email 등 지원 가능

### 6.3 스케줄링 확장
- 현재: macOS launchd
- 확장: GitHub Actions, AWS Lambda 등

---

## 7. 성능 지표

| 지표 | 값 | 비고 |
|------|-----|------|
| 전체 스캔 시간 | ~10분 | 1,021건, 캐시 없음 |
| 캐시 스캔 시간 | ~30초 | 캐시 있음 |
| 임베딩 캐시 크기 | ~33MB | 1,021건 기준 |
| API 비용 | ~$0.02/월 | 일배치 기준 |

---

## 8. 보안 고려사항

| 항목 | 대응 |
|------|------|
| API Key 관리 | `.env` 파일 (gitignore) |
| 데이터 보안 | 로컬 저장, 외부 전송 없음 |
| 로그 관리 | 민감 정보 마스킹 |
