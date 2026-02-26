# Phase 1: AST + NLI 기반 법안 충돌 탐지 계획 v1

> **버전:** v1
> **작성일시:** 2026-02-15 14:00
> **이전 버전:** 없음 (신규)
> **변경사항:**
> - 코사인 유사도 방식 → AST+NLI 방식으로 전면 전환
> - 엣지케이스 방어 2건 반영 (조문 단위 추출, Golden Set 확장)

---

## 1. 배경: 왜 코사인 유사도를 버리는가

### 1.1 현행 방식의 한계

| 문제 | 설명 | 실제 사례 |
|------|------|-----------|
| **주제 유사 ≠ 영향** | 비슷한 단어가 나오면 관련으로 판단 | 환경부 법안에 "에너지" 단어 → 산업부 관련? |
| **FP 과다** | 범용형 부처(행정안전부 75.2%) 감지율 폭발 | 대부분 법안이 "행정" 단어 포함 |
| **논리 충돌 무시** | "허가 vs 금지" 같은 실질적 충돌을 못 잡음 | 같은 주제인데 정반대 규제 방향 |
| **설명 불가** | "0.47점" → 왜? | VC 보고 시 납득 불가 |

### 1.2 새 접근: AST + NLI

**핵심 아이디어:** "텍스트가 비슷한가?" → "논리 구조가 충돌하는가?"

```
기존 법률 조문                    신규 법안
────────────────────         ────────────────────
제4조(에너지 공급)              개정안 제4조
"에너지 사업자는 장관의         "에너지 사업자는 신고만으로
 인가를 받아야 한다"             사업을 개시할 수 있다"

        ↓ AST 파싱                     ↓ AST 파싱

Subject: 에너지 사업자           Subject: 에너지 사업자
Condition: 에너지 공급 시        Condition: 사업 개시 시
Action: 장관 인가 필요(의무)     Action: 신고만으로 가능(허용)
Exception: N/A                  Exception: N/A

        ↓ NLI 비교 ─────────────────────↓

        Action 충돌: 인가(의무) vs 신고(허용)
        → Contradiction Score: 0.85
        → "산업부 소관 에너지법 제4조와 논리적 충돌"
```

---

## 2. 새 파이프라인 아키텍처

```
┌──────────────────────────────────────────────────────────────────────┐
│                 Cross-Domain Radar v3 (AST + NLI)                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [신규 법안 1,021건]                                                  │
│       │                                                              │
│       ▼                                                              │
│  ① KG 프리필터 (kg_prototype.py)                                     │
│     법안 제목 → 법률명 추출 → 소관 부처 매핑                            │
│     "탄소중립기본법 일부개정 → 기후에너지환경부 소관"                     │
│       │                                                              │
│       │  관련 쌍만 추림 (~731건, 71.6%)                                │
│       ▼                                                              │
│  ② 조문 단위 추출 (법제처 API)                ◄── 엣지케이스 #1        │
│     법안이 개정하는 특정 조(제4조, 제12조)만 발췌                       │
│     전체 법률 텍스트 X → 해당 조문 텍스트만                             │
│       │                                                              │
│       ▼                                                              │
│  ③ AST 파싱 (LLM)                                                    │
│     기존 조문 → {Subject, Condition, Action, Exception}               │
│     신규 법안 → {Subject, Condition, Action, Exception}               │
│       │                                                              │
│       ▼                                                              │
│  ④ NLI 평가 (LLM)                                                    │
│     노드별 교차비교 → Entailment / Contradiction / Neutral            │
│       │                                                              │
│       ▼                                                              │
│  ⑤ Alert 생성                                                        │
│     Contradiction ≥ 0.6 → 타 부처 영향 플래그                         │
│     + reasoning으로 "왜 충돌인지" 설명                                 │
│       │                                                              │
│       ▼                                                              │
│  [Teams/이메일 알림]                                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.1 KG의 역할 변화

| | Phase 0 (이전) | Phase 1 (현재) |
|---|---|---|
| **역할** | 스코어링 (점수 매기기) | **프리필터** (비교 대상 좁히기) |
| **출력** | KG Score 0.0~1.0 | 법안-법률 쌍 리스트 |
| **가치** | 유사도에 합산 | LLM 비용 90%+ 절감 |

---

## 3. 태스크 계획

### 3.1 의존관계 다이어그램

```
#7 법률 본문 수집 (법제처 API)
  │   조문(Article) 단위 추출 ◄── 엣지케이스 #1
  ▼
