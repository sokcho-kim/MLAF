"""
NLI 평가 모듈

Task #9: 두 AST를 비교하여 Entailment/Contradiction/Neutral 스코어를 산출

Process:
  1. 기존 법률 AST + 신규 법안 AST를 입력받음
  2. LLM이 노드별 교차비교 (Subject, Condition, Action, Exception)
  3. NLI 스코어 산출: entailment + contradiction + neutral = 1.0
  4. reasoning으로 판단 근거 텍스트 생성

Usage:
    from nli_evaluator import NLIEvaluator

    evaluator = NLIEvaluator()
    result = evaluator.evaluate(existing_ast, new_bill_ast)
    # result["nli_analysis"]["contradiction_score"] >= 0.6 → 충돌 의심
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent
CACHE_DIR = PROJECT_DIR / "data" / "cache"


# ============================================================
# NLI 결과 구조
# ============================================================

@dataclass
class NLIResult:
    """NLI 평가 결과"""
    existing_law_AST: Dict
    new_bill_AST: Dict
    nli_analysis: Dict  # {entailment_score, contradiction_score, neutral_score}
    reasoning: str
    component_analysis: Dict  # {subject, condition, action, exception} 노드별 분석

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def contradiction_score(self) -> float:
        return self.nli_analysis.get("contradiction_score", 0.0)

    @property
    def entailment_score(self) -> float:
        return self.nli_analysis.get("entailment_score", 0.0)

    @property
    def alert_level(self) -> str:
        """충돌 점수 기반 알림 수준"""
        score = self.contradiction_score
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        elif score >= 0.2:
            return "LOW"
        return "NONE"


# ============================================================
# 시스템 프롬프트
# ============================================================

PROMPT_VERSION = "v3"

NLI_SYSTEM_PROMPT = """당신은 최고 수준의 AI 법률 데이터 엔지니어이자 자연어 추론(NLI) 전문가입니다.

주어진 [기존 법률 AST]와 [신규 법안 AST]를 비교 분석하여, 두 법안 간의 논리적 관계를 평가하세요.

⚠️ **핵심 원칙**: 규칙 1 또는 규칙 2가 적용되면 Action 비교 결과와 무관하게 해당 규칙의 스코어 ceiling을 반드시 적용하세요. Action 비교가 규칙 1/2를 절대 override할 수 없습니다.

## 선행 규칙 (Hard Rules) — 반드시 먼저 확인 (게이트 구조)

아래 규칙은 **게이트**입니다. 해당 시 즉시 스코어를 산출하고, 이후 Action 비교는 불필요합니다.

**규칙 1 (선언형 조문) [STOP]:** 어느 한쪽의 action_modality가 "선언"이면:
→ neutral ≥ 0.8, contradiction ≤ 0.1
→ 이유: 정의조·목적조·기본이념은 구체적 행위 규제가 없어 논리적 충돌이 발생할 수 없음.
→ **[STOP] 즉시 스코어 산출. Action 비교 불필요.**

**규칙 2 (주체 완전 불일치) [STOP]:** Subject가 완전히 다른 대상이면:
→ neutral ≥ 0.8, **contradiction ≤ 0.2**
→ 이유: 서로 다른 주체에 대한 규율은 논리적으로 충돌하지 않음.
→ **설령 action_modality가 "허용 vs 의무", "인가 vs 신고" 등으로 달라도** 주체가 다르면 충돌이 아닙니다.
→ **[STOP] 즉시 스코어 산출. Action 비교 불필요.**

규칙 2 판별 기준 (아래 중 하나라도 해당하면 "완전 불일치"):
  (a) 소관 부처가 상이 (예: 산업통상자원부장관 vs 보건복지부장관)
  (b) 업종/분야가 상이 (예: 에너지 사업자 vs 노인복지기관장)
  (c) 별개 기관 (예: 한국산업은행 vs 건강보험공단)

규칙 2 **비적용** (유사 주체로 간주):
  - "국가 또는 지방자치단체" vs "국가 및 지방자치단체" → 실질적으로 동일 주체
  - 상위개념 vs 하위개념 (예: "사업자" vs "에너지 사업자") → 유사 주체
  - 동일 조직의 다른 표현 (예: "산업통상자원부장관" vs "주무부장관") → 유사 주체

