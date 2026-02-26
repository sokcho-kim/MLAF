"""
Task #12: Golden Set V3 전체 테스트 (30건)

AST+NLI V2 프롬프트를 30건 Golden Set으로 검증
- TP 15건: 산업부 영향 있는 법안 (expected_relevant=True)
- TN 15건: 산업부 무관 법안 (expected_relevant=False)

분류 성능 지표: Precision, Recall, F1, Accuracy

Usage:
    python src/golden_test_v3.py
    python src/golden_test_v3.py --model gpt-4o-mini --threshold 0.3
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

SKIP_ARTICLE_TITLES = {"목적", "정의", "기본이념"}


# ============================================================
# 30건 법률 매핑
# ============================================================

GOLDEN_LAW_MAPPING = {
    # ---- TP: 산업부 영향 있는 법안 (15건) ----

    "golden_1": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "에너지 정책/공급 규제 충돌"},
            {"law_name": "에너지이용 합리화법", "reason": "에너지 사용 규제 영향"},
        ],
    },
    "golden_2": {
        "target_laws": [
            {"law_name": "중대재해 처벌 등에 관한 법률", "reason": "산업부 직접 소관"},
        ],
    },
    "golden_3": {
        "target_laws": [
            {"law_name": "산업 디지털 전환 촉진법", "reason": "디지털 전환 데이터 활용"},
            {"law_name": "지능형 로봇 개발 및 보급 촉진법", "reason": "AI/로봇 데이터 규제"},
        ],
    },
    "golden_4": {
        "target_laws": [
            {"law_name": "산업집적활성화 및 공장설립에 관한 법률", "reason": "공장 설립 기준"},
            {"law_name": "제품안전기본법", "reason": "제품 안전 기준"},
        ],
    },
    "golden_5": {
        "target_laws": [
            {"law_name": "신에너지 및 재생에너지 개발ㆍ이용ㆍ보급 촉진법", "reason": "신재생에너지 사업 규제"},
            {"law_name": "전원개발촉진법", "reason": "전원개발 사업"},
        ],
    },
    "golden_6": {
        # 한국산업은행법 → 산업 금융 지원
        "target_laws": [
            {"law_name": "산업발전법", "reason": "산업 금융/지원 정책"},
            {"law_name": "국가첨단전략산업 경쟁력 강화 및 보호에 관한 특별조치법", "reason": "첨단산업 투자"},
        ],
    },
    "golden_7": {
        # 송변전설비법 → 산업부 직접 소관
        "target_laws": [
            {"law_name": "송ㆍ변전설비 주변지역의 보상 및 지원에 관한 법률", "reason": "직접 소관 법률"},
            {"law_name": "전기사업법", "reason": "전기 사업 규제"},
        ],
    },
    "golden_8": {
        # 방위사업법 → 산업부 직접 소관
        "target_laws": [
            {"law_name": "방위사업법", "reason": "직접 소관 법률"},
        ],
    },
    "golden_9": {
        # 기후변화 감시법 → 에너지/탄소
        "target_laws": [
            {"law_name": "에너지법", "reason": "에너지 정책 영향"},
            {"law_name": "신에너지 및 재생에너지 개발ㆍ이용ㆍ보급 촉진법", "reason": "신재생에너지 정책"},
        ],
    },
    "golden_10": {
        # 초대형산불 특별법 → 산업시설 복구
        "target_laws": [
            {"law_name": "산업집적활성화 및 공장설립에 관한 법률", "reason": "산업단지/공장 복구"},
            {"law_name": "고압가스 안전관리법", "reason": "산업시설 안전관리"},
        ],
    },
    "golden_11": {
        # 개별소비세법 → 수소경제
        "target_laws": [
            {"law_name": "수소경제 육성 및 수소 안전관리에 관한 법률", "reason": "수소 제조 세제"},
            {"law_name": "석유 및 석유대체연료 사업법", "reason": "부탄/프로판 세제"},
        ],
    },
    "golden_12": {
        # 임금채권보장법 → 산업 근로자
        "target_laws": [
            {"law_name": "산업발전법", "reason": "산업 근로자 보호"},
            {"law_name": "에너지법", "reason": "에너지 산업 노동"},
        ],
    },
    "golden_13": {
        # 군인사법 → 방위산업
        "target_laws": [
            {"law_name": "방위사업법", "reason": "방위산업 인력"},
            {"law_name": "국가자원안보 특별법", "reason": "자원 안보 인력"},
        ],
    },
    "golden_14": {
        # 애니메이션산업법 → 산업 진흥
        "target_laws": [
            {"law_name": "산업발전법", "reason": "산업 진흥 일반"},
            {"law_name": "산업융합 촉진법", "reason": "콘텐츠-산업 융합"},
        ],
    },
    "golden_15": {
        # 농어업재해대책법 → 산업시설
        "target_laws": [
            {"law_name": "산업집적활성화 및 공장설립에 관한 법률", "reason": "농어촌 산업시설"},
            {"law_name": "고압가스 안전관리법", "reason": "재해 안전관리"},
        ],
    },

    # ---- TN: 산업부 무관 법안 (15건) ----
    # 대표 법률 2개와 비교하여 무관 확인

    "golden_16": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_17": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_18": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_19": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_20": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_21": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_22": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_23": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_24": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_25": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_26": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_27": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_28": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_29": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
    "golden_30": {
        "target_laws": [
            {"law_name": "에너지법", "reason": "TN 대조 (무관 기대)"},
            {"law_name": "산업발전법", "reason": "TN 대조 (무관 기대)"},
        ],
    },
}


# ============================================================
# 핵심 함수
# ============================================================

def load_data():
    """Golden Set V3 + 산업부 법률 로드"""
    with open(DATA_DIR / "golden_set_v3.json", "r", encoding="utf-8") as f:
        golden = json.load(f)

    with open(DATA_DIR / "law_texts" / "산업통상부_laws.json", "r", encoding="utf-8") as f:
        law_texts = json.load(f)

    law_text_map = {l["law_name"]: l for l in law_texts["laws"]}

    return golden, law_text_map


def find_relevant_articles(law: Dict, bill_summary: str) -> List[Dict]:
    """법안 요약에서 관련 조문 추출 (정의조/목적조/기본이념 fallback 제외)"""
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

    # 안전장치
    if not core:
        for a in articles:
            content = a.get("content", "")
            if content and "삭제" not in content[:10]:
                core.append(a)
                if len(core) >= 3:
                    break

    return core


def run_full_test(model: str = "gpt-4o-mini", threshold: float = 0.3):
    """30건 전체 테스트"""
    logger.info(f"=== Golden Set V3 전체 테스트 (모델: {model}, 임계값: {threshold}) ===")
    start_time = time.time()

    golden, law_text_map = load_data()
    ast_parser = ASTParser(model=model)
    nli_evaluator = NLIEvaluator(model=model)

    results = []

    for bill in golden["bills"]:
        golden_id = bill["golden_id"]
        bill_name = bill["bill_name"]
        difficulty = bill["difficulty"]
        expected_relevant = bill["expected_relevant"]
        mapping = GOLDEN_LAW_MAPPING.get(golden_id, {})

        tag = "TP" if expected_relevant else "TN"
        logger.info(f"\n--- [{golden_id}] [{tag}] {bill_name[:50]} ({difficulty}) ---")

        # 1. 법안 AST 파싱
        bill_ast_result = ast_parser.parse_bill_summary(bill)
        bill_ast = bill_ast_result["ast"]
        logger.info(f"  법안 AST: S={bill_ast['subject'][:25]}.. "
                     f"M={bill_ast.get('action_modality', 'N/A')}")

        bill_result = {
            "golden_id": golden_id,
            "bill_name": bill_name,
            "difficulty": difficulty,
            "expected_relevant": expected_relevant,
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

            relevant_articles = find_relevant_articles(law, bill.get("summary", ""))
            logger.info(f"  ↔ {law_name} ({len(relevant_articles)}개 조문)")

            article_results = []
            for article in relevant_articles:
                art_ast_result = ast_parser.parse_article(article)
                if art_ast_result.get("skipped"):
                    continue

                art_ast = art_ast_result["ast"]
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

                c = nli_result.contradiction_score
                n = nli_result.nli_analysis.get("neutral_score", 0)
                logger.info(f"    제{art_ast_result['article_id']}조 "
                            f"C={c:.2f} N={n:.2f} [{nli_result.alert_level}]")

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
        bill_result["predicted_relevant"] = bill_result["max_contradiction"] >= threshold

        results.append(bill_result)

    # 캐시 저장
    ast_parser.save_cache()
    nli_evaluator.save_cache()

    # 통계
    elapsed = time.time() - start_time
    ast_stats = ast_parser.get_stats()
    nli_stats = nli_evaluator.get_stats()

    summary = {
        "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "threshold": threshold,
        "elapsed_seconds": round(elapsed, 1),
        "ast_stats": ast_stats,
        "nli_stats": nli_stats,
        "total_api_calls": ast_stats["api_call"] + nli_stats["api_call"],
        "results": results,
    }

    # 분류 지표 계산
    metrics = compute_metrics(results, threshold)
    summary["metrics"] = metrics

    # 결과 저장
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "golden_v3_test_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 결과 출력
    print_results(summary)

    return summary


def compute_metrics(results: List[Dict], threshold: float) -> Dict:
    """분류 성능 지표 계산"""
    tp = fp = tn = fn = 0

    for r in results:
        expected = r["expected_relevant"]
        predicted = r["max_contradiction"] >= threshold

        if expected and predicted:
            tp += 1
        elif expected and not predicted:
            fn += 1
        elif not expected and predicted:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(results) if results else 0.0

    return {
        "threshold": threshold,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }


def print_results(summary: Dict):
    """결과 출력"""
    results = summary["results"]
    metrics = summary["metrics"]
    threshold = summary["threshold"]

    print(f"\n{'='*90}")
    print(f"Golden Set V3 전체 테스트 결과 (모델: {summary['model']}, 임계값: {threshold})")
    print(f"{'='*90}")
    print(f"소요 시간: {summary['elapsed_seconds']}초")
    print(f"API 호출: AST {summary['ast_stats']['api_call']}건 + "
          f"NLI {summary['nli_stats']['api_call']}건 = "
          f"총 {summary['total_api_calls']}건")
    print()

    # 요약 테이블
    print(f"{'ID':<12} {'기대':<6} {'예측':<6} {'난이도':<8} {'최고C':<8} {'판정':<8} 법안명")
    print(f"{'-'*90}")

    for r in results:
        exp = "TP" if r["expected_relevant"] else "TN"
        pred = "P" if r["predicted_relevant"] else "N"
        score = r["max_contradiction"]

        # 분류 결과
        if r["expected_relevant"] and r["predicted_relevant"]:
            verdict = "TP OK"
        elif r["expected_relevant"] and not r["predicted_relevant"]:
            verdict = "FN !!"
        elif not r["expected_relevant"] and r["predicted_relevant"]:
            verdict = "FP !!"
        else:
            verdict = "TN OK"

        name = r["bill_name"][:35]
        print(f"{r['golden_id']:<12} {exp:<6} {pred:<6} {r['difficulty']:<8} "
              f"{score:<8.2f} {verdict:<8} {name}")

    # Confusion Matrix
    print(f"\n{'='*90}")
    print("Confusion Matrix")
    print(f"{'='*90}")
    m = metrics
    print(f"                  Predicted P    Predicted N")
    print(f"  Actual TP          {m['tp']:>3}            {m['fn']:>3}")
    print(f"  Actual TN          {m['fp']:>3}            {m['tn']:>3}")
    print()

    # 지표
    print(f"{'='*90}")
    print("분류 성능 지표")
    print(f"{'='*90}")
    print(f"  Threshold:  {m['threshold']}")
    print(f"  Precision:  {m['precision']:.4f}  (예측 P 중 실제 TP 비율)")
    print(f"  Recall:     {m['recall']:.4f}  (실제 TP 중 예측 P 비율)")
    print(f"  F1 Score:   {m['f1']:.4f}")
    print(f"  Accuracy:   {m['accuracy']:.4f}  ({m['tp']+m['tn']}/{m['tp']+m['fp']+m['tn']+m['fn']})")
    print()

    # 다중 임계값 분석
    print(f"{'='*90}")
    print("임계값별 성능 비교")
    print(f"{'='*90}")
    print(f"{'Threshold':<12} {'Precision':<12} {'Recall':<12} {'F1':<12} {'Accuracy':<12}")
    print(f"{'-'*60}")
    for t in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        tm = compute_metrics(results, t)
        print(f"{t:<12.1f} {tm['precision']:<12.4f} {tm['recall']:<12.4f} "
              f"{tm['f1']:<12.4f} {tm['accuracy']:<12.4f}")

    # 상세 결과 (주요 건만)
    print(f"\n{'='*90}")
    print("상세 결과 (FN/FP + 주요 충돌)")
    print(f"{'='*90}")

    for r in results:
        exp = r["expected_relevant"]
        pred = r["predicted_relevant"]
        score = r["max_contradiction"]

        # FN, FP, 또는 높은 충돌만 상세 출력
        is_error = (exp != pred)
        is_high = score >= 0.4
        if not (is_error or is_high):
            continue

        tag = "FN" if exp and not pred else ("FP" if not exp and pred else "OK")
        print(f"\n[{r['golden_id']}] [{tag}] {r['bill_name'][:55]}")
        print(f"  기대: {'관련' if exp else '무관'} | "
              f"예측: {'관련' if pred else '무관'} | "
              f"최고C: {score:.2f} | 난이도: {r['difficulty']}")
        print(f"  법안 AST: S={r['bill_ast']['subject'][:40]}")
        print(f"            A={r['bill_ast']['action'][:40]}")
        print(f"            M={r['bill_ast'].get('action_modality', 'N/A')}")

        for comp in r["comparisons"]:
            if comp["status"] != "evaluated":
                continue
            print(f"  ↔ {comp['law_name'][:40]} (최고C={comp['max_contradiction']:.2f})")
            for ar in comp.get("article_results", []):
                nli = ar["nli_analysis"]
                c = nli["contradiction_score"]
                if c >= 0.2 or is_error:
                    ca = ar.get("component_analysis", {})
                    ca_parts = []
                    if ca.get("subject"):
                        ca_parts.append(f"S={ca['subject'][:20]}")
                    if ca.get("action"):
                        ca_parts.append(f"A={ca['action'][:25]}")
                    ca_str = " | ".join(ca_parts) if ca_parts else ""
                    print(f"    제{ar['article_id']}조 [{ar['article_title'][:15]}] "
                          f"C={c:.2f} E={nli['entailment_score']:.2f} "
                          f"N={nli['neutral_score']:.2f} [{ar['alert_level']}]")
                    if ca_str:
                        print(f"      {ca_str}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Golden Set V3 전체 테스트")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        help="LLM 모델 (기본: gpt-4o-mini)")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="충돌 분류 임계값 (기본: 0.3)")

    args = parser.parse_args()
    run_full_test(model=args.model, threshold=args.threshold)