#8 AST 파서 모듈 구현 (LLM)
  │
  ▼
#9 NLI 평가 모듈 구현
  │
  ▼
#10 파일럿 테스트 (Golden 5건)
  │
  ▼
#13 Golden Set 확장 (5→30건) ◄── 엣지케이스 #2
  │
  ▼
#11 프롬프트 튜닝 & 비용 최적화
  │
  ▼
#12 통합 파이프라인 (KG→AST→NLI)
```

### 3.2 태스크 상세

---

#### Task #7: 기존 법률 본문 수집 (법제처 API)

**목표:** 산업통상부 소관 법률의 조문 텍스트를 법제처 API로 수집

**핵심 산출물:** `data/law_texts/산업통상부_laws.json`

**작업 내용:**
1. `ministry_laws.json`에서 산업통상부 소관 법률 목록 추출
2. `moleg_api.py`의 `fetch_law_detail()` 활용하여 조문 수집
3. 조/항/호/목 구조를 유지하며 JSON 저장
4. 수집 실패 건 로깅 및 재시도

**비용:** 무료 (법제처 Open API)

##### 엣지케이스 #1: 조문(Article) 단위 추출

> **위험:** 법제처 API로 기존 법률 본문을 가져올 때, '건축법'이나 '탄소중립기본법'
> 전체를 그대로 LLM에 던지면 컨텍스트 윈도우가 터지거나 토큰 비용이 폭발한다.
> 또한 LLM이 너무 많은 정보 속에서 길을 잃어 환각(Hallucination)을 일으킬 수 있다.

> **보완:** 신규 법안이 개정/제정하고자 하는 **특정 조(예: 제4조, 제12조)**만
> 정규식이나 형태소 분석으로 발췌하여, 해당 조문 텍스트만 AST 파서(Task #8)에
> 넘기도록 코드를 정교하게 구현한다.

**구체적 구현 방향:**

```python
# 신규 법안 요약에서 개정 대상 조문 번호 추출
def extract_target_articles(bill_summary: str) -> list[str]:
    """
    "현행 제4조제1항 및 제12조를 다음과 같이 개정한다"
    → ["제4조", "제12조"]
    """
    pattern = r'제\d+조(?:의\d+)?'
    return re.findall(pattern, bill_summary)

# 법률 전체가 아닌, 해당 조문만 추출
def get_relevant_articles(law_articles: list, target_articles: list) -> list:
    """전체 법률 → 개정 대상 조문만 필터링"""
    return [a for a in law_articles if a['article_no'] in target_articles]
```

**저장 구조:**
```json
{
  "law_name": "에너지법",
  "law_id": "MST_00001234",
  "total_articles": 45,
  "articles": [
    {
      "article_no": "제4조",
      "title": "에너지 공급",
      "content": "① 에너지 사업자는 ...",
      "paragraphs": [
        {"para_no": "①", "content": "..."},
        {"para_no": "②", "content": "..."}
      ]
    }
  ]
}
```

---

#### Task #8: AST 파서 모듈 구현 (LLM 기반)

**목표:** 법률/법안 텍스트 → AST(Subject, Condition, Action, Exception) 분해

**핵심 산출물:** `src/ast_parser.py`, `data/cache/ast_cache.json`

**AST 노드 정의:**
| 노드 | 설명 | 예시 |
|------|------|------|
| Subject | 적용 주체 | "에너지 사업자", "산업통상자원부장관" |
| Condition | 발동 조건 | "에너지를 공급하려는 경우" |
| Action | 의무/금지/허용 | "인가를 받아야 한다(의무)", "신고만으로 가능(허용)" |
| Exception | 예외 조항 | "대통령령으로 정하는 경우는 제외" |

**LLM 프롬프트 (System):**
```
당신은 법률 데이터 엔지니어입니다.
주어진 법률 조문을 아래 4가지 AST 노드로 분해하세요.
명시되지 않은 정보는 "Not Specified"로 기재합니다.

