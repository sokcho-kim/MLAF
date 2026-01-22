"""
지식그래프 프로토타입

Cross-Domain Radar v2를 위한 지식그래프 기반 스코어링

기능:
- 법안 제목에서 법률명 추출
- 법률-부처 매핑
- NetworkX 그래프 구축
- KG 스코어 계산
"""
import re
import json
import networkx as nx
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass


# 경로 설정
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"


# ============================================================
# 1. 법률명 추출
# ============================================================

def extract_law_name(bill_title: str) -> Optional[str]:
    """
    법안 제목에서 개정 대상 법률명 추출

    Args:
        bill_title: 법안 제목 (예: "에너지법 일부개정법률안(홍길동의원 등 10인)")

    Returns:
        법률명 (예: "에너지법") 또는 None (추출 실패 시)

    Examples:
        >>> extract_law_name("에너지법 일부개정법률안")
        "에너지법"
        >>> extract_law_name("정보통신망 이용촉진 및 정보보호 등에 관한 법률 일부개정법률안")
        "정보통신망 이용촉진 및 정보보호 등에 관한 법률"
        >>> extract_law_name("혐오표현 규제 법률안")  # 신규 제정
        None
    """
    # 패턴: "XXX법" 또는 "XXX법률" + "일부/전부개정법률안"
    pattern = r'^(.+(?:법률|법))\s*(일부|전부)?개정법률안'
    match = re.match(pattern, bill_title)

    if match:
        return match.group(1).strip()

    return None


def extract_bill_type(bill_title: str) -> str:
    """
    법안 유형 분류

    Returns:
        "일부개정", "전부개정", "폐지", "제정", "기타"
    """
    if "일부개정" in bill_title:
        return "일부개정"
    elif "전부개정" in bill_title:
        return "전부개정"
    elif "폐지" in bill_title:
        return "폐지"
    elif "법률안" in bill_title and "개정" not in bill_title:
        return "제정"
    else:
        return "기타"


# ============================================================
# 2. 데이터 로더
# ============================================================

def load_bills(file_path: Path = None) -> List[Dict]:
    """법안 데이터 로드"""
    if file_path is None:
        file_path = DATA_DIR / "bills_merged.json"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("bills", [])


def load_ministry_laws(file_path: Path = None) -> Dict[str, List[Dict]]:
    """부처별 소관 법률 로드"""
    if file_path is None:
        file_path = DATA_DIR / "ministry_laws.json"

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_law_to_ministry_map(ministry_laws: Dict) -> Dict[str, List[str]]:
    """
    법률명 → 소관 부처 매핑 생성

    Returns:
        {"에너지법": ["산업통상부"], "지방세법": ["행정안전부"], ...}
    """
    law_to_ministry = {}

    for ministry, laws in ministry_laws.items():
        for law in laws:
            # law가 문자열인 경우 (법률명 직접) 또는 딕셔너리인 경우
            if isinstance(law, str):
                law_name = law
            else:
                law_name = law.get("name", "")

            if law_name:
                if law_name not in law_to_ministry:
                    law_to_ministry[law_name] = []
                if ministry not in law_to_ministry[law_name]:
                    law_to_ministry[law_name].append(ministry)

    return law_to_ministry


# ============================================================
# 3. 법률명 매칭 (Fuzzy)
# ============================================================

def normalize_law_name(name: str) -> str:
    """법률명 정규화 (매칭용)"""
    # 공백 제거, 소문자화
    normalized = name.replace(" ", "").lower()
    # "에관한법률" → "법" 변환은 하지 않음 (너무 aggressive)
    return normalized