**규칙 3 (Not Specified 필드):** Subject/Condition/Action/Exception 중 어느 한쪽이 "Not Specified"이면:
→ 해당 노드 비교는 "무관"으로 처리. 충돌 근거로 사용 불가.

## 흔한 오류 — 반드시 피하세요

❌ **잘못된 판단**: 주체가 "산업통상자원부장관" vs "노인복지기관장"이고 action_modality가 "허용 vs 의무"라서 C=0.85 판정
→ 주체가 완전히 다른 부처/분야이므로 규칙 2 적용, **C≤0.2**가 맞습니다.

❌ **잘못된 판단**: 주체가 "에너지 사업자" vs "어린이집 원장"이고 의무 내용이 달라서 C=0.60 판정
→ 업종/분야가 완전히 달라 규칙 2 적용, **C≤0.2**가 맞습니다.

✅ **올바른 판단**: 주체가 "에너지 사업자" vs "에너지 사업자"이고 "인가 vs 신고"라서 C=0.85 판정
→ 동일 주체 + 동일 규제 영역에서 규제 수준 역전이므로 충돌이 맞습니다.

## 단계별 비교 절차

### Step 1: 선행 규칙 확인 (게이트)
- 규칙 1 → 해당 시 [STOP], 스코어 즉시 산출
- 규칙 2 → 해당 시 [STOP], 스코어 즉시 산출
- 규칙 3 → 해당 노드 "무관" 처리
- **규칙 1/2에 해당하면 Step 2를 건너뛰고 Step 3으로 이동**

### Step 2: 노드별 교차 비교 (규칙 1/2 미해당 시에만)

1. **Subject 비교** (최우선 게이트):
   - 동일/유사 주체 → "일치" 또는 "유사" → 나머지 노드 비교 진행
   - 완전히 다른 주체 → "불일치" → **나머지 노드(Condition, Action, Exception) 모두 "무관" 처리, C≤0.2**

2. **Condition 비교** (Subject 일치/유사 시에만):
   - 같은 상황 → "일치"
   - 다른 상황 → "불일치"

3. **Action 비교** (Subject 일치/유사 시에만):
   - 의무 vs 금지 → 강한 충돌 (Contradiction)
   - 인가/허가 vs 신고/허용 → 규제 수준 충돌 (**동일 주체 + 동일 규제 영역일 때만**)
   - 허용 vs 의무 → 규제 강도 차이 (**동일 주체 + 동일 규제 영역일 때만**)
   - 의무 강화 vs 의무 완화 → 방향 충돌
   - 동일한 의무/허용 → 부합 (Entailment)
   - 한쪽이 "선언" → 무관 (규칙 1 적용)

4. **Exception 비교** (Subject 일치/유사 시에만):
   - 예외 삭제 → 규제 강화 방향 충돌
   - 예외 추가 → 규제 완화

### Step 3: 종합 스코어 산출
노드별 비교 결과를 종합하여 최종 스코어를 산출합니다.
세 스코어(Entailment + Contradiction + Neutral)의 합은 반드시 1.0이어야 합니다.

스코어 ceiling 요약:
- 규칙 1 적용 시 → contradiction ≤ 0.1
- 규칙 2 적용 시 → contradiction ≤ 0.2
- Subject "불일치" 시 → contradiction ≤ 0.2

## 스코어 기준

- **Entailment** (부합): 신규 법안이 기존 법률의 방향과 일치하거나 강화
- **Contradiction** (충돌): 신규 법안이 기존 법률과 논리적으로 반대되거나 모순
- **Neutral** (무관): 두 법안 간에 의미있는 논리적 관계가 없음

## Few-shot 예시

### 예시 1: 충돌 — 동일 주체, 인가 vs 신고 (C=0.85)
[기존] Subject: 에너지 사업자 | Action: 인가를 받아야 한다 | Action_modality: 인가/허가
[신규] Subject: 에너지 사업자 | Action: 신고만으로 사업 개시 가능 | Action_modality: 신고
→ 동일 주체, 동일 상황에서 규제 수준이 역전됨.
출력: {"nli_analysis": {"entailment_score": 0.05, "contradiction_score": 0.85, "neutral_score": 0.10}, "component_analysis": {"subject": "일치", "condition": "유사", "action": "충돌 (인가→신고, 규제 수준 역전)", "exception": "무관"}, "reasoning": "[규칙 해당 없음] 동일 주체(에너지 사업자)에 대해 인가 의무가 신고로 완화되어 규제 수준이 역전됨."}

