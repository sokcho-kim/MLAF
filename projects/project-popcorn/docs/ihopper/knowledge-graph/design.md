# 지식그래프 설계 문서

> **버전:** v0.2
> **작성일:** 2026-01-20
> **수정일:** 2026-01-22 (Phase 0 검증 결과 반영)

---

## 1. 개요

### 1.1 목적

Cross-Domain Radar의 유사도 기반 탐지를 **지식그래프로 보완**하여:
- 관계 기반 탐지 (설명 가능)
- False Positive/Negative 감소
- 간접 연결 탐지

### 1.2 하이브리드 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cross-Domain Radar v2                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [신규 법안] ──┬──→ [1차] 유사도 스크리닝 ──→ 후보 법안        │
│               │         (현재 방식)           (Top N)           │
│               │                                  │              │
│               │                                  ▼              │
│               │         [2차] 지식그래프 검증 ←─┘              │
│               │              │                                  │
│               │              ├─→ 관계 경로 탐색                 │
│               │              ├─→ 소관 부처 확인                 │
│               │              └─→ 연관 법률 확인                 │
│               │                      │                          │
│               │                      ▼                          │
│               └───────────→ [최종] 스코어 산출                  │
│                                      │                          │
│                             final_score =                       │
│                               sim_score × 0.4                   │
│                             + kg_score  × 0.4                   │
│                             + keyword   × 0.2                   │
│                                      │                          │
│                                      ▼                          │
│                              [알림/리포트]                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 엔티티 (Nodes)

### 2.1 핵심 엔티티

| 엔티티 | 설명 | 속성 | 소스 |
|--------|------|------|------|
| **Bill** | 의안 | bill_id, title, propose_dt, status | ods_core.bill |
| **Member** | 국회의원 | member_id, name, party, district | ods_core.member |
| **Committee** | 위원회 | cmte_id, name, type | ods_core.committee |
| **Law** | 현행 법률 | law_id, name, ministry | 법제처 API |
| **Article** | 법률 조문 | article_id, number, content | 법제처 API |
| **Ministry** | 정부 부처 | ministry_id, name, rr_text | 수동/설정 |

### 2.2 엔티티 상세

```yaml
# Bill (의안)
Bill:
  id: bill_id (PK)
  properties:
    - title: string
    - propose_dt: date
    - bill_type: enum [법률안, 결의안, 동의안, ...]
    - status: enum [접수, 심사, 통과, 폐기, ...]
    - proposer_type: enum [의원, 정부, 위원장]

# Member (국회의원)
Member:
  id: member_id (PK)
  properties:
    - name: string
    - party: string
    - district: string
    - elected_count: int

# Committee (위원회)
Committee:
  id: cmte_id (PK)
  properties:
    - name: string
    - type: enum [상임위, 특별위]

# Law (법률)
Law:
  id: law_id (PK)
  properties:
    - name: string
    - law_type: enum [법률, 시행령, 시행규칙]
    - enacted_dt: date
    - last_amended_dt: date

# Article (조문)
Article:
  id: article_id (PK)
  properties:
    - law_id: FK
    - article_no: string (제1조, 제2조의2, ...)
    - title: string
    - content: text

# Ministry (부처)
Ministry:
  id: ministry_id (PK)
  properties:
    - name: string
    - english_name: string
    - rr_text: text (역할 및 책임)
    - keywords: list[string]
```

---

## 3. 관계 (Edges)

### 3.1 관계 정의

| 관계 | From | To | 속성 | 설명 |
|------|------|-----|------|------|
| **PROPOSED_BY** | Bill | Member | role (대표/공동) | 의원이 법안 발의 |
| **REFERRED_TO** | Bill | Committee | referred_dt | 법안이 위원회 회부 |
| **AMENDS** | Bill | Law | - | 법안이 법률 개정 |
| **CREATES** | Bill | Law | - | 법안이 법률 제정 |
| **ABOLISHES** | Bill | Law | - | 법안이 법률 폐지 |
| **REFERENCES** | Bill | Article | - | 법안이 조문 참조 |
| **BELONGS_TO** | Member | Committee | role, period | 의원 위원회 소속 |
| **CONTAINS** | Law | Article | - | 법률이 조문 포함 |
| **GOVERNED_BY** | Law | Ministry | type (주관/협조) | 법률 소관 부처 |
| **RELATED_TO** | Law | Law | type (상위/참조) | 법률 간 관계 |
| **SUPERSEDES** | Bill | Bill | - | 대안반영 폐기 |

