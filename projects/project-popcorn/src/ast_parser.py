"""
AST 파서 모듈 (LLM 기반)

Task #8: 법률/법안 텍스트를 AST(Abstract Syntax Tree) 형태로 분해

AST 노드:
  - Subject: 적용 주체 (누구에게)
  - Condition: 발동 조건 (어떤 상황에서)
  - Action: 의무/금지/허용 등의 행위 (무엇을)
  - Exception: 예외 조항

Usage:
    from ast_parser import ASTParser

    parser = ASTParser()

    # 단건 파싱
    ast = parser.parse_article("제4조(국가 등의 책무) ① 국가는 ...")

    # 법안 요약 파싱
    ast = parser.parse_bill_summary("제안이유 및 주요내용 ...")

    # 배치 파싱 (기존 법률 조문)
    results = parser.parse_articles_batch(articles)
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# 경로 설정
PROJECT_DIR = Path(__file__).parent.parent
CACHE_DIR = PROJECT_DIR / "data" / "cache"


# ============================================================
# AST 데이터 구조
# ============================================================

@dataclass
class LawAST:
    """법률 조문의 AST 표현"""
    subject: str        # 적용 주체
    condition: str      # 발동 조건
    action: str         # 의무/금지/허용 행위
    exception: str      # 예외 조항
    action_modality: str  # 의무|금지|허용|신고|인가/허가|선언|벌칙|Not Specified

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "LawAST":
        return cls(
            subject=d.get("subject", "Not Specified"),
            condition=d.get("condition", "Not Specified"),
            action=d.get("action", "Not Specified"),
            exception=d.get("exception", "Not Specified"),
            action_modality=d.get("action_modality", "Not Specified"),
        )


# ============================================================
# 시스템 프롬프트
# ============================================================

PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """당신은 최고 수준의 AI 법률 데이터 엔지니어입니다.

주어진 법률 조문 또는 법안 요약을 분석하여 5가지 핵심 노드로 분해하세요.

## 한국 법률 조문 유형 가이드 (도메인 지식)

한국 법률 조문은 다음 유형으로 구분됩니다:
- **실체 규정**: 구체적 의무/금지/허용/신고/인가 등 행위를 정하는 조문 (예: 제5조, 제17조)
- **정의 조항(제2조)**: 용어를 정의하는 선언형 조문. 구체적 행위 규제가 없음.
- **목적 조항(제1조)**: 법률의 입법 목적을 선언. 구체적 행위 규제가 없음.
- **기본이념 조항**: 법률의 기본 원칙을 선언. 구체적 행위 규제가 없음.

정의조·목적조·기본이념 조항은 action_modality를 반드시 "선언"으로 분류하세요.

## AST 노드 정의

1. **Subject** (적용 주체): 이 조문이 적용되는 대상.
   예: "에너지 사업자", "산업통상자원부장관", "5인 이상 사업장의 사업주"

2. **Condition** (발동 조건): 이 조문이 작동하는 상황이나 전제.
   예: "에너지를 공급하려는 경우", "중대재해가 발생한 때"

3. **Action** (행위): 구체적 행위 내용.
   예: "인가를 받아야 한다", "신고하여야 한다"

4. **Exception** (예외 조항): 적용이 배제되는 경우.
   예: "대통령령으로 정하는 경우는 제외한다"

5. **Action_modality** (행위 유형): 아래 8개 값 중 하나로 분류:
   - 의무: "~해야 한다", "~하여야 한다"
   - 금지: "~할 수 없다", "~해서는 아니 된다"
   - 허용: "~할 수 있다"
   - 신고: "~을 신고하여야 한다"
   - 인가/허가: "~의 인가(허가)를 받아야 한다"
   - 선언: 정의조, 목적조, 기본이념 등 행위 규제 없는 조문
   - 벌칙: 위반 시 제재(벌금, 징역 등)
   - Not Specified: 위 분류에 해당하지 않는 경우

정보가 텍스트에 명시되어 있지 않으면 "Not Specified"로 기재합니다.
조문에 여러 항이 있으면, 가장 핵심적인 규정(주된 의무/금지/허용)을 기준으로 분해합니다.
법안 요약(제안이유 및 주요내용)이 입력된 경우, 개정의 핵심 내용을 기준으로 분해합니다.

## Few-shot 예시

### 예시 1: 실체 규정 (에너지법 제5조 — 에너지 기본계획)
입력: "① 산업통상자원부장관은 20년을 계획기간으로 하는 에너지기본계획을 5년마다 수립·시행하여야 한다."
출력:
{
  "subject": "산업통상자원부장관",
  "condition": "20년 계획기간, 5년마다",
  "action": "에너지기본계획을 수립·시행하여야 한다",
  "exception": "Not Specified",
  "action_modality": "의무"
}