def find_matching_law(extracted_name: str, law_to_ministry: Dict[str, List[str]]) -> Optional[str]:
    """
    추출된 법률명과 매칭되는 실제 법률 찾기

    Args:
        extracted_name: 법안에서 추출한 법률명
        law_to_ministry: 법률명 → 부처 매핑

    Returns:
        매칭된 법률명 또는 None
    """
    # 1. 정확히 일치
    if extracted_name in law_to_ministry:
        return extracted_name

    # 2. 정규화 후 일치
    normalized_extracted = normalize_law_name(extracted_name)
    for law_name in law_to_ministry.keys():
        if normalize_law_name(law_name) == normalized_extracted:
            return law_name

    # 3. 부분 일치 (추출된 이름이 실제 법률명에 포함)
    for law_name in law_to_ministry.keys():
        if extracted_name in law_name or law_name in extracted_name:
            return law_name

    return None


# ============================================================
# 4. NetworkX 그래프 구축
# ============================================================

@dataclass
class KnowledgeGraph:
    """지식그래프 래퍼"""
    graph: nx.DiGraph
    law_to_ministry: Dict[str, List[str]]
    bill_to_law: Dict[str, str]  # bill_id → law_name

    def get_ministry_for_bill(self, bill_id: str) -> List[str]:
        """법안의 소관 부처 찾기"""
        law_name = self.bill_to_law.get(bill_id)
        if not law_name:
            return []
        return self.law_to_ministry.get(law_name, [])

    def has_path_to_ministry(self, bill_id: str, ministry: str) -> bool:
        """법안 → 부처 경로 존재 여부"""
        ministries = self.get_ministry_for_bill(bill_id)
        # 부처명 유연하게 매칭 (산업통상부 ↔ 산업통상자원부)
        for m in ministries:
            if ministry in m or m in ministry:
                return True
        return False

    def get_path_to_ministry(self, bill_id: str, ministry: str) -> Optional[List[str]]:
        """법안 → 부처 경로 반환"""
        law_name = self.bill_to_law.get(bill_id)
        if not law_name:
            return None

        ministries = self.law_to_ministry.get(law_name, [])
        for m in ministries:
            if ministry in m or m in ministry:
                return [bill_id, law_name, m]

        return None


def build_knowledge_graph(bills: List[Dict], ministry_laws: Dict) -> KnowledgeGraph:
    """
    지식그래프 구축

    노드:
        - Bill: 법안
        - Law: 법률
        - Ministry: 부처

    엣지:
        - Bill -[AMENDS]-> Law
        - Law -[GOVERNED_BY]-> Ministry
    """
    G = nx.DiGraph()

    # 법률 → 부처 매핑
    law_to_ministry = build_law_to_ministry_map(ministry_laws)

    # 부처 노드 추가
    for ministry in ministry_laws.keys():
        G.add_node(ministry, type="Ministry")

    # 법률 노드 및 Law → Ministry 엣지 추가
    for law_name, ministries in law_to_ministry.items():
        G.add_node(law_name, type="Law")
        for ministry in ministries:
            G.add_edge(law_name, ministry, relation="GOVERNED_BY")

    # 법안 노드 및 Bill → Law 엣지 추가
    bill_to_law = {}

    for bill in bills:
        bill_id = bill.get("bill_id", "")
        bill_title = bill.get("bill_name", "")

        if not bill_id:
            continue

        G.add_node(bill_id, type="Bill", title=bill_title)

        # 법률명 추출 및 매칭
        extracted_law = extract_law_name(bill_title)
        if extracted_law:
            matched_law = find_matching_law(extracted_law, law_to_ministry)
            if matched_law:
                G.add_edge(bill_id, matched_law, relation="AMENDS")
                bill_to_law[bill_id] = matched_law

    return KnowledgeGraph(
        graph=G,
        law_to_ministry=law_to_ministry,
        bill_to_law=bill_to_law
    )


# ============================================================
# 5. KG 스코어 계산
# ============================================================

