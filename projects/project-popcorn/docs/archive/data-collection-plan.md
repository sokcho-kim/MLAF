# 데이터 재수집 계획

**작성일**: 2026-01-15
**목적**: API 데이터 품질 문제 해결 및 통합 데이터셋 구축
**참고**: `docs/data-sync-report.md`

---

## 1. 배경

### 1.1 현재 데이터 문제점

| 파일 | 문제 |
|------|------|
| `test_bills.json` | proc_result 0%, summary 없음 |
| `test_bills_with_content.json` | proc_result 0%, summary 70.5% |
| `bill_summary_cache.json` | committee 없음 |

### 1.2 원인 분석

```
[국회의원발의법률안 API]
  └─ PROC_RESULT 필드가 모두 null (API 자체 문제)
  └─ COMMITTEE 64%만 채워짐

[공공데이터포털 API]
  └─ committee 필드 자체가 없음
  └─ summary는 98% 제공

→ 두 API의 장점을 조합해야 함
```

---

## 2. 목표 데이터셋

### 2.1 스키마

```json
{
  "bill_no": "2216052",
  "bill_id": "PRC_X2V5W1S2S1Q9R1P5O3O1W1X4V2W6U5",
  "bill_name": "영유아보육법 일부개정법률안",
  "committee": "보건복지위원회",
  "proc_result": "대안반영",
  "vote_info": {
    "total": 188,
    "yes": 188,
    "no": 0,
    "blank": 0
  },
  "summary": "제안이유 및 주요내용...",
  "propose_dt": "2026-01-14",
  "proposer": "박선영의원등 10인"
}
```

### 2.2 필드별 출처

| 필드 | 출처 API | 예상 품질 |
|------|----------|----------|
| bill_no | 공통 (조인 키) | 100% |
| bill_id | 의안상세정보 | 100% |
| bill_name | 의안상세정보 | 100% |
| committee | 의안상세정보 | 99% |
| proc_result | 의안상세정보 | 100% |
| vote_info | 의안상세정보 | 92% |
| summary | BillInfoService2 | 98% |
| propose_dt | 의안상세정보 | 100% |
| proposer | 의안상세정보 | 100% |

### 2.3 품질 목표

| 지표 | 현재 | 목표 |
|------|------|------|
| committee 채워진 비율 | 64% | **99%** |
| proc_result 채워진 비율 | 0% | **100%** |
| summary 채워진 비율 | 70.5% | **95%+** |

---

## 3. 수집 전략

### 3.1 2단계 수집 + 조인

