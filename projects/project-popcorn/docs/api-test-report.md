# API 연동 테스트 보고서

> 작성일: 2026-01-15
> 작성자: Claude Code

---

## 1. 테스트 개요

| 항목 | 내용 |
|------|------|
| 목적 | Project Popcorn 데이터 수집을 위한 API 연동 검증 |
| 대상 | 공공데이터포털, 열린국회정보 API |
| 환경 | Python 3.x, requests 라이브러리 |

---

## 2. 테스트 결과 요약

| API | 엔드포인트 | 결과 | 비고 |
|-----|-----------|------|------|
| 공공데이터포털 | data.go.kr | **실패** | 403 Forbidden |
| 열린국회정보 | open.assembly.go.kr | **성공** | 정상 동작 |

---

## 3. 공공데이터포털 API 테스트

### 3.1 테스트 정보

| 항목 | 내용 |
|------|------|
| 서비스명 | 국회 국회사무처_의안정보 통합 API |
| 서비스 ID | OOWY4R001216HX11440 |
| API 유형 | **LINK** (외부 링크) |
| 엔드포인트 | `http://apis.data.go.kr/9710000/BillInfoService2` |

### 3.2 테스트 결과

```
[ERROR] API 요청 실패: 403 Client Error: Forbidden
```

### 3.3 원인 분석

- 공공데이터포털의 국회 의안정보 API는 **LINK 타입**
- 실제 데이터는 열린국회정보(open.assembly.go.kr)에서 제공
- 공공데이터포털 API 키로는 직접 접근 불가
- 열린국회정보에서 별도 API 키 발급 필요

### 3.4 결론

`DATA_GO_KR_API_KEY`는 국회 의안 데이터 수집에 **사용 불가**. 열린국회정보 API 키 사용 권장.

---

## 4. 열린국회정보 API 테스트

### 4.1 테스트 정보

| 항목 | 내용 |
|------|------|
| 포털 | 열린국회정보 Open API |
| Base URL | `https://open.assembly.go.kr/portal/openapi` |
| 인증 방식 | API Key (Query Parameter) |
| 응답 형식 | JSON / XML |

### 4.2 테스트 API 목록

#### API 1: TVBPMBILL11 (의안검색)

| 항목 | 내용 |
|------|------|
| 엔드포인트 | `/TVBPMBILL11` |
| 용도 | 전체 의안 검색 |
| 필수 파라미터 | 없음 (AGE로 대수 필터 가능) |

**요청 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| Key | STRING | Y | 인증키 |
| Type | STRING | Y | 응답형식 (json/xml) |
| pIndex | INTEGER | Y | 페이지 번호 (기본값: 1) |
| pSize | INTEGER | Y | 페이지당 건수 (기본값: 100) |
| AGE | INTEGER | N | 대수 (20, 21, 22 등) |

**테스트 결과:**

```
[INFO] 전체 의안 수: 15,632건 (22대)
[INFO] 조회된 의안 수: 5건

[SAMPLE]
1. 장애아동복지법 일부개정법률안
   - 의안번호: 2216052
   - 의안ID: PRC_X2V5W1S2S1Q9R1P5O3O1W1X4V2W6U5
   - 제안자: 박성민의원 외 10인
```

**응답 필드:**

| 필드명 | 설명 |
|--------|------|
| BILL_NO | 의안번호 |
| BILL_ID | 의안 ID |
| BILL_NAME | 의안명 |
| PROPOSER | 제안자 |
| CURR_COMMITTEE | 소관위원회 |
| PROC_RESULT | 처리결과 |
| PROPOSE_DT | 제안일자 |

---

#### API 2: nzmimeepazxkubdpn (국회의원 발의법률안)

| 항목 | 내용 |
|------|------|
| 엔드포인트 | `/nzmimeepazxkubdpn` |
| 용도 | 국회의원 발의법률안 (대표/공동발의자 구분 가능) |
| 필수 파라미터 | AGE (대수) |

**테스트 결과:**

```
[INFO] 전체 발의법률안 수: 14,639건 (22대)

[SAMPLE]
1. 장애아동복지법 일부개정법률안
   - 대표발의자: 박성민
   - 공동발의자: 허영,박상수,이종성,이훈기,윤건만,문영호,최민희,이소영,윤우영
```

**응답 필드:**

| 필드명 | 설명 |
|--------|------|
| BILL_NAME | 의안명 |
| RST_PROPOSER | 대표발의자 |
| PUBL_PROPOSER | 공동발의자 목록 |
| PROPOSER_KIND | 제안자구분 |

---

## 5. API 비교 및 선택

| 구분 | TVBPMBILL11 | nzmimeepazxkubdpn |
|------|-------------|-------------------|
| 데이터 범위 | 전체 의안 (15,632건) | 발의법률안 (14,639건) |
| 대표/공동발의자 구분 | X | **O** |
| 소관위원회 | O | O |
| 필수 파라미터 | 없음 | AGE (대수) |

### 권장 사용 방식

1. **전체 의안 목록 수집**: `TVBPMBILL11` 사용
2. **발의자 상세 정보 필요 시**: `nzmimeepazxkubdpn` 사용
3. **Cross-Domain 리스크 감지**: 두 API 병행 사용

---

## 6. 구현 산출물

| 파일 | 설명 |
|------|------|
| `src/ingest_base.py` | Track 1 수집기 (열린국회정보 API 연동) |

### 주요 함수

```python
# 의안목록 조회
get_bill_list(age=22, p_index=1, p_size=10) -> dict

# 국회의원 발의법률안 조회
get_proposer_bills(age=22, p_index=1, p_size=10) -> dict

# 데이터 저장
save_bills(bills, age, api_name) -> None
```

---

## 7. 다음 단계

- [ ] Solar Embedding 테스트 (부처 R&R 벡터화)
- [ ] Qdrant Docker 실행 및 컬렉션 생성
- [ ] 과거 법안 데이터 전체 수집 (20~22대)

---

## 8. 참고 자료

- [열린국회정보 Open API 포털](https://open.assembly.go.kr/portal/openapi/main.do)
- [공공데이터포털 의안정보 통합 API](https://www.data.go.kr/data/15126134/openapi.do)
- [OpenAPI 의안 관련 사용 참고 문서](https://velog.io/@assembly101/OpenAPI-의안-관련-사용-참고-문서-작성-진행중)
