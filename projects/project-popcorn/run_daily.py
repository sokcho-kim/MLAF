#!/usr/bin/env python3
"""
Cross-Domain Radar 일배치 실행 스크립트

매일 실행하여:
1. 신규 법안 수집
2. Cross-Domain 스캔
3. 리포트 생성
4. 알림 발송 (Teams + 이메일)

사용법:
    python run_daily.py
    python run_daily.py --ministry 산업통상부
    python run_daily.py --since 2026-01-18
"""
import sys
import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# 경로 설정
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from src.ingest_daily import run_daily_ingest
from src.radar import CrossDomainRadar
from src.scorer_v2 import ScorerV2, MinistryConfig
from src.embedder import Embedder
from src.reporter import Reporter
from src.notifier import TeamsNotifier, notify_scan_result
from src.notifier_email import EmailNotifier, notify_scan_result_email

# 디렉토리
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"
LOG_DIR = PROJECT_DIR / "logs"


def log(message: str):
    """로그 출력"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def run_daily_pipeline(
    ministry: str = "산업통상부",
    since_date: str = None,
    skip_ingest: bool = False,
    skip_notify: bool = False,
) -> dict:
    """
    일배치 파이프라인 실행

    Args:
        ministry: 타겟 부처
        since_date: 수집 기준일 (기본: 어제)
        skip_ingest: 수집 건너뛰기 (테스트용)
        skip_notify: 알림 건너뛰기

    Returns:
        실행 결과
    """
    log("=" * 60)
    log("Cross-Domain Radar 일배치 시작")
    log("=" * 60)

    result = {
        "started_at": datetime.now().isoformat(),
        "ministry": ministry,
        "status": "running",
    }

    try:
        # ========================================
        # 1. 신규 법안 수집
        # ========================================
        if not skip_ingest:
            log("[1/4] 신규 법안 수집")
            ingest_result = run_daily_ingest(since_date=since_date)
            result["ingest"] = {
                "new_bills": ingest_result.get("new_bills_count", 0),
                "added": ingest_result.get("added_count", 0),
            }
            log(f"  → 신규: {result['ingest']['new_bills']}건, 추가: {result['ingest']['added']}건")
        else:
            log("[1/4] 수집 건너뜀 (skip_ingest)")
            result["ingest"] = {"skipped": True}

        # ========================================
        # 2. Cross-Domain 스캔
        # ========================================
        log("[2/4] Cross-Domain 스캔")

        # 설정 로드
        config = MinistryConfig()
        ministry_config = config.get_ministry(ministry)
        threshold = ministry_config.get("threshold", 0.45)

        log(f"  → 부처: {ministry}, 임계값: {threshold}")

        # 레이더 초기화 (v2 스코어러 사용)
        radar = CrossDomainRadar(
            ministry_name=ministry,
            threshold=threshold,
            data_dir=DATA_DIR,
        )

        # 마스터 데이터 로드
        master_file = DATA_DIR / "bills_master.json"
        if not master_file.exists():
            # fallback: bills_merged.json
            master_file = DATA_DIR / "bills_merged.json"

        with open(master_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        bills = data.get("bills", [])
        log(f"  → 법안 로드: {len(bills)}건")

        # 어제 이후 법안만 필터링 (일배치)
        if since_date is None:
            since_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        new_bills = [b for b in bills if b.get("propose_dt", "") >= since_date]
        log(f"  → {since_date} 이후 법안: {len(new_bills)}건")

        if not new_bills:
            log("  → 신규 법안 없음, 스캔 건너뜀")
            result["scan"] = {"new_bills": 0, "alerts": 0}
        else:
            # 스캔 실행
            alerts = radar.scan_bills(new_bills, show_progress=True)

            # v2 스코어러로 키워드 가산점 적용
            scorer_v2 = ScorerV2(ministry, config)
            embedder = radar.embedder
            rr_vector = radar.rr_vector

            # 키워드 가산점 재계산
            enhanced_alerts = []
            for alert in alerts:
                # 원본 법안 찾기
                bill = next((b for b in new_bills if b.get("bill_id") == alert.bill_id), None)
                if bill:
                    bonus, matched = scorer_v2.calculate_keyword_bonus(bill)
                    if bonus > 0:
                        # 가산점 적용
                        new_score = alert.similarity_score + bonus
                        alert.similarity_score = round(new_score, 4)
                        # 새 Alert Level 결정
                        alert.alert_level = scorer_v2.get_alert_level(new_score)
                enhanced_alerts.append(alert)

            # Alert Level별 집계
            alerts_by_level = {}
            for a in enhanced_alerts:
                level = a.alert_level
                alerts_by_level[level] = alerts_by_level.get(level, 0) + 1

            result["scan"] = {
                "new_bills": len(new_bills),
                "alerts": len(enhanced_alerts),
                "alerts_by_level": alerts_by_level,
            }

            log(f"  → 감지: {len(enhanced_alerts)}건")

        # ========================================
        # 3. 리포트 생성
        # ========================================
        log("[3/4] 리포트 생성")

        reporter = Reporter(output_dir=OUTPUT_DIR)

        scan_result = {
            "scan_type": "daily",
            "ministry": ministry,
            "threshold": threshold,
            "since_date": since_date,
            "scanned_at": datetime.now().isoformat(),
            "total_bills": result["scan"].get("new_bills", 0),
            "total_alerts": result["scan"].get("alerts", 0),
            "alerts_by_level": result["scan"].get("alerts_by_level", {}),
            "alerts": enhanced_alerts if "enhanced_alerts" in dir() else [],
        }

        if scan_result["total_alerts"] > 0:
            report_path = reporter.generate_daily_report(scan_result)
            result["report_path"] = str(report_path)
            log(f"  → 리포트: {report_path}")
        else:
            log("  → 감지 법안 없음, 리포트 생략")

        # ========================================
        # 4. 알림 발송 (Teams + 이메일)
        # ========================================
        log("[4/4] 알림 발송")

        if skip_notify:
            log("  → 알림 건너뜀 (skip_notify)")
        elif scan_result["total_alerts"] == 0:
            log("  → 감지 법안 없음, 알림 생략")
        else:
            scan_result["report_path"] = result.get("report_path")
            result["notify"] = {}

            # Teams 알림
            teams_success = notify_scan_result(scan_result)
            result["notify"]["teams"] = teams_success
            log(f"  → Teams: {'성공' if teams_success else '건너뜀/실패'}")

            # 이메일 알림
            email_success = notify_scan_result_email(scan_result)
            result["notify"]["email"] = email_success
            log(f"  → 이메일: {'성공' if email_success else '건너뜀/실패'}")

        # ========================================
        # 완료
        # ========================================
        result["status"] = "success"
        result["finished_at"] = datetime.now().isoformat()

        log("=" * 60)
        log("일배치 완료!")
        log("=" * 60)

    except Exception as e:
        log(f"오류 발생: {e}")
        traceback.print_exc()

        result["status"] = "error"
        result["error"] = str(e)
        result["finished_at"] = datetime.now().isoformat()

        # 에러 알림 (Teams + 이메일)
        if not skip_notify:
            try:
                TeamsNotifier().send_error(str(e), context=f"ministry={ministry}")
            except:
                pass
            try:
                EmailNotifier().send(
                    subject=f"❌ Cross-Domain Radar 오류 - {ministry}",
                    body_html=f"<h2>오류 발생</h2><pre>{str(e)}</pre>",
                )
            except:
                pass

    # 결과 저장
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"daily_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        # alerts 직렬화
        serializable = result.copy()
        if "scan" in serializable and "alerts" in result.get("scan", {}):
            pass  # 이미 직렬화됨
        json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)

    log(f"로그 저장: {log_file}")

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cross-Domain Radar 일배치")
    parser.add_argument(
        "--ministry",
        type=str,
        default="산업통상부",
        help="타겟 부처 (기본: 산업통상부)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="수집 기준일 (YYYY-MM-DD, 기본: 어제)",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="수집 단계 건너뛰기",
    )
    parser.add_argument(
        "--skip-notify",
        action="store_true",
        help="알림 발송 건너뛰기",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드 (수집/알림 건너뜀)",
    )

    args = parser.parse_args()

    if args.test:
        args.skip_ingest = True
        args.skip_notify = True

    run_daily_pipeline(
        ministry=args.ministry,
        since_date=args.since,
        skip_ingest=args.skip_ingest,
        skip_notify=args.skip_notify,
    )


if __name__ == "__main__":
    main()
