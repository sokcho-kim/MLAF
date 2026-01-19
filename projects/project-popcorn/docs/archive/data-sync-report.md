# API 데이터 현황 리포트

**작성일**: 2026-01-15
**목적**: 공공데이터포털 / 열린국회정보 API별 제공 필드 비교 및 데이터 품질 분석

---

## 1. 핵심 요약

### 발견된 문제점

| 문제 | 상세 |
|-----|------|
| **PROC_RESULT 누락** | 국회의원발의법률안 API의 PROC_RESULT가 모두 null (0%) |
| **데이터 소스 분리** | summary는 공공데이터포털, committee는 열린국회정보에서만 제공 |
| **API 간 조인 미완성** | bill_no로 조인 가능하나 현재 데이터에 반영 안됨 |

### 해결 방안

| 필드 | 사용할 API |
|-----|-----------|
| summary (제안이유) | 공공데이터포털 `BillInfoService2` (98%) |
| committee (소관위) | 열린국회정보 `의안상세정보` (99%) |
| proc_result (처리결과) | 열린국회정보 `의안상세정보` (100%) |
| vote_info (투표정보) | 열린국회정보 `의안상세정보` (92%) |

---

## 2. API별 필드 비교

### 2.1 열린국회정보 - 국회의원발의법률안 (nzmimeepazxkubdpn)

**용도**: 법안 기본 목록 조회
**엔드포인트**: `https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn`

| 필드 | 설명 | 채워진 비율 |
|-----|------|------------|
| BILL_ID | 의안 ID | 100% |
| BILL_NO | 의안 번호 | 100% |
| BILL_NAME | 의안명 | 100% |
| COMMITTEE | 소관위원회 | **64%** |
| PROC_RESULT | 처리결과 | **0%** (전부 null) |
| PROPOSE_DT | 제안일자 | 100% |
| RST_PROPOSER | 대표발의자 | 100% |
| DETAIL_LINK | 상세 링크 | 100% |

**전체 필드 (22개)**:
```
BILL_ID, BILL_NO, BILL_NAME, COMMITTEE, PROPOSE_DT, PROC_RESULT,
AGE, DETAIL_LINK, PROPOSER, MEMBER_LIST, LAW_PROC_DT, LAW_PRESENT_DT,
LAW_SUBMIT_DT, CMT_PROC_RESULT_CD, CMT_PROC_DT, CMT_PRESENT_DT,
COMMITTEE_DT, PROC_DT, COMMITTEE_ID, PUBL_PROPOSER, LAW_PROC_RESULT_CD,
RST_PROPOSER
```

**결론**: COMMITTEE는 64%만 채워짐, PROC_RESULT는 모두 null로 **처리결과 조회에 부적합**

---

### 2.2 열린국회정보 - 의안상세정보 (nwbpacrgavhjryiph)

**용도**: 처리결과, 투표정보 조회
**엔드포인트**: `https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph`

| 필드 | 설명 | 채워진 비율 |
|-----|------|------------|
| BILL_NO | 의안 번호 | 100% |
| BILL_NM | 의안명 | 100% |
| COMMITTEE_NM | 소관위원회 | **99%** |
| PROC_RESULT_CD | 처리결과 | **100%** |
| VOTE_TCNT | 투표 총수 | **92%** |
| YES_TCNT | 찬성 | 92% |
| NO_TCNT | 반대 | 92% |
| BLANK_TCNT | 기권 | 92% |
| BILL_ID | 의안 ID | 100% |

**전체 필드 (25개)**:
```
AGE, BILL_NO, BILL_NM, BILL_KIND, PROPOSER, COMMITTEE_NM, PROC_RESULT_CD,
VOTE_TCNT, YES_TCNT, NO_TCNT, BLANK_TCNT, PROPOSE_DT, COMMITTEE_SUBMIT_DT,
COMMITTEE_PRESENT_DT, COMMITTEE_PROC_DT, LAW_SUBMIT_DT, LAW_PRESENT_DT,
LAW_PROC_DT, RGS_PRESENT_DT, RGS_PROC_DT, CURR_TRANS_DT, ANNOUNCE_DT,
BILL_ID, LINK_URL, CURR_COMMITTEE_ID
```

**처리결과(PROC_RESULT_CD) 값**:
- 철회
- 인가
- 대안반영
- 원안가결

**결론**: **처리결과와 소관위 정보 조회에 최적** (99-100% 채워짐)

---

### 2.3 공공데이터포털 - BillInfoService2

**용도**: 제안이유/주요내용(summary) 조회
**엔드포인트**: `http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList`
**필수 파라미터**: `bill_kind_cd=B04` (법률안)