### 3.2 관계 다이어그램

```
                          ┌──────────┐
                          │ Ministry │
                          └────┬─────┘
                               │ GOVERNED_BY
                               ▼
┌────────┐  PROPOSED_BY  ┌─────────┐  AMENDS   ┌─────┐  CONTAINS  ┌─────────┐
│ Member │──────────────→│  Bill   │──────────→│ Law │───────────→│ Article │
└────┬───┘               └────┬────┘           └──┬──┘            └─────────┘
     │                        │                   │
     │ BELONGS_TO             │ REFERRED_TO       │ RELATED_TO
     ▼                        ▼                   ▼
┌───────────┐           ┌───────────┐         ┌─────┐
│ Committee │           │ Committee │         │ Law │
└───────────┘           └───────────┘         └─────┘
```

---

## 4. 그래프 쿼리 예시

### 4.1 법안 → 소관 부처 탐색

```cypher
// 법안이 개정하는 법률의 소관 부처 찾기
MATCH (b:Bill {bill_id: $bill_id})-[:AMENDS]->(l:Law)-[:GOVERNED_BY]->(m:Ministry)
RETURN m.name as ministry, l.name as law

// 결과 예시:
// ministry: 산업통상자원부, law: 에너지법
```

### 4.2 법안 → 관련 위원회 탐색

```cypher
// 법안 제안자의 소속 위원회 찾기
MATCH (b:Bill {bill_id: $bill_id})<-[:PROPOSED_BY]-(m:Member)-[:BELONGS_TO]->(c:Committee)
RETURN c.name as committee, count(m) as proposer_count
ORDER BY proposer_count DESC
```

### 4.3 부처 관련 법안 역추적

```cypher
// 특정 부처 소관 법률을 개정하는 법안 찾기
MATCH (ministry:Ministry {name: "산업통상자원부"})
      <-[:GOVERNED_BY]-(l:Law)
      <-[:AMENDS]-(b:Bill)
WHERE b.propose_dt >= date("2026-01-01")
RETURN b.bill_id, b.title, l.name as target_law
```

### 4.4 간접 연결 탐색 (2홉)

```cypher
// 법안이 개정하는 법률과 관련된 다른 법률의 소관 부처
MATCH (b:Bill {bill_id: $bill_id})-[:AMENDS]->(l1:Law)-[:RELATED_TO]->(l2:Law)-[:GOVERNED_BY]->(m:Ministry)
RETURN DISTINCT m.name as indirect_ministry, l2.name as related_law
```

---

## 5. KG 스코어 산출

### 5.1 스코어 요소

| 요소 | 가중치 | 설명 |
|------|--------|------|
| **직접 소관** | 1.0 | 법안 → 법률 → 부처 (1홉) |
| **간접 소관** | 0.5 | 법안 → 법률 → 관련법률 → 부처 (2홉) |
| **위원회 관할** | 0.3 | 회부 위원회가 부처 관할 |
| **발의자 전문성** | 0.2 | 대표발의자가 관련 위원회 소속 |

### 5.2 KG 스코어 계산

```python
def calculate_kg_score(bill_id: str, ministry: str) -> float:
    """지식그래프 기반 스코어 계산"""
    score = 0.0

    # 1. 직접 소관 (법안 → 법률 → 부처)
    direct_laws = query_direct_governed_laws(bill_id, ministry)
    if direct_laws:
        score += 1.0 * len(direct_laws)

    # 2. 간접 소관 (2홉)
    indirect_laws = query_indirect_governed_laws(bill_id, ministry)
    if indirect_laws:
        score += 0.5 * len(indirect_laws)

    # 3. 위원회 관할
    if is_referred_to_related_committee(bill_id, ministry):
        score += 0.3

    # 4. 발의자 전문성
    if has_expert_proposer(bill_id, ministry):
        score += 0.2

    # 정규화 (0~1)
    return min(score / 2.0, 1.0)
```

