# Project Popcorn 빠른 시작 가이드

> **버전:** v1.0
> **최종 수정:** 2026-01-19

---

## 1. 사전 요구사항

### 1.1 시스템 요구사항
- macOS 또는 Linux
- Python 3.12+
- 인터넷 연결 (API 호출)

### 1.2 필요한 API 키
| API | 용도 | 발급처 |
|-----|------|--------|
| OpenAI API Key | 임베딩 | https://platform.openai.com |
| 공공데이터포털 API Key | 법안 수집 | https://data.go.kr |

---

## 2. 설치

### 2.1 프로젝트 이동

```bash
cd /path/to/MLAF/projects/project-popcorn
```

### 2.2 가상환경 생성 (uv 사용)

```bash
# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 가상환경 생성
uv venv

# 활성화
source .venv/bin/activate
```

### 2.3 패키지 설치

```bash
# 필수 패키지
uv pip install python-dotenv openai numpy pandas

# Quarto 리포트용 (선택)
uv pip install jupyter pyyaml matplotlib
```

---

## 3. 환경 설정

### 3.1 .env 파일 생성

```bash
cp .env.example .env
```

### 3.2 .env 파일 편집

```bash
# .env 파일 내용
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
DATA_GO_KR_API_KEY=xxxxxxxxxxxxxxxx
```

### 3.3 설정 확인

```bash
# API 키 확인
source .venv/bin/activate
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OpenAI:', os.getenv('OPENAI_API_KEY')[:20]+'...')"
```

---

## 4. 첫 실행

### 4.1 Golden Set 테스트 (권장)

```bash
source .venv/bin/activate
python -m src.pipeline --mode golden
```

**예상 출력:**
```
============================================================
Golden Set Test: 산업통상부
============================================================
Golden bills: 5

Detection Rate: 60.0% (3/5)
...
```

### 4.2 전체 스캔

```bash
# 슬립 방지 + 전체 스캔
caffeinate -i python -m src.pipeline --mode full
```

**예상 시간:**
- 캐시 없음: ~10분
- 캐시 있음: ~30초

### 4.3 일일 스캔

```bash
python -m src.pipeline --mode daily
```

---

## 5. 결과 확인

### 5.1 출력 파일

```bash
ls -la output/
```

**생성되는 파일:**
| 파일 | 설명 |
|------|------|
| `full_scan_YYYYMMDD_HHMMSS.json` | 스캔 결과 (JSON) |
| `full_scan_report_YYYYMMDD_HHMMSS.md` | 리포트 (Markdown) |

### 5.2 리포트 열기

```bash
# Markdown 리포트
cat output/full_scan_report_*.md | head -50

# 또는 VS Code로 열기
code output/full_scan_report_*.md
```

### 5.3 JSON 결과 확인

```bash
# 요약 정보
cat output/full_scan_*.json | python -c "
import sys, json
d = json.load(sys.stdin)
print(f'총 법안: {d[\"total_bills\"]}')
print(f'감지 법안: {d[\"total_alerts\"]}')
print(f'감지율: {d[\"total_alerts\"]/d[\"total_bills\"]*100:.1f}%')
"
```

---

## 6. CLI 옵션

### 6.1 기본 사용법

```bash
python -m src.pipeline [OPTIONS]
```

### 6.2 옵션

| 옵션 | 값 | 설명 |
|------|-----|------|
| `--mode` | `golden`, `daily`, `full` | 실행 모드 |
| `--ministry` | 부처명 | 타겟 부처 (기본: 산업통상부) |
| `--threshold` | 0.0~1.0 | 임계값 (기본: 0.45) |
| `--no-report` | - | 리포트 생성 안 함 |

### 6.3 예시

```bash
# 국토교통부 대상 스캔
python -m src.pipeline --mode full --ministry 국토교통부 --threshold 0.42

# 리포트 없이 빠른 테스트
python -m src.pipeline --mode golden --no-report
```

---

## 7. 문제 해결

### 7.1 API 키 오류

```
openai.OpenAIError: The api_key client option must be set
```

**해결:**
```bash
# .env 파일 확인
cat .env | grep OPENAI

# 환경변수 직접 설정
export OPENAI_API_KEY=sk-proj-xxx
```

### 7.2 모듈 not found

```
ModuleNotFoundError: No module named 'dotenv'
```

**해결:**
```bash
# 가상환경 활성화 확인
which python  # .venv/bin/python이어야 함

# 패키지 재설치
uv pip install python-dotenv
```

### 7.3 캐시 손상

```
json.decoder.JSONDecodeError: Expecting ',' delimiter
```

**해결:**
```bash
# 캐시 삭제
rm data/cache/embedding_cache.json

# 다시 실행
python -m src.pipeline --mode full
```

### 7.4 슬립으로 중단

**해결:**
```bash
# caffeinate로 실행
caffeinate -i python -m src.pipeline --mode full

# 또는 시스템 설정에서 슬립 비활성화
```

---

## 8. 다음 단계

1. **일일 자동화**: [OPERATIONS.md](./OPERATIONS.md) 참고
2. **설정 변경**: [CONFIGURATION.md](./CONFIGURATION.md) 참고
3. **아키텍처 이해**: [ARCHITECTURE.md](./ARCHITECTURE.md) 참고

---

## 9. 빠른 참조

### 자주 쓰는 명령어

```bash
# 가상환경 활성화
source .venv/bin/activate

# Golden Set 테스트
python -m src.pipeline --mode golden

# 전체 스캔 (슬립 방지)
caffeinate -i python -m src.pipeline --mode full

# 일일 스캔
python -m src.pipeline --mode daily

# 결과 확인
ls -la output/
cat output/full_scan_report_*.md | head -50
```