| 필드 | 설명 | 채워진 비율 |
|-----|------|------------|
| billId | 의안 ID | 100% |
| billNo | 의안 번호 | 100% |
| billName | 의안명 | 100% |
| summary | 제안이유/주요내용 | **98%** |
| proposerKind | 제안자 종류 | 100% |
| procStageCd | 처리단계 | 100% |

**전체 필드 (8개)**:
```
billId, billName, billNo, passGubn, procStageCd, proposeDt, proposerKind, summary
```

**결론**: **summary 필드가 98% 채워짐** - 제안이유 수집에 최적
**주의**: committee(소관위) 필드 없음!

---

## 3. 현재 수집 데이터 현황

### 3.1 로컬 파일별 현황

| 파일 | 건수 | committee | proc_result | summary |
|------|------|-----------|-------------|---------|
| `test_bills.json` | 100 | 100% | **0%** | - |
| `test_bills_with_content.json` | 105 | 99% | **0%** | 70.5% |
| `golden_set.json` | 5 | 80% | - | - |
| `bill_summary_cache.json` | 2000 | - | - | 97.3% |

### 3.2 문제점 분석

1. **proc_result 전체 누락**
   - `test_bills.json`과 `test_bills_with_content.json` 모두 proc_result가 0%
   - 원인: 국회의원발의법률안 API에서 PROC_RESULT가 null로 반환됨
   - 해결: 의안상세정보 API로 교체 필요

2. **summary 매칭률 70.5%**
   - 105건 중 74건만 summary 수집됨
   - 원인: 공공데이터포털에서 20페이지(2000건)만 캐시했기 때문
   - 해결: 전체 페이지 수집 또는 bill_no 기반 직접 조회

3. **데이터 출처 혼재**
   - committee: 열린국회정보
   - summary: 공공데이터포털
   - bill_no 기준 조인이 정상적으로 수행되지 않음

---

## 4. 처리완료 법안 수집 가능 여부

### 결론: **가능** (의안상세정보 API 사용)

의안상세정보 API(`nwbpacrgavhjryiph`)에서 PROC_RESULT_CD가 100% 채워져 있으며, 다음 처리결과를 구분할 수 있음:

| PROC_RESULT_CD | 의미 |
|----------------|------|
| 원안가결 | 원안대로 통과 |
| 대안반영 | 대안에 반영되어 폐기 |
| 인가 | 인가 |
| 철회 | 발의자 철회 |

또한 투표정보(VOTE_TCNT, YES_TCNT, NO_TCNT)도 92% 제공되어 본회의 표결 결과 분석도 가능함.

---

## 5. 권장 데이터 수집 전략

### 5.1 최적 API 조합

```
┌─────────────────────────────────────────────────────────────┐
│                    데이터 수집 파이프라인                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [열린국회정보 - 의안상세정보]                                 │
│  └─ BILL_NO, COMMITTEE_NM, PROC_RESULT_CD, VOTE_*           │
│                                                              │
│  [공공데이터포털 - BillInfoService2]                          │
│  └─ billNo, summary                                          │
│                                                              │
│           ↓ bill_no 기준 조인                                │
│                                                              │
│  [최종 데이터셋]                                              │
│  └─ bill_no, bill_name, committee, proc_result,             │
│     vote_info, summary                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 조인 키

- **BILL_NO** (의안번호): 두 API 모두 100% 제공
- BILL_ID는 형식이 다를 수 있어 bill_no 사용 권장

### 5.3 수집 순서

1. 의안상세정보 API로 22대 국회 전체 법안 목록 수집
   - committee, proc_result, vote_info 확보
2. BillInfoService2로 summary 수집 (bill_kind_cd=B04)
3. bill_no 기준으로 조인

---

## 6. 참고: API 응답 샘플

### 열린국회정보 - 의안상세정보 샘플

```json
{
  "BILL_NO": "2216052",
  "BILL_NM": "영유아보육법 일부개정법률안",
  "COMMITTEE_NM": "보건복지위원회",
  "PROC_RESULT_CD": "대안반영",
  "VOTE_TCNT": "188",
  "YES_TCNT": "188",
  "NO_TCNT": "0",
  "BLANK_TCNT": "0"
}
```

### 공공데이터포털 - BillInfoService2 샘플

```xml
<item>
  <billNo>2216052</billNo>
  <billName>영유아보육법 일부개정법률안</billName>
  <summary>제안이유 및 주요내용: 영유아 보육 환경 개선을 위해...</summary>
</item>
```

---

*Generated: 2026-01-15*