출력 형식 (JSON):
{
  "subject": "적용 주체",
  "condition": "발동 조건",
  "action": "의무/금지/허용 행위",
  "exception": "예외 조항"
}
```

**캐싱 전략:**
- 기존 법률 조문은 변하지 않으므로 1회 파싱 후 캐시
- 캐시 키: `{law_id}_{article_no}` → AST JSON
- 신규 법안만 매번 파싱

**비용 추산 (GPT-4o-mini 기준):**
- 입력: 조문 평균 ~200토큰 + 프롬프트 ~300토큰
- 출력: AST JSON ~150토큰
- 단가: ~$0.0001/건
- 산업부 법률 전체 초기 파싱: ~$0.5 (1회성)

---

#### Task #9: NLI 평가 모듈 구현

**목표:** 두 AST를 비교하여 Entailment/Contradiction/Neutral 스코어 산출

**핵심 산출물:** `src/nli_evaluator.py`

**NLI 출력 스펙:**
```json
{
  "existing_law_AST": {"subject": "", "condition": "", "action": "", "exception": ""},
  "new_bill_AST": {"subject": "", "condition": "", "action": "", "exception": ""},
  "nli_analysis": {
    "entailment_score": 0.15,
    "contradiction_score": 0.75,
    "neutral_score": 0.10
  },
  "reasoning": "기존법은 인가를 의무화하나, 개정안은 신고제로 전환하여 Action 노드가 정반대. Subject와 Condition은 동일하므로 직접적 충돌."
}
```

**비교 로직:**
```
Subject vs Subject   → 동일 주체인가? (범위 포함/배제)
Condition vs Condition → 같은 상황인가? (범위 겹침)
Action vs Action     → 핵심! 허가↔금지, 의무↔면제 등 충돌?
Exception vs Exception → 예외 범위가 역전되는가?
```

**Contradiction 판단 기준:**
| 점수 | 의미 | 액션 |
|------|------|------|
| 0.0~0.3 | Neutral (무관) | 무시 |
| 0.3~0.6 | 약한 연관 | 참고 |
| 0.6~0.8 | 충돌 의심 | Alert (MEDIUM) |
| 0.8~1.0 | 강한 충돌 | Alert (HIGH/CRITICAL) |

**2-step vs 1-shot 결정:**
- 파일럿(Task #10)에서 2-step으로 먼저 구현 (디버깅 용이)
- 비용 최적화(Task #11)에서 1-shot 병합 테스트

---

#### Task #10: 파일럿 테스트 (Golden Set 5건)

**목표:** AST+NLI 파이프라인 첫 E2E 검증

**테스트 대상 (golden_set_v2.json):**

| ID | 법안 | 난이도 | 기대 결과 |
|----|------|--------|-----------|
| golden_1 | 탄소중립·녹색성장 기본법 | Easy | 높은 Contradiction (에너지 규제 충돌) |
| golden_2 | 중대재해 처벌법 | Easy | 높은 Contradiction (산업안전 충돌) |
| golden_3 | 개인정보 보호법 | Medium | 중간 Contradiction (자율주행 데이터) |
| golden_4 | 약사법 | Hard | 낮은 Contradiction (간접 영향) |
| golden_5 | 국유재산특례제한법 | Hard | 낮은 Contradiction (세제 간접) |

**검증 포인트:**
1. AST 파싱 품질: 4개 노드가 의미있게 추출되는가?
2. NLI 스코어 분포: Easy → 높은 Contradiction, Hard → 낮은 Contradiction?
3. 기존 코사인 유사도 결과 vs NLI Contradiction 비교표
4. reasoning 필드의 설명 가능성 (사람이 읽어서 납득되는가?)
5. LLM 호출 횟수 및 비용 실측

**산출물:**
- `output/phase1/pilot_test_results.json`
- `output/phase1/pilot_comparison.md` (유사도 vs NLI 대조표)

---

#### Task #13: Golden Set 확장 (5건 → 30건)

##### 엣지케이스 #2: 잃어버린 Golden Set 확장 부활

> **위험:** 파일럿 5건만으로 프롬프트 튜닝(Task #11)을 하면 과적합(Overfitting)이
> 발생할 수 있다. 2월 말 대표님(VC)께 "기존 코사인 유사도보다 이 방식이 압도적으로
> 좋습니다!"라고 데이터로 증명하려면, 넉넉잡아 20~30건의 평가셋이 반드시 필요하다.

> **보완:** 파일럿 테스트(Task #10) 성공 직후, Golden Set을 30건으로 확장하는
> 단계를 프롬프트 튜닝(Task #11) **이전에** 배치한다.

**확장 설계:**

| 구분 | 건수 | 설명 |
|------|------|------|
| True Positive (관련 있음) | 15건 | 타 소관이지만 산업부 영향 있는 법안 |
| True Negative (관련 없음) | 15건 | 산업부와 무관한 법안 |
| **합계** | **30건** | |

**난이도 분포:**
| 난이도 | TP | TN | 합계 | 기준 |
|--------|----|----|------|------|
| Easy | 5 | 5 | 10 | 산업부 키워드 직접 언급 |
| Medium | 5 | 5 | 10 | 간접 연관 (공급망, 규제 파급) |
| Hard | 5 | 5 | 10 | 전혀 다른 분야지만 미묘한 영향 |

**샘플링 전략:**
1. `bills_merged.json` 1,021건에서 위원회별 계층 샘플링
2. KG 매칭 결과 + 기존 코사인 유사도 결과 교차 참조
3. **수작업 라벨링 필수** (도메인 전문가 또는 법안 요약 직접 확인)
4. 기존 golden_set_v2.json 5건 포함

**산출물:** `data/golden_set_v3.json`

---

#### Task #11: 프롬프트 튜닝 & 비용 최적화

**목표:** 30건 Golden Set 기준 프롬프트 품질 개선 + 운영 비용 최적화

**선행 조건:** Task #10 (파일럿 성공), Task #13 (Golden Set 30건)

**프롬프트 튜닝:**
- 파일럿에서 AST 파싱 실패/부정확 케이스 분석
- Few-shot 예시 추가 (법률 도메인 특화)
- Action 분류 정밀화: 의무/금지/허용/신고/인가/등록/면제 세분화

**비용 최적화 실험:**

| 실험 | 비교 대상 | 평가 기준 |
|------|-----------|-----------|
| A | 2-step (AST→NLI 분리) vs 1-shot (합체) | F1 대비 비용 |
| B | GPT-4o vs GPT-4o-mini | 품질 vs 비용 트레이드오프 |
| C | 조문 단위 vs 요약 단위 입력 | 정확도 vs 토큰량 |

**비용 목표:**
```
KG 프리필터: 1,021건 → ~731건 (무료, 로컬)
AST 파싱: ~731건 × 평균 2조문 = ~1,462건 × $0.0001 = ~$0.15
NLI 평가: ~1,462쌍 × $0.0003 = ~$0.44
────────────────────────────────────────
전체 1회 스캔: ~$0.6 (GPT-4o-mini) ~ $6 (GPT-4o)
목표: 일배치 1회당 $10 이내
```

**산출물:**
- 최적화된 프롬프트 (`config/prompts/`)
- 비용 분석 리포트

---

#### Task #12: 통합 파이프라인 구축 (KG → AST → NLI)

**목표:** 전체 흐름을 일배치(run_daily.py)에서 실행 가능하도록 통합

**파이프라인 코드 흐름:**
```python
# pipeline_nli.py (신규)
def run_nli_pipeline(target_ministry: str, since_date: str):

    # Step 1: 신규 법안 로드 (기존)
    bills = load_bills(since=since_date)

    # Step 2: KG 프리필터 (기존 kg_prototype.py)
    bill_law_pairs = kg_filter(bills, target_ministry)

    # Step 3: 조문 추출 (Task #7)
    for bill, law in bill_law_pairs:
        target_articles = extract_target_articles(bill['summary'])
        law_articles = get_relevant_articles(law, target_articles)

        # Step 4: AST 파싱 (Task #8)
        existing_ast = parse_ast(law_articles)   # 캐시 활용
        new_ast = parse_ast(bill['summary'])

        # Step 5: NLI 평가 (Task #9)
        result = evaluate_nli(existing_ast, new_ast)

        # Step 6: Alert 생성
        if result['contradiction_score'] >= threshold:
            create_alert(bill, law, result)

    # Step 7: 리포트 + 알림
    generate_report(alerts)
    send_notification(alerts)
