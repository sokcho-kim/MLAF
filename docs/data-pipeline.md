# MLAF 데이터 파이프라인

## 개요

국회법 관련 데이터를 수집, 파싱, 병합하는 파이프라인.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Raw Data      │     │   Processed     │     │   Merged        │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ 국회법해설.pdf  │────▶│ na_commentary   │────▶│                 │
│ 국회선례집.pdf  │────▶│ na_precedents   │     │   na_merged     │
│ 법제처 API      │────▶│ na_act_moleg    │────▶│   (최종 데이터) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 데이터 소스

### 1. 국회법해설 (PDF)
- **출처**: [국회입법조사처](https://nsp.nanet.go.kr/plan/subject/detail.do?nationalPlanControlNo=PLAN0000054786)
- **내용**: 국회법 조문별 해설
- **파싱 범위**: 17~716p (국회법만)
- **포함 법률**:
  | 법률 | 페이지 범위 |
  |------|------------|
  | 국회법 | 17~716 |
  | 국정감사 및 조사에 관한 법률 | 717~780 |
  | 국회에서의 증언·감정 등에 관한 법률 | 781~849 |
  | 인사청문회법 | 850~907 |

### 2. 국회선례집 (PDF)
- **출처**: [국회디지털도서관](https://dl.nanet.go.kr/search/searchInnerDetail.do?controlNo=MONO12021000007826)
- **내용**: 국회 운영 선례 모음
- **파싱 범위**: 41p~ (본문)

### 3. 법제처 국가법령정보센터 API
- **API**: `https://www.law.go.kr/DRF/`
- **인증**: OC 파라미터 (테스트용: `chetera`)
- **제공 데이터**: 조/항/호/목 구조화된 법령 원문

## 파이프라인 스크립트

### 1단계: PDF 파싱

```bash
# 국회법해설 파싱 (국회법만)
python src/parser/na_commentary.py

# 국회선례집 파싱
python src/parser/na_precedents.py
```

| 스크립트 | 입력 | 출력 | 설명 |
|---------|------|------|------|
| `na_commentary.py` | `국회법해설.pdf` | `na_commentary.json` | 조문별 해설 추출 |
| `na_precedents.py` | `국회선례집.pdf` | `na_precedents.json` | 선례 추출 |

### 2단계: 법제처 API 데이터 수집

```bash
# 국회법 원문 가져오기
python src/parser/moleg_api.py
```

| 스크립트 | API | 출력 | 설명 |
|---------|-----|------|------|
| `moleg_api.py` | 법제처 API | `na_act_moleg.json` | 조/항/호/목 구조화 |

### 3단계: 데이터 병합

```bash
# 국회법해설 + 법제처 API 병합
python src/parser/merge_na_data.py
```

| 스크립트 | 입력 | 출력 | 설명 |
|---------|------|------|------|
| `merge_na_data.py` | `na_commentary.json` + `na_act_moleg.json` | `na_merged.json` | 조문별 원문+해설 결합 |

## 데이터 스키마

### na_merged.json (최종 데이터)

```json
{
  "info": {
    "law_id": "001416",
    "name": "국회법",
    "promulgation_date": "20251001",
    "enforcement_date": "20251001"
  },
  "chapters": [
    {"number": 1, "type": "장", "title": "총칙"}
  ],
  "articles": [
    {
      "article_id": "5",
      "article_num": 5,
      "sub_num": null,
      "title": "임시회",
      "law_text": "제5조(임시회)",
      "paragraphs": [
        {
          "type": "paragraph",
          "number": 1,
          "content": "① 의장은 임시회의 집회 요구가...",
          "children": [
            {
              "type": "item",
              "number": 1,
              "content": "1. 내우외환...",
              "children": [
                {"type": "subitem", "number": "가", "content": "가. ..."}
              ]
            }
          ]
        }
      ],
      "commentary": "해설 텍스트...",
      "commentary_page": 42,
      "chapter": {"number": 2, "type": "장", "title": "국회의 회기와 휴회"},
      "source": {"moleg": true, "commentary": true}
    }
  ],
  "stats": {
    "total": 219,
    "both_sources": 209,
    "moleg_only": 9,
    "commentary_only": 1
  }
}
```

### 구조 계층

```
조(Article)
└── 항(Paragraph) ①②③...
    └── 호(Item) 1. 2. 3. ...
        └── 목(SubItem) 가. 나. 다. ...
```

## 매핑 현황

### 국회법해설 + 법제처 API

| 항목 | 수량 | 비율 |
|------|------|------|
| 전체 조문 | 219 | 100% |
| 양쪽 매핑 | 209 | 95.4% |
| 법제처만 | 9 | 4.1% |
| 해설만 | 1 | 0.5% |

**법제처에만 있는 조문** (법 개정으로 신설):
> 국회법해설(2024.7 발간) 이후 신설된 조문은 해설이 없는 것이 당연함

| 조문 | 사유 |
|------|------|
| 제22조의5 | 국회세종의사당 (2024년 신설) |
| 제31조, 제53조, 제161조 | 삭제 후 조문번호 재사용 |
| 제165조~제169조 | 제15장 신설 (국회 회의 방해 금지) |

**해설에만 있는 조문** (법 개정으로 삭제):
- 제230조 (매수 및 이해유도죄) - 조문 번호 변경됨

### 선례-조문 매핑

```bash
python src/parser/map_precedent_articles.py
```

| 항목 | 수량 |
|------|------|
| 전체 선례 | 319개 |
| 조문 참조 | 306개 |
| 매핑된 국회법 조문 | 125개 |

**법률별 참조 횟수**:
| 법률 | 참조 횟수 |
|------|----------|
| 국회법 | 227회 |
| 헌법 | 36회 |
| 국정감사법 | 27회 |
| 공직선거법 | 8회 |
| 인사청문회법 | 8회 |

**선례가 많은 조문 TOP 5**:
- 제5조 (임시회): 13개 선례
- 제125조 (표결): 9개 선례
- 제6조 (개회식): 8개 선례
- 제121조 (의결정족수): 7개 선례
- 제122조 (표결방법): 7개 선례

### 관련 법률 (법제처 API)

```bash
python src/parser/fetch_related_laws.py
```

| 법률 | 조문 수 | 출력 파일 | PDF 페이지 |
|------|--------|----------|-----------|
| 국회법 | 218개 | `na_act_moleg.json` | 17~716 |
| 국정감사 및 조사에 관한 법률 | 22개 | `inspection_act_moleg.json` | 717~780 |
| 국회에서의 증언·감정 등에 관한 법률 | 21개 | `testimony_act_moleg.json` | 781~849 |
| 인사청문회법 | 21개 | `hearing_act_moleg.json` | 850~907 |
| **총계** | **282개** | | |

## 비용

| 소스 | 비용 |
|------|------|
| PyMuPDF (PDF 파싱) | $0 |
| 법제처 API | $0 |
| **총 비용** | **$0** |

## 다음 단계

1. [x] 관련 법률 추가 파싱 (국정감사법, 인사청문회법 등) ✓
2. [x] 선례-조문 매핑 ✓
3. [ ] 국회선례집 누락 선례 보완 (207개)
4. [ ] 관련 법률 해설 파싱 및 병합

---

*Last updated: 2026-01-13*
