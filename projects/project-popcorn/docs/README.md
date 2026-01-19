# Project Popcorn: Cross-Domain Radar

> **버전:** v1.0
> **최종 수정:** 2026-01-19

**타 소관 법안 중 우리 부처에 영향을 미치는 법안을 자동 감지하는 시스템**

---

## 1. 프로젝트 소개

### 1.1 배경
국회에서 발의되는 법안 중 상당수가 여러 부처에 영향을 미칩니다. 그러나 현재는 소관 상임위원회 기준으로만 법안이 분류되어, 타 부처 소관 법안이 우리 부처에 미치는 영향을 파악하기 어렵습니다.

### 1.2 목적
- **Cross-Domain 법안 자동 감지**: 타 소관 법안 중 우리 부처 R&R과 관련된 법안 식별
- **조기 경보 시스템**: 관련 법안 발의 시 Teams 알림
- **피드백 기반 개선**: 도메인 전문가 피드백을 통한 지속적 정확도 향상

### 1.3 주요 기능
| 기능 | 설명 |
|------|------|
| 🔍 **임베딩 기반 유사도 분석** | 법안 제목+제안이유 vs 부처 R&R 비교 |
| 📊 **동적 임계값** | 부처 특성에 따른 맞춤 임계값 |
| 🎯 **키워드 가산점** | 핵심 키워드 법안 누락 방지 |
| 📢 **Teams 알림** | HIGH/MEDIUM 법안 즉시 알림 |
| 📈 **일일 리포트** | Markdown/HTML 자동 생성 |

---

## 2. 빠른 시작

```bash
# 1. 클론 및 이동
cd /path/to/MLAF/projects/project-popcorn

# 2. 가상환경 설정
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력

# 4. Golden Set 테스트
python -m src.pipeline --mode golden

# 5. 전체 스캔
python -m src.pipeline --mode full
```

자세한 내용: [QUICKSTART.md](./QUICKSTART.md)

---

## 3. 아키텍처 개요

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 1.수집  │───▶│ 2.임베딩│───▶│ 3.스코어│───▶│ 4.알림  │
│ Ingest  │    │ Embed   │    │ Score   │    │ Notify  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
 국회 API       OpenAI API     동적 임계값      Teams
 신규 법안      캐시 활용      키워드 가산     웹훅 알림
```

자세한 내용: [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 4. 프로젝트 구조

```
project-popcorn/
├── src/                    # 소스 코드
│   ├── embedder.py         # 임베딩 모듈
│   ├── scorer.py           # 스코어링 모듈
│   ├── radar.py            # 레이더 (감지) 모듈
│   ├── pipeline.py         # 메인 파이프라인
│   └── reporter.py         # 리포트 생성
├── config/                 # 설정 파일
│   └── ministry_config.yaml
├── data/                   # 데이터
│   ├── bills_merged.json   # 법안 데이터
│   ├── golden_set_v2.json  # 테스트 데이터
│   └── cache/              # 임베딩 캐시
├── output/                 # 출력 결과
│   ├── *.json              # 스캔 결과
│   └── *.md                # 리포트
├── docs/                   # 문서
└── logs/                   # 로그
```

---

## 5. 핵심 알고리즘

### 5.1 스코어링 공식
```
최종 스코어 = CosineSim(법안, 부처R&R) + 키워드 가산점
```

### 5.2 Alert Level
| Level | Score 범위 | 대응 |
|-------|------------|------|
| CRITICAL | 0.75+ | 긴급 검토 |
| HIGH | 0.65~0.75 | 우선 검토 |
| MEDIUM | 0.55~0.65 | 정기 검토 |
| LOW | threshold~0.55 | 참고 |

### 5.3 동적 임계값
| 부처 유형 | 감지율 | 임계값 |
|-----------|--------|--------|
| 범용형 (행정안전부 등) | 50%+ | 0.50~0.52 |
| 중간형 (산업통상부 등) | 20~50% | 0.45 |
| 특화형 (국토교통부 등) | 20% 미만 | 0.42 |

---

## 6. 문서 목록

| 문서 | 설명 |
|------|------|
| [README.md](./README.md) | 프로젝트 개요 (현재 문서) |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 시스템 아키텍처 |
| [QUICKSTART.md](./QUICKSTART.md) | 설치 및 실행 가이드 |
| [OPERATIONS.md](./OPERATIONS.md) | 운영 가이드 |
| [CONFIGURATION.md](./CONFIGURATION.md) | 설정 가이드 |
| [INDEX.md](./INDEX.md) | 전체 문서 목록 |

---

## 7. 기술 스택

| 분류 | 기술 |
|------|------|
| Language | Python 3.12 |
| Embedding | OpenAI text-embedding-3-small |
| Scheduler | macOS launchd |
| Notification | Microsoft Teams Webhook |
| Documentation | Markdown, Quarto |

---

## 8. 연락처

- **프로젝트**: Project Popcorn
- **팀**: MLAF
- **문의**: Teams 채널

---

## 9. 라이선스

내부 프로젝트 - 사내 사용 전용
