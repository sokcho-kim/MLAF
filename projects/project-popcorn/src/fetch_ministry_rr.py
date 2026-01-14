# -*- coding: utf-8 -*-
"""
정부조직법 기반 부처 R&R(업무분장) 수집

정부조직법 개정(2025.10.1)에 맞춰 조문 제목에서 부처명 자동 추출
"""
import json
import re
import sys
from pathlib import Path

# 상위 MLAF 모듈 import를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.parser.moleg_api import search_law, fetch_law_detail, parse_law_xml

# 부처 조문 범위 (제30조~제47조가 행정각부)
MINISTRY_ARTICLE_RANGE = range(30, 48)

# 국무총리 소속 처 (제26조~제28조)
PM_AGENCY_RANGE = range(26, 29)


def fetch_government_organization_act() -> dict:
    """정부조직법 가져오기"""
    print("[1/3] 정부조직법 검색 중...")
    laws = search_law("정부조직법")

    if not laws:
        raise ValueError("정부조직법을 찾을 수 없습니다")

    gov_act = None
    for law in laws:
        if law['name'] == '정부조직법':
            gov_act = law
            break

    if not gov_act:
        gov_act = laws[0]

    print(f"  - 법령일련번호: {gov_act['mst']}")
    print(f"  - 시행일자: {gov_act['enforcement_date']}")

    print("[2/3] 법령 상세 정보 가져오는 중...")
    xml_text = fetch_law_detail(gov_act['mst'])

    print("[3/3] XML 파싱 중...")
    result = parse_law_xml(xml_text)

    return result


def extract_ministry_rr(law_data: dict) -> list[dict]:
    """부처별 R&R 추출 - 조문 제목에서 부처명 자동 추출"""
    ministry_rr_list = []

    for article in law_data['articles']:
        article_num = article['article_num']

        # 행정각부 조문만 처리 (제30조~제47조)
        if article_num not in MINISTRY_ARTICLE_RANGE:
            # 국무총리 소속 처도 포함 (제26조~제28조)
            if article_num not in PM_AGENCY_RANGE:
                continue

        # 조문 제목에서 부처명 추출
        ministry_name = article.get('title', '').strip()
        if not ministry_name:
            continue

        # 소관사무 텍스트 수집
        rr_texts = []

        # 조문 내용
        if article['content']:
            rr_texts.append(article['content'])

        # 항별 내용
        for para in article['paragraphs']:
            if para['content']:
                rr_texts.append(para['content'])

            # 호별 내용
            for item in para.get('children', []):
                if item['content']:
                    rr_texts.append(f"  {item['number']}. {item['content']}")

                for subitem in item.get('children', []):
                    if subitem['content']:
                        rr_texts.append(f"    {subitem['number']}. {subitem['content']}")

        rr_full_text = "\n".join(rr_texts)

        # 장관 소관사무 추출 (1항에서)
        duties = extract_duties(article)

        ministry_rr = {
            "id": f"ministry_{article_num}",
            "article_num": article_num,
            "ministry_name": ministry_name,
            "rr_text": rr_full_text,
            "duties": duties,  # 핵심 소관사무 목록
            "type": "pm_agency" if article_num in PM_AGENCY_RANGE else "ministry"
        }

        ministry_rr_list.append(ministry_rr)
        print(f"  - 제{article_num}조: {ministry_name} (소관사무 {len(duties)}개)")

    return ministry_rr_list


def extract_duties(article: dict) -> list[str]:
    """
    장관 소관사무 추출
    예: "○○부장관은 A, B, C에 관한 사무를 관장한다" → [A, B, C]
    """
    duties = []

    # 1항 내용에서 추출
    for para in article['paragraphs']:
        if para['number'] == 1:
            content = para['content']
            # "~에 관한 사무를 관장한다" 패턴
            match = re.search(r'장관은\s+(.+?)에\s+관한\s+사무를\s+관장한다', content)
            if match:
                duty_text = match.group(1)
                # 쉼표나 가운뎃점으로 분리
                items = re.split(r'[,·ㆍ]', duty_text)
                for item in items:
                    item = item.strip()
                    if item:
                        duties.append(item)
            break

    # 1항이 없으면 조문 내용에서 추출
    if not duties and article['content']:
        content = article['content']
        match = re.search(r'장관은\s+(.+?)에\s+관한\s+사무를\s+관장한다', content)
        if match:
            duty_text = match.group(1)
            items = re.split(r'[,·ㆍ]', duty_text)
            for item in items:
                item = item.strip()
                if item:
                    duties.append(item)

    return duties


def main():
    """메인 실행"""
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "ministry_rr.json"

    # 정부조직법 가져오기
    law_data = fetch_government_organization_act()
    print(f"\n총 {law_data['total_articles']}개 조문 파싱 완료")

    # 부처별 R&R 추출
    print("\n[부처별 R&R 추출]")
    ministry_rr_list = extract_ministry_rr(law_data)

    # 행정각부만 필터링
    ministries_only = [m for m in ministry_rr_list if m['type'] == 'ministry']
    pm_agencies = [m for m in ministry_rr_list if m['type'] == 'pm_agency']

    # 결과 저장
    result = {
        "source": "정부조직법",
        "law_info": law_data['info'],
        "total_ministries": len(ministries_only),
        "total_pm_agencies": len(pm_agencies),
        "ministries": ministries_only,
        "pm_agencies": pm_agencies
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n완료! 저장 위치: {output_path}")
    print(f"행정각부: {len(ministries_only)}개")
    print(f"국무총리 소속 처: {len(pm_agencies)}개")

    # 샘플 출력
    print("\n=== 행정각부 목록 ===")
    for m in ministries_only:
        duties_preview = ", ".join(m['duties'][:3]) if m['duties'] else "(추출 안됨)"
        print(f"  제{m['article_num']}조 {m['ministry_name']}: {duties_preview}")

    return result


if __name__ == "__main__":
    main()
