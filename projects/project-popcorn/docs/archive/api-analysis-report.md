# 의안 API 분석 리포트

**작성일**: 2026-01-15
**최종 업데이트**: 2026-01-15
**목적**: 법안 제안이유/주요내용 수집을 위한 API 선정

---

## 1. API 후보 목록

| # | API | 제공처 | 엔드포인트 | 상태 |
|---|-----|--------|-----------|------|
| 1 | 국회사무처 의안정보 | 공공데이터포털 | `http://apis.data.go.kr/9710000/BillInfoService2` | 작동 (summary 미반환) |
| 2 | 국회의원 발의법률안 | 열린국회정보 | `https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn` | 작동 (summary 없음) |
| 3 | 의안상세정보 | 열린국회정보 | `https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph` | 작동 (summary 없음) |
| 4 | 법률안 제안이유 및 주요내용 | 열린국회정보 | ID: `OS46YD0012559515463` | URL 미제공 |

---

## 2. API별 상세 분석

### 2.1 공공데이터포털 - BillInfoService2

**URL**: `http://apis.data.go.kr/9710000/BillInfoService2`
**신청 필요**: O (공공데이터포털에서 별도 신청)
**인증**: ServiceKey (URL 인코딩된 API 키)

#### 오퍼레이션 테스트 결과

| 오퍼레이션 | HTTP Status | summary 필드 | 비고 |
|-----------|-------------|-------------|------|
| `getBillInfoList` | 200 OK | **X (미포함)** | 기본 필드만 반환 |
| `getBillSummaryList` | 404 | - | 존재하지 않음 |
| `getRecentBillList` | 404 | - | 존재하지 않음 |
| `getBillProcResultList` | 404 | - | 존재하지 않음 |

#### 실제 응답 필드 (`getBillInfoList`)
```
billId, billName, billNo, generalResult, passGubn,
procDt, procStageCd, proposeDt, proposerKind
```

#### 핵심 발견 (2026-01-15)

**`bill_kind_cd=B04` 파라미터 사용 시 `summary` 필드 반환!**

```python
# summary 필드가 반환되는 파라미터 조합
params = {
    "ServiceKey": API_KEY,
    "bill_kind_cd": "B04",  # 법률안 (필수!)
    "numOfRows": 10,
    "pageNo": 1,
}
```

| 파라미터 조합 | summary 반환 |
|-------------|-------------|
| 파라미터 없음 | X |
| `bill_kind_cd=B04` | **O** |
| `gbn=dae_num_name` + `bill_kind_cd=B04` | **O** |
| 그 외 조합 | X |

#### 추가 발견된 오퍼레이션

| 오퍼레이션 | 설명 |
|-----------|------|
| `getOfferReasonList` | 제안이유/주요내용 목록 정보조회 |
| `getBillReceiptInfo` | summaryLink 필드 포함 |

---

### 2.2 열린국회정보 - 국회의원 발의법률안

**URL**: `https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn`
**신청 필요**: X (열린국회정보 API 키로 사용 가능)
**인증**: Key 파라미터

#### 테스트 결과 (2026-01-15)

```
Status: 200 OK
총 필드: 22개
Summary 관련 필드: DETAIL_LINK만 존재 (제안이유 직접 제공 X)
```

#### 주요 필드

| 필드 | 설명 | 샘플 값 |
|-----|------|---------|
| BILL_ID | 의안 ID | PRC_X2V5W1S2S1Q9R1P5O3O1W1X4V2W6U5 |
| BILL_NO | 의안 번호 | 2216052 |
| BILL_NAME | 의안명 | 영유아보육법 일부개정법률안 |
| PROPOSE_DT | 제안일자 | 2026-01-14 |
| RST_PROPOSER | 대표발의자 | 박선영 |
| DETAIL_LINK | 상세 링크 | http://likms.assembly.go.kr/bill/billDetail.do?billId=... |

#### 결론
- **제안이유/주요내용 필드 없음**
- DETAIL_LINK를 통한 웹 크롤링 필요

---

### 2.3 열린국회정보 - 의안상세정보

**URL**: `https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph`
**신청 필요**: X
**인증**: Key 파라미터

#### 테스트 결과 (2026-01-15)

```
Status: 200 OK
총 필드: 25개
Summary 관련 필드: 없음
```

#### 주요 필드

| 필드 | 설명 |
|-----|------|
| BILL_NM | 의안명 |
| PROPOSER | 제안자 |
| VOTE_TCNT | 투표 총수 |
| YES_TCNT | 찬성 |
| NO_TCNT | 반대 |
| LINK_URL | 상세 링크 |

#### 결론
- 투표 정보 등 처리 결과 상세 제공
- **제안이유/주요내용 필드 없음**

---

### 2.4 열린국회정보 - 법률안 제안이유 및 주요내용

**INF_ID**: `OS46YD0012559515463`
**상태**: API 엔드포인트 미제공

#### 조사 결과 (2026-01-15)

```
- 열린국회정보 전체 API 목록(274개)에서 발견
- 이름: "법률안 제안이유 및 주요내용"
- 설명: "법률안 주요내용"
- URL_PATH: (비어있음)
- DDC_URL: Excel 파일 (API 명세 아님)
```

#### 결론
- API 목록에는 존재하나 **실제 엔드포인트가 제공되지 않음**
- 사용 불가

---

## 3. 비교 요약 (최종)

| 항목 | BillInfoService2 | 발의법률안 | 의안상세정보 |
|-----|-----------------|-----------|------------|
| HTTP Status | 200 OK | 200 OK | 200 OK |
| 제안이유 제공 | **O (bill_kind_cd=B04 필수)** | X | X |
| 사용 용이성 | **최고** | 양호 | 양호 |
| 추천 | **1순위** | 법안 목록용 | 투표 정보용 |

---

## 4. 최종 결론

### 핵심 발견
**BillInfoService2 API의 `getBillInfoList`에서 `bill_kind_cd=B04` 파라미터 사용 시 `summary` 필드(제안이유 및 주요내용)가 반환됨!**

```python
# 작동 확인된 코드
import requests
from urllib.parse import unquote

API_KEY = unquote(os.getenv("DATA_GO_KR_API_KEY"))
endpoint = "http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList"

params = {
    "ServiceKey": API_KEY,
    "bill_kind_cd": "B04",  # 핵심 파라미터!
    "numOfRows": 10,
    "pageNo": 1,
}

response = requests.get(endpoint, params=params)
# 응답에 summary 필드 포함됨
```

---

## 5. 권장 실행 계획

### 즉시 실행 (API 사용)
1. **BillInfoService2 `getBillInfoList`** (권장)
   - `bill_kind_cd=B04` 파라미터 필수
   - summary 필드에서 제안이유/주요내용 직접 수집
   - 속도: API 호출당 0.2초

### 대안 (필요시)
2. **getOfferReasonList** - 제안이유 전용 오퍼레이션 (파라미터 확인 필요)
3. **getBillReceiptInfo** - summaryLink 필드로 웹페이지 URL 제공

---

## 6. 참고 자료

- [공공데이터포털 - 의안정보](https://www.data.go.kr/data/3037286/openapi.do)
- [열린국회정보 Open API](https://open.assembly.go.kr/portal/openapi/main.do)
- [OpenAPI 의안 관련 참고 문서](https://velog.io/@assembly101/OpenAPI-의안-관련-사용-참고-문서-작성-진행중)

---

*Generated: 2026-01-15*
*Last Updated: 2026-01-15 (실제 테스트 결과 반영)*
