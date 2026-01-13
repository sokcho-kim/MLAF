# -*- coding: utf-8 -*-
"""
국회법 데이터 병합 모듈
- 법제처 API (구조화된 법조문) + 국회법해설 (해설/주석) 매핑
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def load_json(path: str) -> Dict:
    """JSON 파일 로드"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_article_id(article_id: str) -> str:
    """조문 ID 정규화 (정렬용)"""
    # "1" -> "001", "1-2" -> "001-002"
    parts = article_id.split('-')
    normalized = []
    for p in parts:
        if p.isdigit():
            normalized.append(p.zfill(3))
        else:
            normalized.append(p)
    return '-'.join(normalized)


def merge_na_data(
    moleg_path: str,
    commentary_path: str,
    output_path: str
) -> Dict:
    """
    법제처 API 데이터 + 국회법해설 병합

    Returns:
        {
            'info': {...},           # 법령 기본정보
            'chapters': [...],       # 장/절 정보
            'articles': [            # 조문 목록
                {
                    'article_id': '1',
                    'title': '목적',
                    'law_text': '제1조(목적)...',
                    'paragraphs': [...],    # 조/항/호/목 구조
                    'commentary': '해설...',  # 국회법해설에서 가져온 해설
                    'chapter': {...},
                    'source': {
                        'moleg': True,      # 법제처 API 출처
                        'commentary': True  # 국회법해설 출처
                    }
                },
                ...
            ],
            'stats': {...}
        }
    """
    print("[1/4] 데이터 로드 중...")
    moleg_data = load_json(moleg_path)
    commentary_data = load_json(commentary_path)

    # 인덱스 구축
    moleg_index = {a['article_id']: a for a in moleg_data['articles']}
    commentary_index = {a['article_id']: a for a in commentary_data['articles']}

    all_ids = set(moleg_index.keys()) | set(commentary_index.keys())

    print(f"[2/4] 조문 병합 중... ({len(all_ids)}개)")

    merged_articles = []
    stats = {
        'total': 0,
        'both_sources': 0,
        'moleg_only': 0,
        'commentary_only': 0,
    }

    for article_id in sorted(all_ids, key=normalize_article_id):
        moleg_article = moleg_index.get(article_id)
        commentary_article = commentary_index.get(article_id)

        merged = {
            'article_id': article_id,
            'source': {
                'moleg': moleg_article is not None,
                'commentary': commentary_article is not None
            }
        }

        # 법제처 데이터 우선 (구조화됨)
        if moleg_article:
            merged['article_num'] = moleg_article['article_num']
            merged['sub_num'] = moleg_article.get('sub_num')
            merged['title'] = moleg_article['title']
            merged['law_text'] = moleg_article['content']
            merged['paragraphs'] = moleg_article['paragraphs']
            merged['reference'] = moleg_article.get('reference', '')
            if moleg_article.get('chapter'):
                merged['chapter'] = moleg_article['chapter']
        elif commentary_article:
            # 법제처에 없으면 해설에서 기본정보 가져옴
            merged['article_num'] = commentary_article['article_num']
            merged['sub_num'] = commentary_article.get('sub_num')
            merged['title'] = commentary_article['title']
            merged['law_text'] = commentary_article.get('law_text', '')
            merged['paragraphs'] = []  # 구조화 안됨

        # 해설 추가
        if commentary_article:
            merged['commentary'] = commentary_article.get('commentary', '')
            merged['commentary_page'] = commentary_article.get('start_page')
        else:
            merged['commentary'] = ''
            merged['commentary_page'] = None

        merged_articles.append(merged)

        # 통계
        stats['total'] += 1
        if moleg_article and commentary_article:
            stats['both_sources'] += 1
        elif moleg_article:
            stats['moleg_only'] += 1
        else:
            stats['commentary_only'] += 1

    print(f"[3/4] 결과 구성 중...")

    result = {
        'info': moleg_data.get('info', {}),
        'chapters': moleg_data.get('chapters', []),
        'articles': merged_articles,
        'total_articles': len(merged_articles),
        'stats': stats,
        'sources': {
            'moleg': '법제처 국가법령정보센터 API',
            'commentary': '국회법해설 (PDF 파싱)'
        }
    }

    print(f"[4/4] 저장 중... ({output_path})")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 통계 출력
    print(f"\n=== 병합 통계 ===")
    print(f"전체 조문: {stats['total']}개")
    print(f"양쪽 모두: {stats['both_sources']}개 ({stats['both_sources']/stats['total']*100:.1f}%)")
    print(f"법제처만: {stats['moleg_only']}개")
    print(f"해설만: {stats['commentary_only']}개")

    return result


def print_sample(result: Dict, count: int = 3):
    """샘플 출력"""
    print(f"\n=== 샘플 (처음 {count}개) ===")

    for article in result['articles'][:count]:
        print(f"\n[제{article['article_id']}조] {article['title']}")
        print(f"  출처: 법제처={article['source']['moleg']}, 해설={article['source']['commentary']}")

        if article.get('chapter'):
            ch = article['chapter']
            print(f"  장: 제{ch['number']}{ch['type']} {ch['title']}")

        print(f"  항 수: {len(article['paragraphs'])}")

        commentary = article.get('commentary', '')
        if commentary:
            preview = commentary[:100].replace('\n', ' ')
            print(f"  해설: {preview}...")
        else:
            print(f"  해설: (없음)")


def analyze_mismatches(result: Dict):
    """매핑 안 된 조문 분석"""
    print("\n=== 매핑 분석 ===")

    moleg_only = [a for a in result['articles'] if a['source']['moleg'] and not a['source']['commentary']]
    commentary_only = [a for a in result['articles'] if not a['source']['moleg'] and a['source']['commentary']]

    if moleg_only:
        print(f"\n법제처에만 있는 조문 ({len(moleg_only)}개):")
        for a in moleg_only:
            print(f"  - 제{a['article_id']}조 ({a['title']})")

    if commentary_only:
        print(f"\n해설에만 있는 조문 ({len(commentary_only)}개):")
        for a in commentary_only:
            print(f"  - 제{a['article_id']}조 ({a['title']})")


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent

    MOLEG_PATH = BASE_DIR / "data" / "processed" / "na_act_moleg.json"
    COMMENTARY_PATH = BASE_DIR / "data" / "processed" / "na_commentary.json"
    OUTPUT_PATH = BASE_DIR / "data" / "processed" / "na_merged.json"

    result = merge_na_data(
        str(MOLEG_PATH),
        str(COMMENTARY_PATH),
        str(OUTPUT_PATH)
    )

    print_sample(result)
    analyze_mismatches(result)
