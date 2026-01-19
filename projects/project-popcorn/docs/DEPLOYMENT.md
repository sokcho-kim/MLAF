# Cross-Domain Radar 배포 가이드

> **버전:** v1.0
> **최종 수정:** 2026-01-19

---

## 1. 개요

회사 데스크탑(또는 서버)에 Cross-Domain Radar를 배포하는 방법을 설명합니다.

**배포 옵션:**
| 방식 | 권장 환경 | 난이도 |
|------|----------|--------|
| **Native Python** | macOS/Linux/Windows | 쉬움 |
| **Docker** | Linux/macOS | 중간 |
| **Docker + Scheduler** | 서버 (24/7) | 중간 |

---

## 2. 사전 요구사항

### 2.1 공통
- OpenAI API Key (임베딩용)
- 법안 데이터 파일 (`bills_master.json` 또는 `bills_merged.json`)

### 2.2 Native Python
- Python 3.10+ (권장: 3.12)
- pip 또는 uv

### 2.3 Docker
- Docker 20.10+
- Docker Compose v2+

---

## 3. Native Python 배포

### 3.1 자동 설치 (권장)

```bash
# 프로젝트 복사
git clone <repo-url> project-popcorn
cd project-popcorn

# 설치 스크립트 실행
./deploy/setup-native.sh
```

### 3.2 수동 설치

```bash
# 1. 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements-prod.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 입력

# 4. 데이터 복사
cp /path/to/bills_master.json data/

# 5. 테스트
python run_daily.py --test
```

### 3.3 Windows 설치

```cmd
REM 설치 스크립트 실행
deploy\setup-windows.bat
```

### 3.4 스케줄러 설정

**macOS (launchd):**
```bash
cp config/com.popcorn.radar.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.popcorn.radar.plist
```

**Windows (작업 스케줄러):**
1. 작업 스케줄러 열기
2. 기본 작업 만들기
3. 트리거: 매일 09:00
4. 동작: 프로그램 시작
   - 프로그램: `C:\path\to\project-popcorn\.venv\Scripts\python.exe`
   - 인수: `run_daily.py`
   - 시작 위치: `C:\path\to\project-popcorn`

**Linux (cron):**
```bash
# crontab 편집
crontab -e

# 추가 (매일 09:00)
0 9 * * * cd /path/to/project-popcorn && .venv/bin/python run_daily.py >> logs/cron.log 2>&1
```

---

## 4. Docker 배포

### 4.1 자동 설치 (권장)

```bash
# 프로젝트 복사
git clone <repo-url> project-popcorn
cd project-popcorn

# Docker 설치 스크립트 실행
./deploy/setup-docker.sh
```

### 4.2 수동 설치

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일 편집

# 2. 데이터 복사
mkdir -p data
cp /path/to/bills_master.json data/

# 3. Docker 이미지 빌드
docker build -t popcorn-radar:latest .

# 4. 테스트 실행
docker run --rm --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config:ro \
  popcorn-radar:latest python run_daily.py --test
```

### 4.3 수동 실행

```bash
# 기본 실행
docker-compose run --rm radar

# 특정 부처
docker-compose run --rm radar python run_daily.py --ministry 국토교통부
```

### 4.4 스케줄러 실행 (24/7)

```bash
# 스케줄러 시작 (매일 09:00 자동 실행)
docker-compose up -d scheduler

# 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f scheduler

# 중지
docker-compose down
```

---

## 5. 데이터 이전

### 5.1 필수 파일

```
project-popcorn/
├── .env                    # API 키 (직접 생성)
├── data/
│   └── bills_master.json   # 법안 데이터 (복사)
└── data/cache/
    └── embedding_cache.json  # 임베딩 캐시 (선택, 33MB)
```

### 5.2 데이터 복사

```bash
# 개인 PC에서 (scp 사용)
scp data/bills_master.json user@work-pc:/path/to/project-popcorn/data/
scp data/cache/embedding_cache.json user@work-pc:/path/to/project-popcorn/data/cache/

# 또는 USB/공유폴더 사용
```

### 5.3 캐시 유무에 따른 차이

| 항목 | 캐시 있음 | 캐시 없음 |
|------|----------|----------|
| 첫 실행 시간 | ~10초 | ~30분 |
| API 호출 | 없음 | 1,000건+ |
| API 비용 | $0 | ~$0.10 |

**권장:** 캐시 파일도 함께 복사

---

## 6. 환경변수 설정

`.env` 파일 예시:

```bash
# 필수
OPENAI_API_KEY=sk-proj-xxxxx

# 선택 (법안 수집용)
DATA_GO_KR_API_KEY=xxxxx

# 선택 (Teams 알림용)
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxxxx
```

---

## 7. 검증

### 7.1 테스트 실행

```bash
# Native
python run_daily.py --test

# Docker
docker-compose run --rm radar python run_daily.py --test
```

### 7.2 예상 출력

```
[2026-01-19 09:00:00] Cross-Domain Radar 일배치 시작
[2026-01-19 09:00:01] [1/4] 수집 건너뜀 (skip_ingest)
[2026-01-19 09:00:01] [2/4] Cross-Domain 스캔
[2026-01-19 09:00:01]   → 부처: 산업통상부, 임계값: 0.45
[2026-01-19 09:00:01]   → 법안 로드: 1021건
...
[2026-01-19 09:00:02] 일배치 완료!
```

### 7.3 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| `ModuleNotFoundError` | 의존성 미설치 | `pip install -r requirements-prod.txt` |
| `OPENAI_API_KEY not set` | 환경변수 미설정 | `.env` 파일 확인 |
| `bills_master.json not found` | 데이터 파일 없음 | 데이터 복사 |
| `Permission denied` | 실행 권한 없음 | `chmod +x deploy/*.sh` |

---

## 8. 빠른 배포 체크리스트

```
[ ] 1. 코드 복사 (git clone 또는 zip)
[ ] 2. .env 파일 생성 및 API 키 입력
[ ] 3. 데이터 파일 복사 (bills_master.json)
[ ] 4. 캐시 파일 복사 (선택, embedding_cache.json)
[ ] 5. 설치 스크립트 실행 (setup-native.sh 또는 setup-docker.sh)
[ ] 6. 테스트 실행 (python run_daily.py --test)
[ ] 7. 스케줄러 설정 (cron/launchd/작업스케줄러)
[ ] 8. Teams 웹훅 설정 (선택)
```

---

*Last updated: 2026-01-19*