```

**기존 시스템과 호환:**
- `run_daily.py`에서 `--method nli` 또는 `--method similarity` 스위칭
- config에서 방식 선택 가능 (점진적 전환)

**산출물:** `src/pipeline_nli.py`, `run_daily.py` 업데이트

---

## 4. 일정 (목표)

| 주차 | 태스크 | 산출물 |
|------|--------|--------|
| **W1** (2/15~) | #7 법률 본문 수집 + #8 AST 파서 | 법률 데이터 + ast_parser.py |
| **W1** | #9 NLI 평가기 | nli_evaluator.py |
| **W2** (2/22~) | #10 파일럿 5건 테스트 | pilot_test_results.json |
| **W2** | #13 Golden Set 30건 확장 | golden_set_v3.json |
| **W2** | #11 프롬프트 튜닝 + 비용 최적화 | 최적 프롬프트 |
| **W3** (3/1~) | #12 통합 파이프라인 | pipeline_nli.py |
| **2월 말** | **VC 보고: 유사도 vs NLI 비교 데이터** | Phase 1 종합 리포트 |

---

## 5. 엣지케이스 방어 요약

### 5.1 조문 단위 추출 (Task #7)

| 항목 | 내용 |
|------|------|
| **위험** | 법률 전체를 LLM에 던지면 컨텍스트 윈도우 초과 + 토큰 비용 폭발 + 환각 |
| **보완** | 법안이 개정하는 특정 조문만 정규식으로 발췌 → 해당 조문만 AST 파서에 전달 |
| **적용 위치** | Task #7 코드에서 `extract_target_articles()` + `get_relevant_articles()` |
| **효과** | 입력 토큰 90%+ 감소, 환각 방지, 비용 절감 |

### 5.2 Golden Set 확장 (Task #13)

| 항목 | 내용 |
|------|------|
| **위험** | 5건만으로 프롬프트 튜닝 시 과적합, VC 보고 시 통계적 설득력 부족 |
| **보완** | 파일럿 성공 직후 30건으로 확장 (TP 15 + TN 15, 난이도 균등 분포) |
| **적용 위치** | Task #10 → Task #13 → Task #11 순서로 배치 (튜닝 이전에 확장) |
| **효과** | 과적합 방지, 통계적 유의미한 비교 가능, VC 보고 데이터 확보 |

---

## 6. 기존 자산 활용

| 기존 자산 | 새 역할 |
|-----------|---------|
| `kg_prototype.py` | 프리필터 (법안→법률 매핑) |
| `moleg_api.py` | 조문 텍스트 수집 |
| `ministry_laws.json` | 부처별 소관 법률 목록 |
| `bills_merged.json` | 신규 법안 데이터 (1,021건) |
| `golden_set_v2.json` | 파일럿 테스트셋 (5건) |
| `embedder.py` | 더 이상 핵심 아님 (비교 베이스라인용으로만 유지) |
| `scorer_v2.py` | 더 이상 핵심 아님 (비교 베이스라인용으로만 유지) |

---

## 7. 리스크

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| 법제처 API 법률 본문 미제공 | 낮음 | 높음 | 국가법령정보센터 웹 스크래핑 대안 |
| LLM AST 파싱 품질 불량 | 중간 | 중간 | Few-shot 예시 보강, 모델 업그레이드 |
| NLI가 코사인보다 못한 경우 | 낮음 | 높음 | 하이브리드(NLI+유사도) 폴백 |
| 비용 초과 ($10/회 목표) | 중간 | 낮음 | GPT-4o-mini + 캐싱 + KG 프리필터 |
| Golden Set 라벨링 주관성 | 중간 | 중간 | 2인 이상 교차 검증 |

---

*Last updated: 2026-02-15*
