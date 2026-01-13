# MLAF 프로젝트 지침

## 프로젝트 개요
국회법 관련 데이터 수집/파싱/분석 프로젝트

## 세션 시작 시
1. `tmpclaude-*` 파일이 있으면 삭제
2. 작업일지 확인: `docs/worklog/`

## 세션 종료 시
1. `tmpclaude-*` 임시 파일 삭제 확인
2. 작업일지 업데이트

## 임시 파일 정리
```bash
# tmpclaude 파일 확인 및 삭제
find . -name "tmpclaude-*" -type f -delete
```

`.gitignore`에 이미 추가됨:
```
tmpclaude-*
```

## 데이터 파이프라인
자세한 내용: `docs/data-pipeline.md`

## 주요 스크립트
| 스크립트 | 용도 |
|---------|------|
| `src/parser/na_commentary.py` | 국회법해설 PDF 파싱 |
| `src/parser/na_precedents.py` | 국회선례집 PDF 파싱 |
| `src/parser/moleg_api.py` | 법제처 API 연동 |
| `src/parser/merge_na_data.py` | 데이터 병합 |
| `src/parser/map_precedent_articles.py` | 선례-조문 매핑 |

## 작업일지
- 위치: `docs/worklog/YYYY-MM-DD.md`
- `/worklog` 스킬 사용 가능 (DobbyOps)