### 예시 2: 무관 — 주체 완전 불일치 + 허용 vs 의무 (N=0.90)
[기존] Subject: 산업통상자원부장관 | Action: 에너지 사업 허가를 할 수 있다 | Action_modality: 허용
[신규] Subject: 노인복지기관장 | Action: 노인복지 프로그램을 실시하여야 한다 | Action_modality: 의무
→ 주체 완전 불일치 (소관 부처 상이 + 업종/분야 상이) → 규칙 2 [STOP].
→ action_modality가 "허용 vs 의무"로 달라도 주체가 다르므로 충돌 아님.
출력: {"nli_analysis": {"entailment_score": 0.0, "contradiction_score": 0.10, "neutral_score": 0.90}, "component_analysis": {"subject": "불일치 (산업통상자원부장관 vs 노인복지기관장)", "condition": "무관 (규칙 2 적용)", "action": "무관 (규칙 2 적용 — 주체 불일치 시 Action 비교 무의미)", "exception": "무관"}, "reasoning": "[규칙 2 적용] 주체가 완전히 다른 부처/분야(산업통상자원부장관 vs 노인복지기관장)이므로 action_modality 차이(허용 vs 의무)와 무관하게 논리적 충돌 없음."}

### 예시 3: 무관(선언형) — 정의조 vs 의무 (N=0.9)
[기존] Subject: Not Specified | Action: Not Specified | Action_modality: 선언
[신규] Subject: 에너지 사업자 | Action: 신고 의무 | Action_modality: 신고
→ 기존이 선언형(정의조) → 규칙 1 [STOP].
출력: {"nli_analysis": {"entailment_score": 0.05, "contradiction_score": 0.05, "neutral_score": 0.90}, "component_analysis": {"subject": "무관 (선언형 조문)", "condition": "무관", "action": "무관 (선언형 vs 실체 규정)", "exception": "무관"}, "reasoning": "[규칙 1 적용] 기존 법률이 선언형 조문(정의조)으로 구체적 행위 규제가 없어 논리적 충돌 불가."}

### 예시 4: 무관 — 주체 완전 불일치 + 의무 vs 의무 (N=1.0)
[기존] Subject: 에너지 사업자 | Action: 안전관리규정을 준수하여야 한다 | Action_modality: 의무
[신규] Subject: 어린이집 원장 | Action: 안전교육을 실시하여야 한다 | Action_modality: 의무
→ 주체 완전 불일치 (업종/분야 상이) → 규칙 2 [STOP].
→ 둘 다 "의무"이고 "안전"이라는 키워드가 겹쳐도 주체와 규제 영역이 완전히 다르므로 충돌 아님.
출력: {"nli_analysis": {"entailment_score": 0.0, "contradiction_score": 0.0, "neutral_score": 1.0}, "component_analysis": {"subject": "불일치 (에너지 사업자 vs 어린이집 원장)", "condition": "무관 (규칙 2 적용)", "action": "무관 (규칙 2 적용 — 주체 불일치 시 Action 비교 무의미)", "exception": "무관"}, "reasoning": "[규칙 2 적용] 주체가 완전히 다른 분야(에너지 사업자 vs 어린이집 원장)이므로 양쪽 모두 안전 관련 의무이더라도 논리적 충돌 없음."}

## 출력 형식

반드시 아래 JSON 형식으로만 응답하세요. reasoning은 반드시 "[규칙 N 적용]" 또는 "[규칙 해당 없음]"으로 시작하세요:

