# Project Popcorn 운영 가이드

> **버전:** v1.0
> **최종 수정:** 2026-01-19

---

## 1. 일배치 실행

### 1.1 수동 실행

```bash
cd /Users/sokchokim/sokcho_code/MLAF/projects/project-popcorn
source .venv/bin/activate

# 기본 실행 (산업통상부, 어제 이후 법안)
python run_daily.py

# 특정 부처
python run_daily.py --ministry 국토교통부

# 특정 날짜 이후
python run_daily.py --since 2026-01-15

# 테스트 모드 (수집/알림 건너뜀)
python run_daily.py --test
```

### 1.2 실행 결과

```
[2026-01-19 09:00:00] ============================================================
[2026-01-19 09:00:00] Cross-Domain Radar 일배치 시작
[2026-01-19 09:00:00] ============================================================
[2026-01-19 09:00:01] [1/4] 신규 법안 수집
[2026-01-19 09:00:05]   → 신규: 15건, 추가: 12건
[2026-01-19 09:00:06] [2/4] Cross-Domain 스캔
[2026-01-19 09:00:10]   → 감지: 3건
[2026-01-19 09:00:11] [3/4] 리포트 생성
[2026-01-19 09:00:11]   → 리포트: output/daily_report_2026-01-19.md
[2026-01-19 09:00:12] [4/4] Teams 알림
[2026-01-19 09:00:12]   → 알림 발송: 성공
```

---

## 2. 스케줄러 설정 (launchd)

### 2.1 plist 파일 복사

```bash
cp config/com.popcorn.radar.plist ~/Library/LaunchAgents/
```

### 2.2 스케줄러 등록

```bash
# 등록
launchctl load ~/Library/LaunchAgents/com.popcorn.radar.plist

# 상태 확인
launchctl list | grep popcorn

# 즉시 실행 (테스트)
launchctl start com.popcorn.radar
```

### 2.3 스케줄러 해제

```bash
# 해제
launchctl unload ~/Library/LaunchAgents/com.popcorn.radar.plist

# 삭제
rm ~/Library/LaunchAgents/com.popcorn.radar.plist
```

### 2.4 실행 시간 변경

`config/com.popcorn.radar.plist` 수정:

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>9</integer>   <!-- 시 (0-23) -->
    <key>Minute</key>
    <integer>0</integer>   <!-- 분 (0-59) -->
</dict>
```

수정 후 재등록:
```bash
launchctl unload ~/Library/LaunchAgents/com.popcorn.radar.plist
launchctl load ~/Library/LaunchAgents/com.popcorn.radar.plist
```

---

## 3. Teams 웹훅 설정

### 3.1 웹훅 URL 발급

1. Teams 채널 > ... > 커넥터
2. "Incoming Webhook" 추가
3. 이름 입력 (예: Cross-Domain Radar)
4. 웹훅 URL 복사

### 3.2 환경변수 설정

`.env` 파일에 추가:

```bash
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxx
```

### 3.3 테스트

```bash
source .venv/bin/activate
python -m src.notifier --test --url "YOUR_WEBHOOK_URL"
```

---

## 4. 로그 확인

### 4.1 로그 위치

```
logs/
├── daily_YYYYMMDD_HHMMSS.json   # 일배치 결과
├── launchd_stdout.log           # launchd 표준 출력
└── launchd_stderr.log           # launchd 에러
```

### 4.2 로그 확인

```bash
# 최근 일배치 로그
cat logs/daily_*.json | tail -1 | jq .

# launchd 로그
tail -f logs/launchd_stdout.log

# 에러 로그
tail -f logs/launchd_stderr.log
```

### 4.3 로그 정리

```bash
# 7일 이상 된 로그 삭제
find logs/ -name "*.json" -mtime +7 -delete
find logs/ -name "*.log" -mtime +7 -delete
```

---

## 5. 모니터링

### 5.1 헬스체크

```bash
# 스케줄러 상태
launchctl list | grep popcorn

# 최근 실행 확인
ls -lt logs/daily_*.json | head -5

# 최근 결과 요약
cat logs/daily_*.json | tail -1 | jq '{status, ministry, alerts: .scan.alerts}'
```

### 5.2 수동 테스트

```bash
# 전체 파이프라인 테스트 (알림 제외)
python run_daily.py --skip-notify

# Golden Set 테스트
python -m src.pipeline --mode golden
```

---

## 6. 슬립 방지

### 6.1 시스템 설정

시스템 환경설정 > 에너지 절약:
- "디스플레이가 꺼져 있을 때 자동으로 잠자기 방지" 체크

### 6.2 pmset 명령

```bash
# 현재 설정 확인
pmset -g

# 전원 연결 시 슬립 비활성화
sudo pmset -c sleep 0
sudo pmset -c disksleep 0

# 복원
sudo pmset -c sleep 10
```

### 6.3 caffeinate (임시)

```bash
# 스크립트 실행 중 슬립 방지
caffeinate -i python run_daily.py
```

---

## 7. 문제 해결

### 7.1 스케줄러가 실행되지 않음

```bash
# 1. 상태 확인
launchctl list | grep popcorn

# 2. 로그 확인
cat logs/launchd_stderr.log

# 3. 수동 실행 테스트
launchctl start com.popcorn.radar

# 4. 재등록
launchctl unload ~/Library/LaunchAgents/com.popcorn.radar.plist
launchctl load ~/Library/LaunchAgents/com.popcorn.radar.plist
```

### 7.2 Teams 알림 실패

```bash
# 1. 웹훅 URL 확인
echo $TEAMS_WEBHOOK_URL

# 2. 테스트 발송
python -m src.notifier --test

# 3. curl 직접 테스트
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"테스트"}' \
  "$TEAMS_WEBHOOK_URL"
```

### 7.3 API 오류

```bash
# 1. API 키 확인
cat .env | grep API_KEY

# 2. 네트워크 확인
curl -I https://open.assembly.go.kr

# 3. 재시도
python run_daily.py --skip-ingest
```

---

## 8. 백업 및 복구

### 8.1 중요 파일

```
config/ministry_config.yaml    # 부처 설정
.env                           # 환경변수
data/bills_master.json         # 마스터 데이터
data/cache/embedding_cache.json # 임베딩 캐시
```

### 8.2 백업

```bash
# 설정 백업
tar -czf backup_config_$(date +%Y%m%d).tar.gz config/ .env

# 데이터 백업
tar -czf backup_data_$(date +%Y%m%d).tar.gz data/
```

### 8.3 복구

```bash
# 마스터 초기화 (bills_merged.json에서)
python -m src.ingest_daily --init-master
```

---

## 9. 일일 체크리스트

- [ ] 09:00 스케줄러 실행 확인
- [ ] Teams 알림 수신 확인
- [ ] HIGH/CRITICAL 법안 검토
- [ ] 피드백 반영 (필요시)

---

*Last updated: 2026-01-19*