def calculate_kg_score(
    bill_id: str,
    ministry: str,
    kg: KnowledgeGraph
) -> Tuple[float, Optional[List[str]]]:
    """
    지식그래프 기반 스코어 계산

    Args:
        bill_id: 법안 ID
        ministry: 타겟 부처
        kg: 지식그래프

    Returns:
        (score, path): 스코어 (0.0 ~ 1.0)와 경로
    """
    path = kg.get_path_to_ministry(bill_id, ministry)

    if path:
        # 직접 연결: 1.0
        return 1.0, path
    else:
        # 연결 없음: 0.0
        return 0.0, None


# ============================================================
# 6. 통합 분석
# ============================================================

def analyze_bills(bills: List[Dict], ministry_laws: Dict) -> Dict:
    """
    전체 법안 분석

    Returns:
        분석 결과 딕셔너리
    """
    kg = build_knowledge_graph(bills, ministry_laws)

    results = {
        "total_bills": len(bills),
        "law_extracted": 0,
        "law_matched": 0,
        "by_type": {},
        "matched_bills": [],
        "unmatched_bills": [],
    }

    for bill in bills:
        bill_id = bill.get("bill_id", "")
        bill_title = bill.get("bill_name", "")
        bill_type = extract_bill_type(bill_title)

        # 유형별 카운트
        results["by_type"][bill_type] = results["by_type"].get(bill_type, 0) + 1

        # 법률명 추출
        extracted_law = extract_law_name(bill_title)
        if extracted_law:
            results["law_extracted"] += 1

            # 매칭
            if bill_id in kg.bill_to_law:
                results["law_matched"] += 1
                results["matched_bills"].append({
                    "bill_id": bill_id,
                    "title": bill_title[:50],
                    "law": kg.bill_to_law[bill_id],
                    "ministries": kg.get_ministry_for_bill(bill_id)
                })
            else:
                results["unmatched_bills"].append({
                    "bill_id": bill_id,
                    "title": bill_title[:50],
                    "extracted_law": extracted_law
                })

    return results


# ============================================================
# CLI
# ============================================================

def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(description="지식그래프 프로토타입")
    parser.add_argument("--analyze", action="store_true", help="전체 법안 분석")
    parser.add_argument("--bill", type=str, help="특정 법안 분석 (bill_id)")
    parser.add_argument("--ministry", type=str, default="산업통상부", help="타겟 부처")

    args = parser.parse_args()

    # 데이터 로드
    print("데이터 로드 중...")
    bills = load_bills()
    ministry_laws = load_ministry_laws()

    print(f"  법안: {len(bills)}건")
    print(f"  부처: {len(ministry_laws)}개")

    if args.analyze:
        print("\n전체 법안 분석 중...")
        results = analyze_bills(bills, ministry_laws)

        print(f"\n=== 분석 결과 ===")
        print(f"총 법안: {results['total_bills']}건")
        print(f"법률명 추출: {results['law_extracted']}건 ({results['law_extracted']/results['total_bills']*100:.1f}%)")
        print(f"법률 매칭: {results['law_matched']}건 ({results['law_matched']/results['total_bills']*100:.1f}%)")

        print(f"\n유형별 분포:")
        for t, cnt in sorted(results["by_type"].items(), key=lambda x: -x[1]):
            print(f"  {t}: {cnt}건")

        print(f"\n매칭 성공 예시 (5건):")
        for m in results["matched_bills"][:5]:
            print(f"  - {m['title']}...")
            print(f"    → {m['law']} → {m['ministries']}")

        print(f"\n매칭 실패 예시 (5건):")
        for m in results["unmatched_bills"][:5]:
            print(f"  - {m['title']}...")
            print(f"    → 추출: {m['extracted_law']} (매칭 실패)")

    elif args.bill:
        # 지식그래프 구축
        kg = build_knowledge_graph(bills, ministry_laws)

        # 특정 법안 분석
        score, path = calculate_kg_score(args.bill, args.ministry, kg)

        print(f"\n=== 법안 분석 ===")
        print(f"법안 ID: {args.bill}")
        print(f"타겟 부처: {args.ministry}")
        print(f"KG 스코어: {score}")
        print(f"경로: {' → '.join(path) if path else '없음'}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
