"""
R&R 데이터 증강

원본 R&R + 소관 법령 목록 + 하부 조직명 병합
"""
import json
from pathlib import Path


def load_json(path: str) -> dict:
    """JSON 파일 로드"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def augment_rr_data():
    """R&R 데이터 증강"""
    data_dir = Path(__file__).parent.parent / "data"

    # 데이터 로드
    print("[1/4] 데이터 로드 중...")
    rr_data = load_json(data_dir / "ministry_rr.json")
    ministry_laws = load_json(data_dir / "ministry_laws.json")
    ministry_orgs = load_json(data_dir / "ministry_orgs.json")

    print(f"  - 부처 수: {rr_data['total_ministries'] + rr_data['total_pm_agencies']}개")
    print(f"  - 소관 법령 부처: {len(ministry_laws)}개")
    print(f"  - 하부 조직 부처: {len([k for k,v in ministry_orgs.items() if v])}개")

    # 증강 데이터 생성
    print("\n[2/4] R&R 데이터 증강 중...")
    augmented_ministries = []

    # 행정각부 처리
    for ministry in rr_data['ministries']:
        augmented = augment_single_ministry(ministry, ministry_laws, ministry_orgs)
        augmented_ministries.append(augmented)

    # 국무총리소속처 처리
    augmented_pm_agencies = []
    for agency in rr_data['pm_agencies']:
        augmented = augment_single_ministry(agency, ministry_laws, ministry_orgs)
        augmented_pm_agencies.append(augmented)

    # 결과 구성
    print("\n[3/4] 결과 구성 중...")
    result = {
        "source": "정부조직법 + 소관법령 + 직제",
        "augmentation_info": {
            "original": "ministry_rr.json",
            "laws_source": "ministry_laws.json",
            "orgs_source": "ministry_orgs.json",
        },
        "total_ministries": len(augmented_ministries),
        "total_pm_agencies": len(augmented_pm_agencies),
        "ministries": augmented_ministries,
        "pm_agencies": augmented_pm_agencies,
    }

    # 저장
    print("\n[4/4] 저장 중...")
    output_path = data_dir / "ministry_rr_augmented.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")

    # 통계 출력
    print("\n" + "=" * 60)
    print("증강 결과 통계")
    print("=" * 60)
    for ministry in augmented_ministries[:5]:
        print(f"\n{ministry['ministry_name']}:")
        print(f"  - 원본 R&R: {len(ministry['rr_text'])}자")
        print(f"  - 소관 법령: {len(ministry['laws'])}개")
        print(f"  - 하부 조직: {len(ministry['orgs'])}개")
        print(f"  - 증강 텍스트: {len(ministry['augmented_text'])}자")

    return result


def augment_single_ministry(ministry: dict, ministry_laws: dict, ministry_orgs: dict) -> dict:
    """단일 부처 R&R 증강"""
    ministry_name = ministry['ministry_name']
    original_rr = ministry['rr_text']

    # 소관 법령 가져오기
    laws = ministry_laws.get(ministry_name, [])

    # 하부 조직 가져오기
    orgs = ministry_orgs.get(ministry_name, [])

    # 증강 텍스트 생성
    augmented_parts = [original_rr]

    if laws:
        laws_text = f"\n[소관법령] {', '.join(laws[:30])}"  # 최대 30개
        if len(laws) > 30:
            laws_text += f" 외 {len(laws) - 30}개"
        augmented_parts.append(laws_text)

    if orgs:
        orgs_text = f"\n[조직] {', '.join(orgs[:30])}"  # 최대 30개
        if len(orgs) > 30:
            orgs_text += f" 외 {len(orgs) - 30}개"
        augmented_parts.append(orgs_text)

    augmented_text = ''.join(augmented_parts)

    return {
        "id": ministry['id'],
        "article_num": ministry['article_num'],
        "ministry_name": ministry_name,
        "type": ministry['type'],
        "rr_text": original_rr,
        "duties": ministry.get('duties', []),
        "laws": laws,
        "orgs": orgs,
        "augmented_text": augmented_text,
    }


if __name__ == "__main__":
    augment_rr_data()