### 5.3 최종 스코어 (하이브리드)

```python
def calculate_hybrid_score(bill, ministry) -> float:
    """하이브리드 스코어 계산"""

    # 1차: 유사도 (현재 방식)
    sim_score = calculate_similarity(bill, ministry.rr_vector)

    # 2차: 지식그래프
    kg_score = calculate_kg_score(bill.bill_id, ministry.name)

    # 키워드 가산점
    keyword_score = calculate_keyword_bonus(bill, ministry.keywords)

    # 가중 합산
    final_score = (
        sim_score    * 0.4 +
        kg_score     * 0.4 +
        keyword_score * 0.2
    )

    return final_score
```

---

## 6. 데이터 현황 분석 (2026-01-20)

### 6.1 보유 데이터

| 데이터 | 파일 | 건수 | 용도 |
|--------|------|------|------|
| 법안 | `bills_merged.json` | 1,021건 | Bill 노드 |
| 법률-부처 매핑 | `ministry_laws.json` | 21개 부처, ~2,000법률 | Law-Ministry 관계 |
| 부처 R&R | `ministry_rr_augmented.json` | 21개 부처 | Ministry 노드 |

### 6.2 법안-법률 매핑 가능성 검증

**법안 제목에서 법률명 추출 테스트 결과:**

```
전체: 1,021건
├── 일부/전부개정: 955건 (93.5%) → 법률명 추출 가능
└── 신규 제정: 66건 (6.5%) → 기존 법률 없음 (매핑 불필요)
```

**추출 정규식:**
```python
pattern = r'^(.+(?:법률|법))\s*(일부|전부)?개정법률안'
# 예: "에너지법 일부개정법률안" → "에너지법"
```

**추출 성공률: 92.2%** (941/1,021건)

실패 케이스는 대부분 신규 제정 법안 (기존 법률 참조 없음)

### 6.3 프로토타입 범위 (MVP)

**포함:**
- Bill → Law (AMENDS 관계)
- Law → Ministry (GOVERNED_BY 관계)

**제외 (추후):**
- Member, Committee (ihopper 연동 필요)
- Article (조문 파싱 복잡)
- Law → Law (관련 법률)

---

## 7. 구현 계획 (Concrete)

### Phase 0: 프로토타입 ✅ 완료 (2026-01-22)

**목표:** NetworkX로 MVP 검증

| 단계 | 작업 | 산출물 | 상태 |
|------|------|--------|------|
| 0-1 | 법률명 추출 함수 | `extract_law_name()` | ✅ |
| 0-2 | 법률-부처 매핑 로드 | `load_ministry_laws()` | ✅ |
| 0-3 | NetworkX 그래프 구축 | `build_knowledge_graph()` | ✅ |
| 0-4 | KG 스코어 계산 | `calculate_kg_score()` | ✅ |
| 0-5 | 전체 분석 | `analyze_bills()` | ✅ |

**코드 위치:** `src/kg_prototype.py`

### Phase 1: 검증 및 개선 ← **현재**

- [ ] Golden Set으로 정확도 비교
- [ ] 하이브리드 스코어 적용 테스트
- [ ] False Positive/Negative 분석
- [ ] 가중치 튜닝 (sim/kg/keyword 비율)

### Phase 2: 확장 (ihopper 연동 후)

- [ ] Member-Committee 관계 추가
- [ ] 2홉 탐색 (간접 소관)
- [ ] 그래프 DB 마이그레이션 검토

---

## 8. 기술 스택

### 프로토타입 (Phase 0)

| 항목 | 선택 | 이유 |
|------|------|------|
| 그래프 라이브러리 | **NetworkX** | 설치 쉬움, 1,021건 충분 |
| 데이터 저장 | JSON 파일 | 별도 DB 불필요 |
| 언어 | Python | 기존 코드와 통합 |