```
┌─────────────────────────────────────────────────────────────┐
│                     데이터 수집 파이프라인                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Step 1] 열린국회정보 - 의안상세정보                          │
│  ──────────────────────────────────────                      │
│  URL: https://open.assembly.go.kr/portal/openapi/            │
│       nwbpacrgavhjryiph                                      │
│  파라미터: AGE=22, pSize=1000                                │
│  수집 필드:                                                   │
│    - BILL_NO (조인 키)                                       │
│    - BILL_ID, BILL_NM                                        │
│    - COMMITTEE_NM (소관위)                                   │
│    - PROC_RESULT_CD (처리결과)                               │
│    - VOTE_TCNT, YES_TCNT, NO_TCNT, BLANK_TCNT               │
│    - PROPOSE_DT, PROPOSER                                    │
│                                                              │
│                          ↓                                   │
│                                                              │
│  [Step 2] 공공데이터포털 - BillInfoService2                   │
│  ──────────────────────────────────────────                  │
│  URL: http://apis.data.go.kr/9710000/BillInfoService2/       │
│       getBillInfoList                                        │
│  파라미터: bill_kind_cd=B04, end_ord=22                      │
│  수집 필드:                                                   │
│    - billNo (조인 키)                                        │
│    - summary (제안이유/주요내용)                              │
│                                                              │
│                          ↓                                   │
│                                                              │
│  [Step 3] 데이터 조인                                         │
│  ─────────────────────                                       │
│  조인 키: bill_no                                            │
│  결과: 통합 데이터셋                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 수집 범위

| 항목 | 값 | 비고 |
|------|-----|------|
| 대상 국회 | 22대 | AGE=22 |
| 법안 종류 | 법률안 | bill_kind_cd=B04 |
| 예상 전체 건수 | ~15,000건 | 22대 발의 법안 전체 |
| 처리완료 법안 | ~2,000건 | proc_result != null |

### 3.3 샘플링 전략

테스트용 100건 샘플링:

| 기준 | 방법 |
|------|------|
| 소관위별 균등 | 17개 상임위 × 6건 ≈ 100건 |
| 처리결과 다양성 | 원안가결, 대안반영, 철회 등 포함 |
| summary 존재 | summary 있는 법안만 선택 |

---

## 4. API 상세

### 4.1 열린국회정보 - 의안상세정보

**엔드포인트**
```
https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph
```

**파라미터**
| 파라미터 | 값 | 설명 |
|---------|-----|------|
| Key | {API_KEY} | 열린국회정보 API 키 |
| Type | json | 응답 형식 |
| pIndex | 1 | 페이지 번호 |
| pSize | 1000 | 페이지당 건수 |
| AGE | 22 | 22대 국회 |

**응답 필드 (25개)**
```
AGE, BILL_NO, BILL_NM, BILL_KIND, PROPOSER, COMMITTEE_NM,
PROC_RESULT_CD, VOTE_TCNT, YES_TCNT, NO_TCNT, BLANK_TCNT,
PROPOSE_DT, COMMITTEE_SUBMIT_DT, COMMITTEE_PRESENT_DT,
COMMITTEE_PROC_DT, LAW_SUBMIT_DT, LAW_PRESENT_DT, LAW_PROC_DT,
RGS_PRESENT_DT, RGS_PROC_DT, CURR_TRANS_DT, ANNOUNCE_DT,
BILL_ID, LINK_URL, CURR_COMMITTEE_ID
```

**PROC_RESULT_CD 값**
- 원안가결
- 수정가결
- 대안반영
- 철회
- 폐기
- 부결

### 4.2 공공데이터포털 - BillInfoService2

**엔드포인트**
```
http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList
```

**파라미터**
| 파라미터 | 값 | 설명 |
|---------|-----|------|
| ServiceKey | {API_KEY} | 공공데이터포털 API 키 |
| bill_kind_cd | B04 | 법률안 (summary 반환 필수!) |
| end_ord | 22 | 22대 국회까지 |
| ord | D01 | 최신순 정렬 |
| numOfRows | 100 | 페이지당 건수 |
| pageNo | 1 | 페이지 번호 |

**응답 필드 (8개)**
```
billId, billName, billNo, passGubn, procStageCd,
proposeDt, proposerKind, summary
```

---

## 5. 산출물

### 5.1 파일 목록

| 파일 | 설명 |
|------|------|
| `data/bills_raw_assembly.json` | Step 1 수집 결과 (의안상세정보) |
| `data/bills_raw_summary.json` | Step 2 수집 결과 (BillInfoService2) |
| `data/bills_merged.json` | 조인 완료 통합 데이터 |
| `data/bills_sample_100.json` | 테스트용 100건 샘플 |
| `data/golden_set_v2.json` | Golden Set (재선정) |

### 5.2 스크립트

| 파일 | 설명 |
|------|------|
| `src/collect_assembly_bills.py` | Step 1: 의안상세정보 수집 |
| `src/collect_summary.py` | Step 2: summary 수집 |
| `src/merge_bill_data.py` | Step 3: 데이터 조인 |
| `src/sample_bills.py` | 샘플링 스크립트 |

---

## 6. 검증 체크리스트

수집 완료 후 확인 사항:

- [ ] 전체 건수 확인 (예상: ~15,000건)
- [ ] committee 채워진 비율 ≥ 99%
- [ ] proc_result 채워진 비율 = 100%
- [ ] summary 채워진 비율 ≥ 95%
- [ ] 조인 누락 건수 확인 (bill_no 불일치)
- [ ] 샘플 100건 소관위 분포 확인

---

## 7. 일정

| 단계 | 작업 | 예상 소요 |
|------|------|----------|
| 1 | 의안상세정보 수집 | API 호출 ~15회 |
| 2 | summary 수집 | API 호출 ~150회 |
| 3 | 데이터 조인 | 즉시 |
| 4 | 샘플링 + 검증 | 즉시 |
| 5 | Golden Set 재선정 | 수동 작업 |

---

*Generated: 2026-01-15*