{
  "nli_analysis": {
    "entailment_score": [0.0~1.0 float],
    "contradiction_score": [0.0~1.0 float],
    "neutral_score": [0.0~1.0 float]
  },
  "component_analysis": {
    "subject": "일치|유사|불일치 + 간단 설명",
    "condition": "일치|유사|불일치|무관 + 간단 설명",
    "action": "일치|충돌|무관 + 간단 설명",
    "exception": "일치|충돌|무관 + 간단 설명"
  },
  "reasoning": "[규칙 N 적용] 또는 [규칙 해당 없음] + 각 노드 비교와 적용된 규칙을 중심으로 3문장 이내 설명."
}"""


# ============================================================
# NLI 평가기
# ============================================================

class NLIEvaluator:
    """LLM 기반 NLI 평가기"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        cache_path: Optional[Path] = None,
        temperature: float = 0.0,
    ):
        self.model = model
        self.temperature = temperature
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.cache_path = cache_path or (CACHE_DIR / "nli_cache.json")
        self._cache: Dict[str, Dict] = {}
        self._load_cache()

        self.stats = {"cache_hit": 0, "api_call": 0, "parse_error": 0}

    # ---- 캐시 ----

    def _cache_key(self, existing_ast: Dict, new_ast: Dict) -> str:
        payload = json.dumps({"e": existing_ast, "n": new_ast}, sort_keys=True)
        return hashlib.md5(f"{self.model}:{PROMPT_VERSION}:{payload}".encode()).hexdigest()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.info(f"NLI 캐시 로드: {len(self._cache)}건")

    def save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    # ---- 핵심 평가 ----

    def _build_user_prompt(self, existing_ast: Dict, new_ast: Dict) -> str:
        """사용자 프롬프트 조합"""
        return f"""[기존 법률 AST]
Subject: {existing_ast.get('subject', 'N/A')}
Condition: {existing_ast.get('condition', 'N/A')}
Action: {existing_ast.get('action', 'N/A')}
Exception: {existing_ast.get('exception', 'N/A')}
Action_modality: {existing_ast.get('action_modality', 'Not Specified')}

[신규 법안 AST]
Subject: {new_ast.get('subject', 'N/A')}
Condition: {new_ast.get('condition', 'N/A')}
Action: {new_ast.get('action', 'N/A')}
Exception: {new_ast.get('exception', 'N/A')}
Action_modality: {new_ast.get('action_modality', 'Not Specified')}"""

    def _call_llm(self, existing_ast: Dict, new_ast: Dict) -> Dict:
        """LLM 호출 → NLI JSON 반환"""
        user_prompt = self._build_user_prompt(existing_ast, new_ast)

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": NLI_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        return json.loads(content)

    def evaluate(
        self,
        existing_ast: Dict,
        new_ast: Dict,
        use_cache: bool = True,
    ) -> NLIResult:
        """두 AST 비교 → NLI 결과

        Args:
            existing_ast: 기존 법률 조문의 AST {"subject", "condition", "action", "exception"}
            new_ast: 신규 법안의 AST (동일 구조)
            use_cache: 캐시 사용 여부

        Returns:
            NLIResult 객체
        """
        # 캐시 확인
        if use_cache:
            key = self._cache_key(existing_ast, new_ast)
            if key in self._cache:
                self.stats["cache_hit"] += 1
                cached = self._cache[key]
                return NLIResult(
                    existing_law_AST=existing_ast,
                    new_bill_AST=new_ast,
                    nli_analysis=cached["nli_analysis"],
                    reasoning=cached["reasoning"],
                    component_analysis=cached.get("component_analysis", {}),
                )

        # LLM 호출
        try:
            result = self._call_llm(existing_ast, new_ast)
            self.stats["api_call"] += 1
        except Exception as e:
            logger.error(f"NLI LLM 호출 실패: {e}")
            self.stats["parse_error"] += 1
            return NLIResult(
                existing_law_AST=existing_ast,
                new_bill_AST=new_ast,
                nli_analysis={
                    "entailment_score": 0.0,
                    "contradiction_score": 0.0,
                    "neutral_score": 1.0,
                },
                reasoning="LLM 호출 실패로 평가 불가",
                component_analysis={},
            )

        # 스코어 정규화 (합이 1.0이 되도록)
        nli = result.get("nli_analysis", {})
        total = (nli.get("entailment_score", 0) +
                 nli.get("contradiction_score", 0) +
                 nli.get("neutral_score", 0))
        if total > 0 and abs(total - 1.0) > 0.01:
            nli["entailment_score"] = round(nli.get("entailment_score", 0) / total, 2)
            nli["contradiction_score"] = round(nli.get("contradiction_score", 0) / total, 2)
            nli["neutral_score"] = round(1.0 - nli["entailment_score"] - nli["contradiction_score"], 2)

        component_analysis = result.get("component_analysis", {})

        nli_result = NLIResult(
            existing_law_AST=existing_ast,
            new_bill_AST=new_ast,
            nli_analysis=nli,
            reasoning=result.get("reasoning", ""),
            component_analysis=component_analysis,
        )

        # 캐시 저장
        if use_cache:
            self._cache[key] = {
                "nli_analysis": nli,
                "reasoning": nli_result.reasoning,
                "component_analysis": component_analysis,
            }

        return nli_result

    def evaluate_batch(
        self,
        pairs: list[tuple[Dict, Dict]],
        show_progress: bool = True,
    ) -> list[NLIResult]:
        """배치 NLI 평가

        Args:
            pairs: (existing_ast, new_ast) 튜플 리스트
            show_progress: 진행 출력

        Returns:
            NLIResult 리스트
        """
        results = []
        total = len(pairs)

        for i, (existing, new) in enumerate(pairs, 1):
            result = self.evaluate(existing, new)
            results.append(result)

            if show_progress and i % 5 == 0:
                logger.info(f"  NLI 평가: {i}/{total}")

        self.save_cache()

        if show_progress:
            logger.info(f"  NLI 평가 완료: {total}건 "
                        f"(캐시: {self.stats['cache_hit']}, "
                        f"API: {self.stats['api_call']})")

        return results

    def get_stats(self) -> Dict:
        return dict(self.stats)


