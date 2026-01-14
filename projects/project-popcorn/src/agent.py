"""
LangGraph 워크플로우 에이전트

순차적 판단 로직: 감지 -> 조회 -> 작성
"""
from typing import TypedDict


class AgentState(TypedDict):
    """에이전트 상태"""
    bill_text: str
    risk_alerts: list
    legal_references: list
    report_draft: str


def create_agent():
    """LangGraph 에이전트 생성"""
    # TODO: LangGraph 워크플로우 구현
    # 1. detect_node: 리스크 감지
    # 2. retrieve_node: 국회법 조문/선례 조회
    # 3. generate_node: 보고서 초안 생성
    pass


if __name__ == "__main__":
    print("Agent module initialized")