### 운영 (Phase 2 이후)

| 옵션 | 장점 | 단점 |
|------|------|------|
| **Neo4j** | Cypher 쿼리, 시각화, 성숙도 | 비용 (Enterprise), 리소스 |
| **PostgreSQL + Apache AGE** | 기존 인프라 활용, 무료 | 성숙도, 기능 제한 |
| **Amazon Neptune** | 관리형, 확장성 | AWS 종속, 비용 |

**결정:** 프로토타입 검증 후 선택

---

## 9. 예상 효과

| 지표 | Before (유사도) | After (하이브리드) |
|------|-----------------|-------------------|
| 탄소중립기본법 감지 | ❌ (0.441) | ✅ (KG 경로 존재) |
| False Positive | 높음 | 감소 (관계 검증) |
| 설명 가능성 | 낮음 | 높음 (경로 제시) |
| 간접 영향 탐지 | 불가 | 가능 (2홉 탐색) |

---

## 10. Phase 0 검증 결과 (2026-01-22)

### 10.1 핵심 지표

| 지표 | 결과 | 비고 |
|------|------|------|
| 총 법안 | 1,021건 | `bills_merged.json` |
| 법률명 추출 성공 | 941건 (92.2%) | 정규식 기반 |
| KG 경로 확인 | 731건 (71.6%) | Bill → Law → Ministry |

### 10.2 법안 유형별 분포

```
일부개정: 951건 (93.1%)
기타:      42건 (4.1%)
제정:      22건 (2.2%)
전부개정:   4건 (0.4%)
폐지:       2건 (0.2%)
```

### 10.3 부처별 KG 매칭

| 순위 | 부처 | 소관 법안 |
|------|------|----------|
| 1 | 보건복지부 | 104건 |
| 2 | 국토교통부 | 92건 |
| 3 | 문화체육관광부 | 65건 |
| 4 | 교육부 | 54건 |
| 5 | 재정경제부 | 52건 |
| 6 | 산업통상부 | 51건 |
| 7 | 법무부 | 48건 |
| 8 | 해양수산부 | 48건 |
| 9 | 기후에너지환경부 | 43건 |
| 10 | 행정안전부 | 42건 |

### 10.4 확인된 KG 강점

1. **설명 가능성**
   - 경로 제시: `법안 → 산업 디지털 전환 촉진법 → 산업통상부`
   - 왜 관련 있는지 명확하게 설명 가능

2. **정확한 소관 파악**
   - 예: 탄소중립기본법 → 기후에너지환경부 (산업통상부 아님)
   - 법적 소관 관계 기반 정확한 판단

3. **Binary 판단**
   - 경로 있음 = 1.0, 없음 = 0.0
   - 유사도의 모호함 제거

### 10.5 매칭 실패 원인 분석 (290건)

| 원인 | 예시 |
|------|------|
| 신규 제정 법안 | "인공지능 발전과 신뢰 기반 조성 등에 관한 기본법" |
| `ministry_laws.json` 누락 | "항공·철도 사고조사에 관한 법률" |
| 특수문자 불일치 | `·` vs 일반 문자 |
| 법률명 변경/통폐합 | 구법 → 신법 |

### 10.6 CLI 사용법

```bash
# 전체 분석
python3 src/kg_prototype.py --analyze

# 특정 법안 분석
python3 src/kg_prototype.py --bill <bill_id> --ministry 산업통상부
```

### 10.7 다음 단계 권장사항

1. **매칭률 개선 (71.6% → 85%+)**
   - `ministry_laws.json` 보완 (누락 법률 추가)
   - 특수문자 정규화 강화
   - Fuzzy 매칭 알고리즘 개선

2. **하이브리드 스코어 테스트**
   - Golden Set 구축 (정답 레이블)
   - 유사도 vs KG vs 하이브리드 비교
   - 최적 가중치 탐색

3. **간접 소관 탐지 (Phase 2)**
   - 2홉 탐색: Bill → Law → Related Law → Ministry
   - 탄소중립기본법 → 에너지법 → 산업통상부 케이스 해결

---

*Last updated: 2026-01-22*