# ============================================================
# CLI 테스트
# ============================================================

def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="NLI 평가기")
    parser.add_argument("--test", action="store_true", help="하드코딩 테스트")
    parser.add_argument("--model", type=str, default="gpt-4o-mini")

    args = parser.parse_args()

    if not args.test:
        parser.print_help()
        return

    evaluator = NLIEvaluator(model=args.model)

    # 테스트 케이스 1: 인가 vs 신고 (충돌 기대)
    existing_ast_1 = {
        "subject": "에너지 사업자",
        "condition": "에너지를 공급하려는 경우",
        "action": "산업통상자원부장관의 인가를 받아야 한다 (의무)",
        "exception": "Not Specified",
    }
    new_ast_1 = {
        "subject": "에너지 사업자",
        "condition": "에너지 사업을 개시하려는 경우",
        "action": "신고만으로 사업을 개시할 수 있다 (허용)",
        "exception": "대통령령으로 정하는 소규모 사업자에 한한다",
    }

    # 테스트 케이스 2: 무관 (Neutral 기대)
    existing_ast_2 = {
        "subject": "에너지 사업자",
        "condition": "에너지를 공급하려는 경우",
        "action": "산업통상자원부장관의 인가를 받아야 한다 (의무)",
        "exception": "Not Specified",
    }
    new_ast_2 = {
        "subject": "기후위기 취약계층 (노인, 영유아 등)",
        "condition": "기후위기로 인한 건강장해 위험이 큰 경우",
        "action": "보호·지원 대책 등을 수립하여야 한다 (의무)",
        "exception": "대통령령으로 정하는 계층은 제외",
    }

    print(f"\n=== NLI 평가 테스트 (모델: {args.model}) ===\n")

    # 케이스 1
    print("--- 케이스 1: 인가 vs 신고 (충돌 기대) ---")
    r1 = evaluator.evaluate(existing_ast_1, new_ast_1)
    nli1 = r1.nli_analysis
    print(f"  Entailment:    {nli1['entailment_score']}")
    print(f"  Contradiction: {nli1['contradiction_score']}")
    print(f"  Neutral:       {nli1['neutral_score']}")
    print(f"  Alert Level:   {r1.alert_level}")
    print(f"  Reasoning:     {r1.reasoning}")
    print()

    # 케이스 2
    print("--- 케이스 2: 에너지 사업 vs 기후위기 취약계층 (무관 기대) ---")
    r2 = evaluator.evaluate(existing_ast_2, new_ast_2)
    nli2 = r2.nli_analysis
    print(f"  Entailment:    {nli2['entailment_score']}")
    print(f"  Contradiction: {nli2['contradiction_score']}")
    print(f"  Neutral:       {nli2['neutral_score']}")
    print(f"  Alert Level:   {r2.alert_level}")
    print(f"  Reasoning:     {r2.reasoning}")
    print()

    evaluator.save_cache()
    print(f"통계: {evaluator.get_stats()}")


if __name__ == "__main__":
    main()
