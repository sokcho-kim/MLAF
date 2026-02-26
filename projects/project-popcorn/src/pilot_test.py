"""
Task #10: 파일럿 테스트 (Golden Set 5건)

AST+NLI 파이프라인 E2E 검증
- 각 Golden Set 법안을 산업부 소관 법률과 비교
- AST 파싱 → NLI 평가 → 충돌 여부 판정
- 기존 코사인 유사도와 비교

Usage:
    python src/pilot_test.py
    python src/pilot_test.py --model gpt-4o   # GPT-4o로 테스트
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from ast_parser import ASTParser
from nli_evaluator import NLIEvaluator
from collect_law_texts import extract_target_articles, get_relevant_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output" / "phase1"


# ============================================================
# Golden Set → 산업부 법률 매핑 (수동 정의)
# ============================================================
# 각 Golden Set 법안이 산업부의 어떤 법률과 비교되어야 하는지
# 실제 파이프라인에서는 KG + 키워드로 자동화되지만, 파일럿에서는 수동 지정

GOLDEN_LAW_MAPPING = {
    "golden_1": {
        # 탄소중립기본법 개정 → 에너지 규제 영향
        "description": "탄소 배출권, 공장 가동 규제 이슈",
        "target_laws": [
            {"law_name": "에너지법", "reason": "에너지 정책/공급 규제 충돌"},
            {"law_name": "에너지이용 합리화법", "reason": "에너지 사용 규제 영향"},
        ],
    },
    "golden_2": {
        # 중대재해처벌법 개정 → 산업현장 안전 (산업부 직접 소관)
        "description": "산업 현장 안전, 경영자 처벌 이슈",
        "target_laws": [
            {"law_name": "중대재해 처벌 등에 관한 법률", "reason": "산업부 직접 소관 법률"},
        ],
    },
    "golden_3": {
        # 개인정보보호법 개정 → 신산업 데이터 활용 규제
        "description": "자율주행, AI 등 신산업 데이터 활용 규제 이슈",
        "target_laws": [
            {"law_name": "산업 디지털 전환 촉진법", "reason": "디지털 전환 데이터 활용 영향"},
            {"law_name": "지능형 로봇 개발 및 보급 촉진법", "reason": "AI/로봇 데이터 규제 영향"},
        ],
    },
    "golden_4": {
        # 약사법 개정 → 의약품 제조시설/공장 기준
        "description": "의약품 제조 시설(공장) 설비 기준 강화 이슈",
        "target_laws": [
            {"law_name": "산업집적활성화 및 공장설립에 관한 법률", "reason": "공장 설립 기준 영향"},
            {"law_name": "제품안전기본법", "reason": "제품 안전 기준 영향"},
        ],
    },
    "golden_5": {
        # 국유재산특례제한법 개정 → 신재생에너지 국유재산 사용료 감면
        "description": "산업단지/경제자유구역 세제 혜택 제한 이슈",
        "target_laws": [
            {"law_name": "신에너지 및 재생에너지 개발ㆍ이용ㆍ보급 촉진법", "reason": "신재생에너지 사업 규제 영향"},
            {"law_name": "전원개발촉진법", "reason": "전원개발 사업 영향"},
        ],
    },
}


def load_data():
    """데이터 로드"""
    # Golden Set
    with open(DATA_DIR / "golden_set_v2.json", "r", encoding="utf-8") as f:
        golden = json.load(f)

    # 산업부 법률 텍스트
    with open(DATA_DIR / "law_texts" / "산업통상부_laws.json", "r", encoding="utf-8") as f:
        law_texts = json.load(f)

    law_text_map = {l["law_name"]: l for l in law_texts["laws"]}

    return golden, law_text_map


SKIP_ARTICLE_TITLES = {"목적", "정의", "기본이념"}


def find_relevant_articles(law: Dict, bill_summary: str) -> List[Dict]:
    """법안 요약에서 대상 조문을 추출하고, 법률에서 해당 조문 필터링

    대상 조문을 못 찾으면 법률 핵심 조문(목적, 정의, 주요 규정)을 반환
    정의조/목적조/기본이념은 fallback에서 제외 (선언형 조문 → False Positive 방지)
    """
    target_refs = extract_target_articles(bill_summary)
    articles = law.get("articles", [])

    if target_refs:
        filtered = get_relevant_articles(articles, target_refs)
        if filtered:
            return filtered

    # fallback: 핵심 조문 (정의조/목적조/기본이념 제외)
    core = []
    for a in articles:
        content = a.get("content", "")
        title = a.get("title", "")
        if content and "삭제" not in content[:10]:
            if title in SKIP_ARTICLE_TITLES:
                continue
            core.append(a)
            if len(core) >= 3:
                break

    # 안전장치: 전부 건너뛰면 건너뛴 조문도 포함
    if not core:
        for a in articles:
            content = a.get("content", "")
            if content and "삭제" not in content[:10]:
                core.append(a)
                if len(core) >= 3:
                    break

    return core


def run_pilot_test(model: str = "gpt-4o-mini"):
    """파일럿 테스트 실행"""
    logger.info(f"=== Phase 1 파일럿 테스트 시작 (모델: {model}) ===")
    start_time = time.time()

    golden, law_text_map = load_data()
    ast_parser = ASTParser(model=model)
    nli_evaluator = NLIEvaluator(model=model)

    results = []

    for bill in golden["bills"]:
        golden_id = bill["golden_id"]
        bill_name = bill["bill_name"]
        difficulty = bill["difficulty"]
        mapping = GOLDEN_LAW_MAPPING.get(golden_id, {})

        logger.info(f"\n--- [{golden_id}] {bill_name[:50]} (난이도: {difficulty}) ---")

        # 1. 법안 AST 파싱
        bill_ast_result = ast_parser.parse_bill_summary(bill)
        bill_ast = bill_ast_result["ast"]
        logger.info(f"  법안 AST: Subject={bill_ast['subject'][:30]}...")

        bill_result = {
            "golden_id": golden_id,
            "bill_name": bill_name,
            "difficulty": difficulty,
            "risk_description": bill.get("risk_description", ""),
            "bill_ast": bill_ast,
            "comparisons": [],
        }

        # 2. 각 대상 법률과 비교
        for target in mapping.get("target_laws", []):
            law_name = target["law_name"]
            reason = target["reason"]

            law = law_text_map.get(law_name)
            if not law:
                logger.warning(f"  법률 미수집: {law_name}")
                bill_result["comparisons"].append({
                    "law_name": law_name,
                    "reason": reason,
                    "status": "law_not_found",
                })
                continue

            # 3. 관련 조문 추출
            relevant_articles = find_relevant_articles(law, bill.get("summary", ""))
            logger.info(f"  비교 대상: {law_name} ({len(relevant_articles)}개 조문)")

            # 4. 각 조문에 대해 AST 파싱 + NLI 평가
            article_results = []
            for article in relevant_articles:
                art_ast_result = ast_parser.parse_article(article)
                if art_ast_result.get("skipped"):
                    continue

                art_ast = art_ast_result["ast"]

                # NLI 평가: 기존 법률 조문 vs 신규 법안
                nli_result = nli_evaluator.evaluate(art_ast, bill_ast)

                article_results.append({
                    "article_id": art_ast_result["article_id"],
                    "article_title": art_ast_result["title"],
                    "law_ast": art_ast,
                    "nli_analysis": nli_result.nli_analysis,
                    "reasoning": nli_result.reasoning,
                    "alert_level": nli_result.alert_level,
                    "component_analysis": nli_result.component_analysis,
                })

                logger.info(
                    f"    제{art_ast_result['article_id']}조 "
                    f"→ C={nli_result.contradiction_score:.2f} "
                    f"E={nli_result.entailment_score:.2f} "
                    f"[{nli_result.alert_level}]"
                )

            # 법률별 최고 충돌 점수
            max_contradiction = 0.0
            if article_results:
                max_contradiction = max(
                    r["nli_analysis"]["contradiction_score"] for r in article_results
                )

            bill_result["comparisons"].append({
                "law_name": law_name,
                "reason": reason,
                "status": "evaluated",
                "articles_compared": len(article_results),
                "max_contradiction": max_contradiction,
                "article_results": article_results,
            })

        # 법안 전체 최고 충돌 점수
        all_scores = [
            c["max_contradiction"]
            for c in bill_result["comparisons"]
            if c.get("status") == "evaluated"
        ]
        bill_result["max_contradiction"] = max(all_scores) if all_scores else 0.0

        results.append(bill_result)

    # 통계
    elapsed = time.time() - start_time
    ast_stats = ast_parser.get_stats()
    nli_stats = nli_evaluator.get_stats()

    summary = {
        "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "elapsed_seconds": round(elapsed, 1),
        "ast_stats": ast_stats,
        "nli_stats": nli_stats,
        "total_api_calls": ast_stats["api_call"] + nli_stats["api_call"],
        "results": results,
    }

    # 캐시 저장
    ast_parser.save_cache()
    nli_evaluator.save_cache()

    # 결과 저장
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "pilot_test_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 결과 출력
    print_results(summary)

    return summary


def print_results(summary: Dict):
    """결과 테이블 출력"""
    results = summary["results"]

    print(f"\n{'='*80}")
    print(f"Phase 1 파일럿 테스트 결과 (모델: {summary['model']})")
    print(f"{'='*80}")
    print(f"소요 시간: {summary['elapsed_seconds']}초")
    print(f"API 호출: AST {summary['ast_stats']['api_call']}건 + "
          f"NLI {summary['nli_stats']['api_call']}건 = "
          f"총 {summary['total_api_calls']}건")
    print()

    # 요약 테이블
    print(f"{'ID':<12} {'난이도':<8} {'최고 충돌':<10} {'판정':<10} 법안명")
    print(f"{'-'*80}")

    for r in results:
        score = r["max_contradiction"]
        if score >= 0.6:
            verdict = "충돌 감지"
        elif score >= 0.3:
            verdict = "약한 연관"
        else:
            verdict = "무관"

        name = r["bill_name"][:40]
        print(f"{r['golden_id']:<12} {r['difficulty']:<8} {score:<10.2f} {verdict:<10} {name}")

    # 상세 결과
    print(f"\n{'='*80}")
    print("상세 결과")
    print(f"{'='*80}")

    for r in results:
        print(f"\n[{r['golden_id']}] {r['bill_name'][:60]}")
        print(f"  난이도: {r['difficulty']} | 기대: {r['risk_description']}")
        print(f"  법안 AST:")
        ast = r["bill_ast"]
        print(f"    Subject:   {ast['subject'][:60]}")
        print(f"    Action:    {ast['action'][:60]}")

        for comp in r["comparisons"]:
            if comp["status"] != "evaluated":
                print(f"  ↔ {comp['law_name']}: 미수집")
                continue

            print(f"  ↔ {comp['law_name']} "
                  f"(비교 {comp['articles_compared']}건, "
                  f"최고 충돌={comp['max_contradiction']:.2f})")

            for ar in comp.get("article_results", []):
                nli = ar["nli_analysis"]
                print(f"    제{ar['article_id']}조 [{ar['article_title'][:20]}] "
                      f"C={nli['contradiction_score']:.2f} "
                      f"E={nli['entailment_score']:.2f} "
                      f"N={nli['neutral_score']:.2f} "
                      f"[{ar['alert_level']}]")
                # component_analysis 표시
                ca = ar.get("component_analysis", {})
                if ca:
                    parts = []
                    if ca.get("subject"):
                        parts.append(f"S={ca['subject']}")
                    if ca.get("action"):
                        parts.append(f"A={ca['action']}")
                    if parts:
                        print(f"      분석: {' | '.join(parts)}")
                if ar["reasoning"]:
                    reason = ar["reasoning"][:120]
                    print(f"      → {reason}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1 파일럿 테스트")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        help="LLM 모델 (기본: gpt-4o-mini)")

    args = parser.parse_args()
    run_pilot_test(model=args.model)
