"""
기존 법률 본문 수집기 (법제처 API)

Task #7: 산업통상부 소관 법률의 조문 텍스트를 법제처 API로 수집
- 조문(Article) 단위로 구조화하여 저장
- 법률 전체가 아닌, 조/항/호/목 단위로 분리

Usage:
    python src/collect_law_texts.py --ministry 산업통상부
    python src/collect_law_texts.py --ministry 산업통상부 --law "에너지법"  # 단건 테스트
    python src/collect_law_texts.py --ministry 산업통상부 --skip-rules     # 시행규칙 제외
"""
import re
import json
import time
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import sys
# moleg_api.py 위치: MLAF/src/parser/moleg_api.py
# collect_law_texts.py: MLAF/projects/project-popcorn/src/ → 4단계 상위
_PARSER_DIR = Path(__file__).resolve().parent.parent.parent.parent / "src" / "parser"
sys.path.insert(0, str(_PARSER_DIR))
from moleg_api import fetch_law_detail, parse_law_xml

# 경로 설정
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = DATA_DIR / "law_texts"
LOG_DIR = PROJECT_DIR / "logs"

# 로깅 설정
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "collect_law_texts.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 법제처 API 설정
API_OC = "chetera"
API_DISPLAY = 100       # 검색 결과 최대 수
API_DELAY = 0.5         # 요청 간 딜레이 (초) - 서버 부하 방지