### 예시 2: 정의 조항 (에너지법 제2조 — 정의)
입력: "이 법에서 사용하는 용어의 뜻은 다음과 같다. 1. '에너지'란 연료·열 및 전기를 말한다. ..."
출력:
{
  "subject": "Not Specified",
  "condition": "Not Specified",
  "action": "Not Specified",
  "exception": "Not Specified",
  "action_modality": "선언"
}

## 출력 형식

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요:

{
  "subject": "적용 주체",
  "condition": "발동 조건",
  "action": "행위",
  "exception": "예외 조항",
  "action_modality": "의무|금지|허용|신고|인가/허가|선언|벌칙|Not Specified"
}"""


# ============================================================
# AST 파서
# ============================================================

class ASTParser:
    """LLM 기반 법률 AST 파서"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        cache_path: Optional[Path] = None,
        temperature: float = 0.0,
    ):
        """
        Args:
            model: OpenAI 모델명 (gpt-4o-mini 권장 - 비용 효율)
            cache_path: AST 캐시 파일 경로
            temperature: LLM 온도 (0.0 = 결정적)
        """
        self.model = model
        self.temperature = temperature
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.cache_path = cache_path or (CACHE_DIR / "ast_cache.json")
        self._cache: Dict[str, Dict] = {}
        self._load_cache()

        # 통계
        self.stats = {"cache_hit": 0, "api_call": 0, "parse_error": 0}

    # ---- 캐시 관리 ----

    def _cache_key(self, text: str) -> str:
        """텍스트 → 캐시 키"""
        return hashlib.md5(f"{self.model}:{PROMPT_VERSION}:{text}".encode()).hexdigest()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.info(f"AST 캐시 로드: {len(self._cache)}건")

    def save_cache(self) -> None:
        """캐시를 디스크에 저장"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)
        logger.debug(f"AST 캐시 저장: {len(self._cache)}건")

    # ---- 핵심 파싱 ----

    def _call_llm(self, text: str) -> Dict:
        """LLM API 호출 → AST JSON 반환"""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )

        content = response.choices[0].message.content
        return json.loads(content)

    def parse_text(self, text: str, use_cache: bool = True) -> LawAST:
        """텍스트를 AST로 파싱

        Args:
            text: 법률 조문 또는 법안 요약
            use_cache: 캐시 사용 여부

        Returns:
            LawAST 객체
        """
        # 캐시 확인
        if use_cache:
            key = self._cache_key(text)
            if key in self._cache:
                self.stats["cache_hit"] += 1
                return LawAST.from_dict(self._cache[key])

        # LLM 호출
        try:
            result = self._call_llm(text)
            self.stats["api_call"] += 1
        except Exception as e:
            logger.error(f"LLM 호출 실패: {e}")
            self.stats["parse_error"] += 1
            return LawAST(
                subject="Parse Error",
                condition="Parse Error",
                action="Parse Error",
                exception="Parse Error",
                action_modality="Not Specified",
            )

        ast = LawAST.from_dict(result)

        # 캐시 저장
        if use_cache:
            self._cache[key] = ast.to_dict()

        return ast

    # ---- 편의 메서드 ----

    def parse_article(self, article: Dict) -> Dict:
        """법률 조문 딕셔너리 → AST 포함 결과

        Args:
            article: 법제처 API에서 가져온 조문 딕셔너리
                     (article_id, title, content, paragraphs 포함)

        Returns:
            원본 정보 + AST가 추가된 딕셔너리
        """
        # 조문 텍스트 조합: 본문 + 항 내용
        text_parts = []

        content = article.get("content", "")
        if content:
            text_parts.append(content)

        for para in article.get("paragraphs", []):
            para_content = para.get("content", "")
            if para_content:
                text_parts.append(para_content)
            for item in para.get("children", []):
                item_content = item.get("content", "")
                if item_content:
                    text_parts.append(f"  {item_content}")

        full_text = "\n".join(text_parts)

        # 빈 조문 또는 삭제된 조문 건너뛰기
        if not full_text.strip() or "삭제" in full_text[:20]:
            return {
                "article_id": article.get("article_id", ""),
                "title": article.get("title", ""),
                "text": full_text,
                "ast": LawAST(
                    subject="Not Applicable",
                    condition="Not Applicable",
                    action="삭제된 조문",
                    exception="Not Applicable",
                    action_modality="Not Specified",
                ).to_dict(),
                "skipped": True,
            }

        ast = self.parse_text(full_text)

        return {
            "article_id": article.get("article_id", ""),
            "title": article.get("title", ""),
            "text": full_text[:200],  # 저장 시 텍스트 요약
            "ast": ast.to_dict(),
            "skipped": False,
        }

    def parse_bill_summary(self, bill: Dict) -> Dict:
        """법안 요약 → AST

        Args:
            bill: 법안 딕셔너리 (bill_name, summary 포함)

        Returns:
            법안 정보 + AST
        """
        title = bill.get("bill_name", "")
        summary = bill.get("summary", "")

        # 제목 + 요약 결합
        if summary:
            text = f"[법안명] {title}\n\n[제안이유 및 주요내용]\n{summary}"
        else:
            text = f"[법안명] {title}"

        # 요약이 너무 길면 앞 3000자만 (토큰 절약)
        text = text[:3000]

        ast = self.parse_text(text)

        return {
            "bill_id": bill.get("bill_id", ""),
            "bill_name": title,
            "ast": ast.to_dict(),
        }

    def parse_articles_batch(
        self,
        articles: List[Dict],
        show_progress: bool = True,
    ) -> List[Dict]:
        """조문 리스트 배치 파싱

        Args:
            articles: 조문 딕셔너리 리스트
            show_progress: 진행 출력

        Returns:
            AST 포함 결과 리스트
        """
        results = []
        total = len(articles)

        for i, article in enumerate(articles, 1):
            result = self.parse_article(article)
            results.append(result)

            if show_progress and i % 10 == 0:
                logger.info(f"  AST 파싱: {i}/{total} "
                            f"(캐시: {self.stats['cache_hit']}, "
                            f"API: {self.stats['api_call']})")

        # 배치 완료 후 캐시 저장
        self.save_cache()

        if show_progress:
            logger.info(f"  AST 파싱 완료: {total}건 "
                        f"(캐시: {self.stats['cache_hit']}, "
                        f"API: {self.stats['api_call']}, "
                        f"오류: {self.stats['parse_error']})")

        return results

    def get_stats(self) -> Dict:
        """통계 반환"""
        return dict(self.stats)


# ============================================================
# CLI
# ============================================================

def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="법률 AST 파서")
    parser.add_argument("--test-article", action="store_true",
                        help="에너지법 조문 테스트")
    parser.add_argument("--test-bill", action="store_true",
                        help="Golden Set 법안 테스트")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        help="LLM 모델 (기본: gpt-4o-mini)")

    args = parser.parse_args()

    ast_parser = ASTParser(model=args.model)

    if args.test_article:
        # 에너지법 제4조 테스트
        law_texts_path = PROJECT_DIR / "data" / "law_texts" / "산업통상부_laws.json"
        with open(law_texts_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 에너지법 찾기
        energy_law = None
        for law in data["laws"]:
            if law["law_name"] == "에너지법":
                energy_law = law
                break

        if not energy_law:
            print("에너지법을 찾을 수 없습니다")
            return

        # 제4조, 제5조 테스트
        test_articles = [a for a in energy_law["articles"]
                         if a["article_id"] in ("4", "5", "17")]

        print(f"\n=== 에너지법 조문 AST 파싱 (모델: {args.model}) ===\n")
        for article in test_articles:
            result = ast_parser.parse_article(article)
            print(f"--- 제{result['article_id']}조 [{result['title']}] ---")
            if result.get("skipped"):
                print("  (건너뜀: 삭제된 조문)")
                continue
            ast = result["ast"]
            print(f"  Subject:   {ast['subject']}")
            print(f"  Condition: {ast['condition']}")
            print(f"  Action:    {ast['action']}")
            print(f"  Exception: {ast['exception']}")
            print(f"  Modality:  {ast.get('action_modality', 'N/A')}")
            print()

        ast_parser.save_cache()
        print(f"통계: {ast_parser.get_stats()}")

    elif args.test_bill:
        # Golden Set 법안 테스트
        golden_path = PROJECT_DIR / "data" / "golden_set_v2.json"
        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)

        print(f"\n=== Golden Set 법안 AST 파싱 (모델: {args.model}) ===\n")
        for bill in golden["bills"][:2]:  # 처음 2건만
            result = ast_parser.parse_bill_summary(bill)
            print(f"--- {result['bill_name'][:50]} ---")
            print(f"  난이도: {bill['difficulty']}")
            ast = result["ast"]
            print(f"  Subject:   {ast['subject']}")
            print(f"  Condition: {ast['condition']}")
            print(f"  Action:    {ast['action']}")
            print(f"  Exception: {ast['exception']}")
            print(f"  Modality:  {ast.get('action_modality', 'N/A')}")
            print()

        ast_parser.save_cache()
        print(f"통계: {ast_parser.get_stats()}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