def load_ministry_laws(ministry: str) -> List[str]:
    """부처별 소관 법률 목록 로드"""
    with open(DATA_DIR / "ministry_laws.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    laws = data.get(ministry, [])
    if not laws:
        available = list(data.keys())
        raise ValueError(f"부처 '{ministry}' 없음. 가능한 부처: {available}")

    return laws


def filter_law_names(law_names: List[str], skip_rules: bool = True) -> List[str]:
    """수집 대상 법률 필터링

    Args:
        law_names: 전체 법률명 리스트
        skip_rules: True이면 시행령/시행규칙/규정/규칙 제외 (법률만)
    """
    if not skip_rules:
        return law_names

    filtered = []
    skipped = []
    for name in law_names:
        # 시행령, 시행규칙, 규정, 규칙은 제외 (법률만 대상)
        if re.search(r'시행령|시행규칙|규칙$|규정$|직제$', name):
            skipped.append(name)
        else:
            filtered.append(name)

    logger.info(f"필터링: {len(law_names)}건 → {len(filtered)}건 (제외 {len(skipped)}건)")
    if skipped:
        logger.debug(f"제외 목록: {skipped[:5]}...")

    return filtered


def search_law_mst(law_name: str) -> Optional[Dict]:
    """법률명으로 법제처 API 검색 → MST(법령일련번호) 반환

    Returns:
        {"mst": "...", "name": "...", "department": "..."} 또는 None
    """
    import requests
    import xml.etree.ElementTree as ET

    url = "https://www.law.go.kr/DRF/lawSearch.do"
    params = {
        "OC": API_OC,
        "target": "law",
        "type": "XML",
        "query": law_name,
        "display": API_DISPLAY,
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.text)
    except Exception as e:
        logger.error(f"검색 실패 [{law_name}]: {e}")
        return None

    # 1. 정확 매칭 시도
    for law_elem in root.findall(".//law"):
        name = law_elem.findtext("법령명한글", "")
        if name == law_name:
            return {
                "mst": law_elem.findtext("법령일련번호", ""),
                "name": name,
                "department": law_elem.findtext("소관부처명", ""),
            }

    # 2. 정규화 매칭 (공백/특수문자 차이)
    normalized_target = law_name.replace(" ", "").replace("ㆍ", "·")
    for law_elem in root.findall(".//law"):
        name = law_elem.findtext("법령명한글", "")
        normalized_name = name.replace(" ", "").replace("ㆍ", "·")
        if normalized_name == normalized_target:
            return {
                "mst": law_elem.findtext("법령일련번호", ""),
                "name": name,
                "department": law_elem.findtext("소관부처명", ""),
            }

    # 3. 포함 매칭 (법률명이 검색 결과에 포함)
    for law_elem in root.findall(".//law"):
        name = law_elem.findtext("법령명한글", "")
        # 시행령/시행규칙 제외
        if "시행령" in name or "시행규칙" in name:
            continue
        if law_name in name or name in law_name:
            return {
                "mst": law_elem.findtext("법령일련번호", ""),
                "name": name,
                "department": law_elem.findtext("소관부처명", ""),
            }

    return None


def fetch_and_parse_law(mst: str, law_name: str) -> Optional[Dict]:
    """법령 상세 조회 + 파싱

    Returns:
        파싱된 법률 데이터 (info, articles, chapters 등)
    """
    try:
        xml_text = fetch_law_detail(mst, API_OC)
        result = parse_law_xml(xml_text)
        return result
    except Exception as e:
        logger.error(f"상세 조회 실패 [{law_name}] MST={mst}: {e}")
        return None


def extract_target_articles(bill_summary: str) -> List[str]:
    """법안 요약에서 개정 대상 조문 번호 추출

    Args:
        bill_summary: 법안 제안이유 및 주요내용

    Returns:
        조문 번호 리스트 (예: ["제4조", "제12조", "제12조의2"])

    Examples:
        >>> extract_target_articles("(안 제2조제18호 신설 등)")
        ["제2조"]
        >>> extract_target_articles("(안 제2조제9호가목 및 제15조의2 신설)")
        ["제2조", "제15조의2"]
    """
    # "안 제N조" 또는 "제N조" 패턴 매칭
    # 제N조, 제N조의N 형태 캡처
    pattern = r'제(\d+)조(?:의(\d+))?'
    matches = re.findall(pattern, bill_summary)

    articles = set()
    for main_num, sub_num in matches:
        if sub_num:
            articles.add(f"제{main_num}조의{sub_num}")
        else:
            articles.add(f"제{main_num}조")

    return sorted(articles, key=lambda x: (
        int(re.search(r'(\d+)', x).group(1)),
        int(re.search(r'의(\d+)', x).group(1)) if '의' in x else 0
    ))


def get_relevant_articles(
    law_articles: List[Dict],
    target_article_refs: List[str],
) -> List[Dict]:
    """법률 전체 조문에서 타겟 조문만 필터링

    Args:
        law_articles: 법률의 전체 조문 리스트
        target_article_refs: 대상 조문 참조 리스트 (예: ["제4조", "제12조의2"])

    Returns:
        해당 조문만 필터링된 리스트
    """
    if not target_article_refs:
        return law_articles  # 특정 조문 없으면 전체 반환

    # 조문 번호 → article_id 변환
    # "제4조" → "4", "제12조의2" → "12-2"
    target_ids = set()
    for ref in target_article_refs:
        match = re.match(r'제(\d+)조(?:의(\d+))?', ref)
        if match:
            main = match.group(1)
            sub = match.group(2)
            if sub:
                target_ids.add(f"{main}-{sub}")
            else:
                target_ids.add(main)

    filtered = []
    for article in law_articles:
        art_id = str(article.get("article_id", ""))
        if art_id in target_ids:
            filtered.append(article)

    return filtered


def collect_ministry_laws(
    ministry: str,
    skip_rules: bool = True,
    single_law: Optional[str] = None,
) -> Dict:
    """부처 소관 법률 일괄 수집

    Args:
        ministry: 부처명
        skip_rules: 시행규칙 등 제외 여부
        single_law: 단건 테스트 시 법률명 지정

    Returns:
        수집 결과 딕셔너리
    """
    logger.info(f"=== {ministry} 소관 법률 수집 시작 ===")

    # 1. 법률 목록 로드
    all_laws = load_ministry_laws(ministry)
    logger.info(f"전체 소관 법률: {len(all_laws)}건")

    if single_law:
        target_laws = [single_law]
    else:
        target_laws = filter_law_names(all_laws, skip_rules)

    # 2. 수집 결과 초기화
    result = {
        "ministry": ministry,
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_target": len(target_laws),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "laws": [],
        "failures": [],
    }

    # 3. 법률별 수집
    for i, law_name in enumerate(target_laws, 1):
        logger.info(f"[{i}/{len(target_laws)}] {law_name}")

        # 3-1. MST 검색
        search_result = search_law_mst(law_name)
        time.sleep(API_DELAY)

        if not search_result:
            logger.warning(f"  → 검색 실패 (API 결과 없음)")
            result["failures"].append({
                "law_name": law_name,
                "reason": "search_not_found",
            })
            result["failed"] += 1
            continue

        mst = search_result["mst"]
        api_name = search_result["name"]
        if api_name != law_name:
            logger.info(f"  → 매칭: '{law_name}' → '{api_name}'")

        # 3-2. 상세 조회 + 파싱
        parsed = fetch_and_parse_law(mst, law_name)
        time.sleep(API_DELAY)

        if not parsed:
            logger.warning(f"  → 상세 조회 실패")
            result["failures"].append({
                "law_name": law_name,
                "mst": mst,
                "reason": "detail_fetch_failed",
            })
            result["failed"] += 1
            continue

        # 3-3. 저장 구조
        law_data = {
            "law_name": api_name,
            "law_name_query": law_name,
            "mst": mst,
            "law_id": parsed["info"].get("law_id", ""),
            "department": parsed["info"].get("department", ""),
            "enforcement_date": parsed["info"].get("enforcement_date", ""),
            "total_articles": parsed["total_articles"],
            "chapters": parsed["chapters"],
            "articles": parsed["articles"],
        }

        result["laws"].append(law_data)
        result["success"] += 1
        logger.info(f"  → 성공: {parsed['total_articles']}개 조문")

    # 4. 통계
    logger.info(f"\n=== 수집 완료 ===")
    logger.info(f"성공: {result['success']}건")
    logger.info(f"실패: {result['failed']}건")
    logger.info(f"총 조문: {sum(l['total_articles'] for l in result['laws'])}개")

    return result


def save_result(result: Dict, ministry: str) -> Path:
    """결과 JSON 저장"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 파일명: 산업통상부_laws.json
    filename = f"{ministry}_laws.json"
    output_path = OUTPUT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"저장 완료: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="법제처 API 법률 본문 수집기")
    parser.add_argument("--ministry", type=str, default="산업통상부", help="대상 부처")
    parser.add_argument("--law", type=str, default=None, help="단건 테스트 법률명")
    parser.add_argument("--skip-rules", action="store_true", default=True,
                        help="시행규칙/시행령 제외 (기본값: True)")
    parser.add_argument("--include-all", action="store_true",
                        help="시행규칙/시행령 포함")

    args = parser.parse_args()
    skip_rules = not args.include_all

    result = collect_ministry_laws(
        ministry=args.ministry,
        skip_rules=skip_rules,
        single_law=args.law,
    )

    output_path = save_result(result, args.ministry)
    print(f"\n결과: {output_path}")
    print(f"성공 {result['success']}건 / 실패 {result['failed']}건")

    if result["failures"]:
        print(f"\n실패 목록:")
        for f in result["failures"]:
            print(f"  - {f['law_name']}: {f['reason']}")


if __name__ == "__main__":
    main()
